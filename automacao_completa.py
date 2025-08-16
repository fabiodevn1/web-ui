#!/usr/bin/env python3
"""
Sistema de Automação Completa - Busca de Links de Imóveis
Executa buscas para todas as combinações ativas no banco
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
import os
from browser_use import Agent, Browser, BrowserConfig
from src.utils.llm_provider import get_llm_model
from dotenv import load_dotenv
from database import db
import json
import signal
import sys

# Carregar variáveis de ambiente
load_dotenv()

# Configurar logging
log_level = os.environ.get('LOG_LEVEL', 'INFO')
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('automacao_completa.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AutomacaoBuscaCompleta:
    """Sistema de automação completa para busca de links de imóveis"""
    
    def __init__(self):
        self.running = True
        self.ciclo_numero = 0
        self.intervalo_horas = 12  # Intervalo entre ciclos em horas
        self.delay_entre_buscas = 30  # Delay entre cada busca em segundos
        
        # Configurar LLM
        self.llm = get_llm_model(
            provider="openai",
            model="gpt-4o",
            temperature=0.1,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Configurar handler para Ctrl+C
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handler para interrupção do programa"""
        logger.info("\n🛑 Recebido sinal de interrupção. Finalizando...")
        self.running = False
        self.gerar_relatorio_final()
        sys.exit(0)
    
    def get_configuracoes_ativas(self) -> Dict:
        """Busca todas as configurações ativas do banco"""
        try:
            # Buscar cidades ativas
            query_cidades = """
                SELECT DISTINCT m.id as municipio_id, m.nome as cidade, 
                       e.id as estado_id, e.nome as estado_nome, e.sigla as estado_sigla
                FROM municipios m
                JOIN estados e ON m.estado_id = e.id
                WHERE m.ativo = 1 AND e.ativo = 1
                ORDER BY e.sigla, m.nome
            """
            cidades = db.execute_query(query_cidades)
            
            # Buscar plataformas ativas
            query_plataformas = """
                SELECT id, nome, url_base 
                FROM plataformas 
                WHERE ativo = 1
                ORDER BY nome
            """
            plataformas = db.execute_query(query_plataformas)
            
            # Buscar tipos de busca
            query_tipos = """
                SELECT id, nome 
                FROM tipos_busca
                ORDER BY nome
            """
            tipos_busca = db.execute_query(query_tipos)
            
            logger.info(f"📊 Configurações encontradas:")
            logger.info(f"   • {len(cidades)} cidades ativas")
            logger.info(f"   • {len(plataformas)} plataformas ativas")
            logger.info(f"   • {len(tipos_busca)} tipos de busca")
            
            total_combinacoes = len(cidades) * len(plataformas) * len(tipos_busca)
            logger.info(f"   • Total de combinações possíveis: {total_combinacoes}")
            
            return {
                'cidades': cidades,
                'plataformas': plataformas,
                'tipos_busca': tipos_busca,
                'total_combinacoes': total_combinacoes
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao buscar configurações: {e}")
            return None
    
    def verificar_link_existente(self, municipio_id: int, estado_id: int, 
                                plataforma_id: int, tipo_busca_id: int) -> bool:
        """Verifica se já existe um link recente para esta combinação"""
        try:
            # Verifica se já existe link atualizado nas últimas 24h
            query = """
                SELECT id, url, updated_at 
                FROM links_duckduckgo 
                WHERE plataforma_id = %s 
                AND tipo_busca_id = %s 
                AND estado_id = %s 
                AND municipio_id = %s
                AND (updated_at > DATE_SUB(NOW(), INTERVAL 24 HOUR) 
                     OR created_at > DATE_SUB(NOW(), INTERVAL 24 HOUR))
            """
            
            resultado = db.execute_query(query, 
                (plataforma_id, tipo_busca_id, estado_id, municipio_id))
            
            return len(resultado) > 0
            
        except Exception as e:
            logger.error(f"❌ Erro ao verificar link existente: {e}")
            return False
    
    async def buscar_link_plataforma(self, cidade: str, estado: str, 
                                    plataforma: str, tipo_busca: str) -> Dict:
        """Busca o link de uma plataforma específica usando browser_use"""
        try:
            logger.info(f"🔍 Buscando: {plataforma} - {tipo_busca} em {cidade}/{estado}")
            
            # Criar tarefa para o Agent
            task = f"""
            Faça uma busca real na internet para encontrar o link oficial da plataforma {plataforma} 
            para {tipo_busca.lower()} de imóveis em {cidade}, {estado}.
            
            INSTRUÇÕES:
            1. Vá para https://duckduckgo.com
            2. Pesquise por: "{plataforma} {tipo_busca.lower()} imóveis {cidade} {estado}"
            3. Encontre o link oficial da plataforma {plataforma} nos resultados
            4. Clique no link para navegar até o site
            5. Verifique se há imóveis listados na página
            6. Capture o URL atual da página
            
            IMPORTANTE:
            - O link deve ser do site oficial da {plataforma}
            - Deve ser uma página de listagem de imóveis, não um imóvel específico
            - Verifique se existem imóveis na página
            
            Retorne um JSON com:
            {{
                "plataforma": "{plataforma}",
                "cidade": "{cidade}",
                "estado": "{estado}",
                "tipo_busca": "{tipo_busca}",
                "link": "URL da página",
                "titulo": "título da página",
                "tem_imoveis": true/false,
                "total_imoveis": "quantidade se visível"
            }}
            """
            
            # Executar busca com o Agent - com headless se for opção 1
            headless = os.environ.get('HEADLESS_MODE', 'false').lower() == 'true'
            
            # Criar browser com configuração headless se necessário
            config = BrowserConfig(headless=headless)
            browser = Browser(config=config)
            agent = Agent(task=task, llm=self.llm, browser=browser)
            result = await agent.run(max_steps=30)
            
            # Processar resultado - o Agent retorna um AgentHistoryList
            logger.info(f"Processando resultado do Agent...")
            
            if result:
                # Verificar se a tarefa foi concluída com sucesso (são métodos, não propriedades!)
                if result.is_done() and result.is_successful():
                    # Primeiro tentar do final_result que já vem formatado
                    final = result.final_result()
                    if final:
                        logger.info(f"Resultado final obtido: {type(final)}")
                        
                        # Se for string, fazer parse (o mais comum)
                        if isinstance(final, str):
                            try:
                                # Tentar parse direto primeiro
                                dados = json.loads(final)
                                if dados.get('link'):
                                    logger.info(f"✅ Link encontrado: {dados.get('link')}")
                                    return dados
                            except json.JSONDecodeError:
                                # Tentar extrair JSON da string
                                start = final.find('{')
                                end = final.rfind('}') + 1
                                if start != -1 and end > start:
                                    try:
                                        json_str = final[start:end]
                                        dados = json.loads(json_str)
                                        if dados.get('link'):
                                            logger.info(f"✅ Link encontrado: {dados.get('link')}")
                                            return dados
                                    except json.JSONDecodeError as e:
                                        logger.debug(f"Erro ao fazer parse do resultado final: {e}")
                        # Se já for dict, usar diretamente
                        elif isinstance(final, dict):
                            if final.get('link'):
                                logger.info(f"✅ Link encontrado: {final.get('link')}")
                                return final
                    
                    # Se não conseguiu do final_result, tentar do extracted_content
                    content = result.extracted_content()
                    if content:
                        logger.debug(f"Conteúdo extraído (tipo: {type(content)}): {content}")
                        
                        # Se for lista, procurar o JSON no último item
                        if isinstance(content, list):
                            for item in reversed(content):
                                if isinstance(item, str) and '{' in item:
                                    start = item.find('{')
                                    end = item.rfind('}') + 1
                                    if start != -1 and end > start:
                                        try:
                                            json_str = item[start:end]
                                            dados = json.loads(json_str)
                                            if dados.get('link'):
                                                logger.info(f"✅ Link encontrado: {dados.get('link')}")
                                                return dados
                                        except json.JSONDecodeError:
                                            continue
                else:
                    logger.warning(f"Agent não completou a tarefa com sucesso. is_done={result.is_done()}, is_successful={result.is_successful()}")
                    if result.errors:
                        logger.error(f"Erros: {result.errors}")
            
            logger.warning(f"⚠️ Não foi possível encontrar link para {plataforma}")
            return None
            
        except Exception as e:
            logger.error(f"❌ Erro na busca: {e}")
            return None
    
    def salvar_link(self, dados: Dict, municipio_id: int, estado_id: int, 
                   plataforma_id: int, tipo_busca_id: int) -> bool:
        """Salva o link encontrado no banco de dados"""
        try:
            if not dados or not dados.get('link'):
                logger.warning(f"❌ Dados inválidos para salvar: {dados}")
                return False
            
            logger.info(f"💾 Tentando salvar link: {dados.get('link')[:50]}...")
            
            # Verificar se já existe
            logger.debug(f"Verificando se existe link para: plataforma={plataforma_id}, tipo={tipo_busca_id}, estado={estado_id}, municipio={municipio_id}")
            existe = db.execute_query(
                "SELECT id FROM links_duckduckgo WHERE plataforma_id = %s AND tipo_busca_id = %s AND estado_id = %s AND municipio_id = %s",
                (plataforma_id, tipo_busca_id, estado_id, municipio_id)
            )
            
            logger.debug(f"Resultado da verificação: {existe}")
            
            if existe:
                # Atualizar existente
                query = """
                    UPDATE links_duckduckgo 
                    SET url = %s, updated_at = NOW()
                    WHERE plataforma_id = %s AND tipo_busca_id = %s 
                    AND estado_id = %s AND municipio_id = %s
                """
                db.execute_update(query, (
                    dados['link'], plataforma_id, tipo_busca_id, 
                    estado_id, municipio_id
                ))
                logger.info(f"🔄 Link atualizado no banco")
            else:
                # Inserir novo
                query = """
                    INSERT INTO links_duckduckgo 
                    (url, plataforma_id, tipo_busca_id, estado_id, municipio_id,
                     termo_busca, posicao_busca, processado, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """
                termo = f"{dados.get('tipo_busca', '')} {dados.get('cidade', '')} {dados.get('estado', '')}"
                db.execute_update(query, (
                    dados['link'], plataforma_id, tipo_busca_id, 
                    estado_id, municipio_id, termo, 1, 0
                ))
                logger.info(f"💾 Novo link salvo no banco")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar link: {e}")
            return False
    
    async def executar_ciclo_completo(self):
        """Executa um ciclo completo de busca para todas as combinações"""
        self.ciclo_numero += 1
        inicio_ciclo = datetime.now()
        
        logger.info(f"\n{'='*80}")
        logger.info(f"🔄 INICIANDO CICLO #{self.ciclo_numero}")
        logger.info(f"📅 {inicio_ciclo.strftime('%d/%m/%Y %H:%M:%S')}")
        logger.info(f"{'='*80}\n")
        
        # Buscar configurações ativas
        config = self.get_configuracoes_ativas()
        if not config:
            logger.error("❌ Não foi possível obter configurações")
            return
        
        total_processados = 0
        total_sucesso = 0
        total_pulados = 0
        total_erros = 0
        
        # Processar cada combinação
        for cidade in config['cidades']:
            for plataforma in config['plataformas']:
                for tipo_busca in config['tipos_busca']:
                    
                    # Verificar se deve continuar
                    if not self.running:
                        logger.info("⏸️ Execução interrompida pelo usuário")
                        return
                    
                    total_processados += 1
                    
                    # Verificar se já existe link recente
                    if self.verificar_link_existente(
                        cidade['municipio_id'], cidade['estado_id'],
                        plataforma['id'], tipo_busca['id']
                    ):
                        logger.info(f"⏭️ Pulando (link recente existe): {plataforma['nome']} - {tipo_busca['nome']} - {cidade['cidade']}/{cidade['estado_sigla']}")
                        total_pulados += 1
                        continue
                    
                    # Fazer a busca
                    logger.info(f"\n[{total_processados}/{config['total_combinacoes']}] Processando:")
                    logger.info(f"   📍 {cidade['cidade']}, {cidade['estado_sigla']}")
                    logger.info(f"   🏢 {plataforma['nome']}")
                    logger.info(f"   🏠 {tipo_busca['nome']}")
                    
                    resultado = await self.buscar_link_plataforma(
                        cidade['cidade'], 
                        cidade['estado_sigla'],
                        plataforma['nome'],
                        tipo_busca['nome']
                    )
                    
                    if resultado:
                        logger.info(f"📝 Resultado obtido: {resultado}")
                        # Salvar no banco mesmo sem verificar tem_imoveis
                        if self.salvar_link(
                            resultado,
                            cidade['municipio_id'],
                            cidade['estado_id'],
                            plataforma['id'],
                            tipo_busca['id']
                        ):
                            total_sucesso += 1
                            logger.info(f"✅ Sucesso!")
                        else:
                            total_erros += 1
                            logger.error(f"❌ Erro ao salvar")
                    else:
                        total_erros += 1
                        logger.warning(f"⚠️ Sem resultados ou sem imóveis")
                    
                    # Delay entre buscas
                    logger.info(f"⏳ Aguardando {self.delay_entre_buscas}s antes da próxima busca...")
                    await asyncio.sleep(self.delay_entre_buscas)
        
        # Estatísticas do ciclo
        fim_ciclo = datetime.now()
        duracao = fim_ciclo - inicio_ciclo
        
        logger.info(f"\n{'='*80}")
        logger.info(f"📊 RESUMO DO CICLO #{self.ciclo_numero}")
        logger.info(f"{'='*80}")
        logger.info(f"⏱️ Duração: {duracao}")
        logger.info(f"📈 Estatísticas:")
        logger.info(f"   • Total processado: {total_processados}")
        logger.info(f"   • Sucesso: {total_sucesso}")
        logger.info(f"   • Pulados (recentes): {total_pulados}")
        logger.info(f"   • Erros: {total_erros}")
        logger.info(f"   • Taxa de sucesso: {(total_sucesso/max(total_processados-total_pulados, 1))*100:.1f}%")
        logger.info(f"{'='*80}\n")
        
        # Salvar estatísticas
        self.salvar_estatisticas_ciclo({
            'ciclo': self.ciclo_numero,
            'inicio': inicio_ciclo.isoformat(),
            'fim': fim_ciclo.isoformat(),
            'duracao': str(duracao),
            'total_processados': total_processados,
            'total_sucesso': total_sucesso,
            'total_pulados': total_pulados,
            'total_erros': total_erros
        })
    
    def salvar_estatisticas_ciclo(self, stats: Dict):
        """Salva estatísticas do ciclo em arquivo JSON"""
        try:
            arquivo = 'estatisticas_automacao.json'
            
            # Ler estatísticas existentes
            historico = []
            if os.path.exists(arquivo):
                with open(arquivo, 'r') as f:
                    historico = json.load(f)
            
            # Adicionar novo ciclo
            historico.append(stats)
            
            # Salvar
            with open(arquivo, 'w') as f:
                json.dump(historico, f, indent=2, ensure_ascii=False)
            
            logger.info(f"📊 Estatísticas salvas em {arquivo}")
            
        except Exception as e:
            logger.error(f"❌ Erro ao salvar estatísticas: {e}")
    
    def gerar_relatorio_final(self):
        """Gera relatório final com estatísticas do banco"""
        try:
            logger.info("\n📊 RELATÓRIO FINAL")
            logger.info("="*80)
            
            # Total de links no banco
            query_total = """
                SELECT COUNT(*) as total,
                       COUNT(DISTINCT plataforma_id) as plataformas,
                       COUNT(DISTINCT CONCAT(estado_id, '-', municipio_id)) as cidades,
                       COUNT(DISTINCT tipo_busca_id) as tipos
                FROM links_duckduckgo
            """
            
            totais = db.execute_query(query_total)
            if totais:
                total = totais[0]
                logger.info(f"📈 Totais no banco:")
                logger.info(f"   • Links salvos: {total['total']}")
                logger.info(f"   • Plataformas: {total['plataformas']}")
                logger.info(f"   • Cidades: {total['cidades']}")
                logger.info(f"   • Tipos de busca: {total['tipos']}")
            
            # Links atualizados hoje
            query_hoje = """
                SELECT COUNT(*) as total
                FROM links_duckduckgo
                WHERE DATE(updated_at) = CURDATE()
                   OR DATE(created_at) = CURDATE()
            """
            
            hoje = db.execute_query(query_hoje)
            if hoje:
                logger.info(f"   • Atualizados hoje: {hoje[0]['total']}")
            
            logger.info("="*80)
            
        except Exception as e:
            logger.error(f"❌ Erro ao gerar relatório: {e}")
    
    async def executar_loop_continuo(self):
        """Loop principal que executa os ciclos com intervalo definido"""
        logger.info(f"\n{'🚀'*20}")
        logger.info("SISTEMA DE AUTOMAÇÃO COMPLETA INICIADO")
        logger.info(f"{'🚀'*20}")
        logger.info(f"⏰ Intervalo entre ciclos: {self.intervalo_horas} horas")
        logger.info(f"⏱️ Delay entre buscas: {self.delay_entre_buscas} segundos")
        logger.info("Pressione Ctrl+C para parar\n")
        
        while self.running:
            try:
                # Executar ciclo completo
                await self.executar_ciclo_completo()
                
                if not self.running:
                    break
                
                # Calcular próxima execução
                proxima_execucao = datetime.now() + timedelta(hours=self.intervalo_horas)
                logger.info(f"\n💤 Aguardando {self.intervalo_horas} horas...")
                logger.info(f"⏰ Próxima execução: {proxima_execucao.strftime('%d/%m/%Y %H:%M:%S')}")
                logger.info("Pressione Ctrl+C para parar\n")
                
                # Aguardar com verificação periódica
                tempo_espera = self.intervalo_horas * 3600  # converter para segundos
                intervalo_check = 60  # verificar a cada minuto
                
                for _ in range(0, tempo_espera, intervalo_check):
                    if not self.running:
                        break
                    await asyncio.sleep(min(intervalo_check, tempo_espera))
                
            except Exception as e:
                logger.error(f"❌ Erro no ciclo: {e}")
                logger.info("⏳ Aguardando 5 minutos antes de tentar novamente...")
                await asyncio.sleep(300)
        
        logger.info("\n👋 Sistema finalizado")
        self.gerar_relatorio_final()

async def main():
    """Função principal"""
    automacao = AutomacaoBuscaCompleta()
    
    # Configurar handler para Ctrl+C
    def signal_handler(sig, frame):
        logger.info("\n⏸️ Recebido sinal de interrupção (Ctrl+C)")
        automacao.running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await automacao.executar_loop_continuo()
    except KeyboardInterrupt:
        logger.info("\n⏸️ Interrompido pelo usuário")
        automacao.running = False
    finally:
        automacao.gerar_relatorio_final()

if __name__ == "__main__":
    # Executar o sistema
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Sistema finalizado pelo usuário")