#!/usr/bin/env python3
"""
Sistema de Busca Única de Imóveis
Lê cidades ativas do banco MariaDB e busca apenas UM LINK por cidade/tipo
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
import requests
from database import db, get_plataformas_ativas
import json

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('busca_unica.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BuscaUnicaImoveis:
    """Sistema de busca única de imóveis usando WebUI"""
    
    def __init__(self):
        self.api_url = "http://127.0.0.1:8002"  # API MariaDB
        self.running = True
        self.ciclo_numero = 0
        self.tipos_operacao = ["venda", "aluguel"]
        
    def get_cidades_ativas(self) -> List[Dict]:
        """Busca cidades ativas do banco MariaDB"""
        try:
            query = """
                SELECT m.id, m.nome, m.estado_id, 
                       e.nome as estado_nome, e.sigla as estado_sigla
                FROM municipios m
                JOIN estados e ON m.estado_id = e.id
                WHERE m.ativo = 1 AND e.ativo = 1
                ORDER BY e.sigla, m.nome
                LIMIT 20  # Limitar para teste
            """
            cidades = db.execute_query(query)
            logger.info(f"✅ Encontradas {len(cidades)} cidades ativas no banco")
            return cidades
        except Exception as e:
            logger.error(f"❌ Erro ao buscar cidades ativas: {e}")
            return []
    
    def verificar_api_status(self) -> bool:
        """Verifica se a API está funcionando"""
        try:
            response = requests.get(f"{self.api_url}/status", timeout=10)
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ API Status: {data['status']}")
                logger.info(f"   Cidades ativas: {data['cidades_ativas']}")
                logger.info(f"   Plataformas ativas: {data['plataformas_ativas']}")
                return True
            else:
                logger.error(f"❌ API retornou status {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Erro ao conectar com API: {e}")
            return False
    
    async def buscar_link_unico(self, cidade: str, estado: str, tipo_operacao: str) -> Dict:
        """Busca link único para uma cidade/tipo específico"""
        logger.info(f"🔍 Buscando link único: {tipo_operacao} em {cidade}, {estado}")
        
        payload = {
            "cidade": cidade,
            "estado": estado,
            "tipo_operacao": tipo_operacao,
            "plataforma": "VivaReal"
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/buscar-link-unico",
                json=payload,
                timeout=300  # 5 minutos para a busca
            )
            
            if response.status_code == 200:
                resultado = response.json()
                logger.info(f"✅ Link único encontrado para {cidade}/{estado}")
                logger.info(f"   URL: {resultado['link_unico']}")
                logger.info(f"   Título: {resultado['titulo_pagina']}")
                logger.info(f"   Total imóveis: {resultado.get('total_imoveis', 'N/A')}")
                return resultado
            else:
                logger.error(f"❌ Busca falhou para {cidade}/{estado}: {response.status_code}")
                try:
                    error_data = response.json()
                    logger.error(f"   Erro: {error_data.get('detail', 'Erro desconhecido')}")
                except:
                    logger.error(f"   Resposta: {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error(f"⏰ Timeout na busca de {cidade}/{estado}")
            return None
        except Exception as e:
            logger.error(f"❌ Erro na busca de {cidade}/{estado}: {e}")
            return None
    
    def verificar_link_existente(self, cidade: str, estado: str, tipo_operacao: str) -> bool:
        """Verifica se já existe um link para esta cidade/tipo no banco"""
        try:
            # Busca cidade e estado no banco
            cidade_result = db.execute_query(
                "SELECT m.id as municipio_id, e.id as estado_id FROM municipios m JOIN estados e ON m.estado_id = e.id WHERE m.nome = %s AND e.sigla = %s",
                (cidade, estado)
            )
            
            if not cidade_result:
                return False
            
            municipio_id = cidade_result[0]['municipio_id']
            estado_id = cidade_result[0]['estado_id']
            
            # Busca plataforma VivaReal
            plataforma_result = db.execute_query(
                "SELECT id FROM plataformas WHERE nome = 'VivaReal' AND ativo = 1"
            )
            
            if not plataforma_result:
                return False
            
            plataforma_id = plataforma_result[0]['id']
            
            # Busca tipo de busca
            tipo_result = db.execute_query(
                "SELECT id FROM tipos_busca WHERE nome = %s",
                (tipo_operacao.upper(),)
            )
            
            if not tipo_result:
                return False
            
            tipo_busca_id = tipo_result[0]['id']
            
            # Verifica se já existe link
            link_existente = db.execute_query(
                "SELECT id, url, updated_at FROM links_duckduckgo WHERE plataforma_id = %s AND tipo_busca_id = %s AND estado_id = %s AND municipio_id = %s",
                (plataforma_id, tipo_busca_id, estado_id, municipio_id)
            )
            
            if link_existente:
                link = link_existente[0]
                ultima_atualizacao = link.get('updated_at') or link.get('created_at')
                
                # Se foi atualizado nas últimas 24h, não precisa buscar novamente
                if ultima_atualizacao:
                    if isinstance(ultima_atualizacao, str):
                        ultima_atualizacao = datetime.fromisoformat(ultima_atualizacao.replace('Z', '+00:00'))
                    
                    if datetime.now() - ultima_atualizacao < timedelta(hours=24):
                        logger.info(f"⏭️ Link já existe e foi atualizado recentemente para {cidade}/{estado}")
                        return True
                    else:
                        logger.info(f"🔄 Link existe mas é antigo para {cidade}/{estado}, será atualizado")
                        return False
                
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Erro ao verificar link existente para {cidade}/{estado}: {e}")
            return False
    
    async def processar_cidade(self, cidade: Dict, tipo_operacao: str):
        """Processa uma cidade específica para um tipo de operação"""
        nome_cidade = cidade['nome']
        sigla_estado = cidade['estado_sigla']
        
        logger.info(f"🏙️ Processando: {nome_cidade}/{sigla_estado} - {tipo_operacao}")
        
        # Verifica se já existe link recente
        if self.verificar_link_existente(nome_cidade, sigla_estado, tipo_operacao):
            logger.info(f"✅ Link já existe para {nome_cidade}/{sigla_estado} - {tipo_operacao}")
            return True
        
        # Busca o link único
        resultado = await self.buscar_link_unico(nome_cidade, sigla_estado, tipo_operacao)
        
        if resultado:
            logger.info(f"✅ Link único processado com sucesso para {nome_cidade}/{sigla_estado}")
            return True
        else:
            logger.warning(f"⚠️ Falha ao processar {nome_cidade}/{sigla_estado} - {tipo_operacao}")
            return False
    
    async def executar_ciclo_busca(self):
        """Executa um ciclo completo de busca única"""
        self.ciclo_numero += 1
        logger.info(f"\n{'='*70}")
        logger.info(f"🔍 CICLO DE BUSCA ÚNICA #{self.ciclo_numero}")
        logger.info(f"{'='*70}\n")
        
        # Verificar se API está funcionando
        if not self.verificar_api_status():
            logger.error("❌ API não está funcionando. Pulando ciclo.")
            return False
        
        # Buscar cidades ativas
        cidades = self.get_cidades_ativas()
        if not cidades:
            logger.warning("⚠️ Nenhuma cidade ativa encontrada")
            return False
        
        logger.info(f"📋 Processando {len(cidades)} cidades para {len(self.tipos_operacao)} tipos de operação")
        
        total_processados = 0
        total_sucessos = 0
        
        # Processar cada cidade para cada tipo de operação
        for i, cidade in enumerate(cidades, 1):
            logger.info(f"\n[{i}/{len(cidades)}] Cidade: {cidade['nome']}/{cidade['estado_sigla']}")
            
            for j, tipo_operacao in enumerate(self.tipos_operacao, 1):
                logger.info(f"   [{j}/{len(self.tipos_operacao)}] Tipo: {tipo_operacao}")
                
                sucesso = await self.processar_cidade(cidade, tipo_operacao)
                total_processados += 1
                
                if sucesso:
                    total_sucessos += 1
                
                # Aguardar entre buscas para não sobrecarregar
                await asyncio.sleep(10)
            
            # Aguardar entre cidades
            if i < len(cidades):
                logger.info(f"   ⏳ Aguardando 30 segundos antes da próxima cidade...")
                await asyncio.sleep(30)
        
        # Resumo do ciclo
        logger.info(f"\n{'='*70}")
        logger.info(f"📊 RESUMO DO CICLO #{self.ciclo_numero}")
        logger.info(f"{'='*70}")
        logger.info(f"   Total processado: {total_processados}")
        logger.info(f"   Sucessos: {total_sucessos}")
        logger.info(f"   Falhas: {total_processados - total_sucessos}")
        logger.info(f"   Taxa de sucesso: {(total_sucessos/total_processados)*100:.1f}%")
        logger.info(f"{'='*70}\n")
        
        return total_sucessos > 0
    
    def gerar_relatorio(self):
        """Gera relatório dos links salvos"""
        try:
            # Busca estatísticas do banco
            query_stats = """
                SELECT 
                    COUNT(*) as total_links,
                    COUNT(DISTINCT CONCAT(m.nome, '/', e.sigla)) as total_cidades,
                    COUNT(DISTINCT t.nome) as total_tipos,
                    MAX(l.updated_at) as ultima_atualizacao
                FROM links_duckduckgo l
                JOIN plataformas p ON l.plataforma_id = p.id
                JOIN tipos_busca t ON l.tipo_busca_id = t.id
                JOIN estados e ON l.estado_id = e.id
                JOIN municipios m ON l.municipio_id = m.id
                WHERE p.nome = 'VivaReal'
            """
            
            stats = db.execute_query(query_stats)
            if stats:
                stats = stats[0]
                
                logger.info("📊 RELATÓRIO DE LINKS SALVOS:")
                logger.info(f"   Total de links: {stats['total_links']}")
                logger.info(f"   Cidades cobertas: {stats['total_cidades']}")
                logger.info(f"   Tipos de operação: {stats['total_tipos']}")
                logger.info(f"   Última atualização: {stats['ultima_atualizacao']}")
                
                # Salvar relatório em arquivo
                relatorio = {
                    "timestamp": datetime.now().isoformat(),
                    "estatisticas": stats,
                    "ciclo_numero": self.ciclo_numero
                }
                
                with open('relatorio_busca_unica.json', 'w', encoding='utf-8') as f:
                    json.dump(relatorio, f, indent=2, ensure_ascii=False)
                
                logger.info("💾 Relatório salvo em 'relatorio_busca_unica.json'")
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar relatório: {e}")
    
    async def executar_loop_principal(self):
        """Loop principal de execução"""
        logger.info("🚀 Iniciando Sistema de Busca Única de Imóveis")
        logger.info("✅ Integrado com banco MariaDB")
        logger.info("🎯 Busca apenas UM LINK por cidade/tipo")
        logger.info("⏰ Execução automática a cada 6 horas")
        logger.info("Ctrl+C para parar\n")
        
        try:
            while self.running:
                try:
                    # Executar ciclo de busca
                    sucesso = await self.executar_ciclo_busca()
                    
                    if sucesso:
                        logger.info("✅ Ciclo executado com sucesso")
                    else:
                        logger.warning("⚠️ Ciclo executado com falhas")
                    
                    # Gerar relatório
                    self.gerar_relatorio()
                    
                    # Calcular próxima execução
                    proxima = datetime.now() + timedelta(hours=6)
                    logger.info(f"⏰ Próxima execução: {proxima.strftime('%d/%m/%Y %H:%M')}")
                    logger.info("💤 Aguardando 6 horas...")
                    
                    # Aguardar 6 horas
                    await asyncio.sleep(6 * 60 * 60)
                    
                except Exception as e:
                    logger.error(f"❌ Erro no ciclo principal: {e}")
                    logger.info("⏳ Aguardando 1 hora antes de tentar novamente...")
                    await asyncio.sleep(60 * 60)
                    
        except KeyboardInterrupt:
            logger.info("\n🛑 Sistema interrompido pelo usuário")
            self.running = False
            
            # Gerar relatório final
            self.gerar_relatorio()
            
            logger.info("👋 Sistema finalizado")

async def main():
    """Função principal"""
    print("\n" + "="*70)
    print("🔍 SISTEMA DE BUSCA ÚNICA DE IMÓVEIS - MARIA DB")
    print("="*70)
    print("✅ Integrado com banco MariaDB existente")
    print("✅ Busca apenas UM LINK por cidade/tipo")
    print("✅ Usa WebUI em vez de Bing")
    print("✅ Execução automática a cada 6 horas")
    print("✅ Salva no banco existente (links_duckduckgo)")
    print("\nCtrl+C para parar")
    print("="*70 + "\n")
    
    sistema = BuscaUnicaImoveis()
    await sistema.executar_loop_principal()

if __name__ == "__main__":
    asyncio.run(main())
