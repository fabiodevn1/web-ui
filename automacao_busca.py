#!/usr/bin/env python3
"""
Script de automação para busca periódica de imóveis
Executa buscas automáticas e salva no banco de dados
"""

import schedule
import time
import logging
from datetime import datetime
import requests
from salvar_banco import BancoImoveis, buscar_e_salvar
import json

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('automacao_imoveis.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Configurações de busca
CIDADES_BUSCA = [
    {"cidade": "Araucaria", "estado": "PR", "tipo": "venda"},
    {"cidade": "Araucaria", "estado": "PR", "tipo": "aluguel"},
    {"cidade": "Curitiba", "estado": "PR", "tipo": "venda"},
    {"cidade": "Curitiba", "estado": "PR", "tipo": "aluguel"},
    {"cidade": "Pinhais", "estado": "PR", "tipo": "venda"},
    {"cidade": "Pinhais", "estado": "PR", "tipo": "aluguel"},
]

# Configurações de agendamento
HORARIOS_BUSCA = [
    "08:00",  # Manhã
    "12:00",  # Meio-dia
    "18:00",  # Tarde
    "22:00",  # Noite
]

def verificar_api():
    """Verifica se a API está funcionando"""
    try:
        response = requests.get("http://127.0.0.1:8000/status", timeout=10)
        if response.status_code == 200:
            logger.info("✅ API está funcionando")
            return True
        else:
            logger.error(f"❌ API retornou status {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Erro ao conectar com API: {e}")
        return False

def executar_busca_cidade(cidade: str, estado: str, tipo: str):
    """Executa busca para uma cidade específica"""
    logger.info(f"🔍 Iniciando busca: {tipo} em {cidade}, {estado}")
    
    try:
        resultado = buscar_e_salvar(
            cidade=cidade,
            estado=estado,
            tipo_operacao=tipo,
            max_paginas=2  # Limitar a 2 páginas por busca
        )
        
        if resultado:
            logger.info(f"✅ Busca concluída: {resultado.get('total_imoveis', 0)} imóveis encontrados")
            
            # Salvar log da busca
            with open('historico_buscas.json', 'a') as f:
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "cidade": cidade,
                    "estado": estado,
                    "tipo": tipo,
                    "total_encontrado": resultado.get('total_imoveis', 0),
                    "status": "sucesso"
                }
                f.write(json.dumps(log_entry) + '\n')
        else:
            logger.error(f"❌ Falha na busca: {tipo} em {cidade}, {estado}")
            
            # Salvar log de erro
            with open('historico_buscas.json', 'a') as f:
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "cidade": cidade,
                    "estado": estado,
                    "tipo": tipo,
                    "total_encontrado": 0,
                    "status": "erro"
                }
                f.write(json.dumps(log_entry) + '\n')
                
    except Exception as e:
        logger.error(f"❌ Erro na execução da busca: {e}")

def executar_todas_buscas():
    """Executa todas as buscas configuradas"""
    logger.info("🚀 Iniciando execução de todas as buscas")
    
    # Verificar se API está funcionando
    if not verificar_api():
        logger.error("❌ API não está funcionando. Pulando execução.")
        return
    
    # Executar busca para cada cidade
    for config in CIDADES_BUSCA:
        try:
            executar_busca_cidade(
                cidade=config["cidade"],
                estado=config["estado"],
                tipo=config["tipo"]
            )
            
            # Aguardar entre buscas para não sobrecarregar
            time.sleep(30)
            
        except Exception as e:
            logger.error(f"❌ Erro na busca de {config['cidade']}: {e}")
    
    logger.info("✅ Execução de todas as buscas concluída")

def gerar_relatorio():
    """Gera relatório das buscas realizadas"""
    try:
        banco = BancoImoveis()
        stats = banco.estatisticas()
        
        logger.info("📊 Relatório de Estatísticas:")
        logger.info(f"   Total de imóveis: {stats['total_imoveis']}")
        logger.info(f"   Por cidade: {stats['por_cidade']}")
        logger.info(f"   Por tipo: {stats['por_tipo']}")
        logger.info(f"   Última atualização: {stats['ultima_atualizacao']}")
        
        # Salvar relatório em arquivo
        with open('relatorio_imoveis.json', 'w') as f:
            json.dump(stats, f, indent=2, default=str)
            
        logger.info("📄 Relatório salvo em 'relatorio_imoveis.json'")
        
    except Exception as e:
        logger.error(f"❌ Erro ao gerar relatório: {e}")

def configurar_agendamento():
    """Configura o agendamento das buscas"""
    logger.info("⏰ Configurando agendamento das buscas")
    
    # Agendar buscas nos horários configurados
    for horario in HORARIOS_BUSCA:
        schedule.every().day.at(horario).do(executar_todas_buscas)
        logger.info(f"   Busca agendada para {horario}")
    
    # Agendar relatório diário
    schedule.every().day.at("23:00").do(gerar_relatorio)
    logger.info("   Relatório agendado para 23:00")
    
    # Executar busca inicial
    logger.info("🚀 Executando busca inicial...")
    executar_todas_buscas()

def main():
    """Função principal"""
    logger.info("🏠 Iniciando sistema de automação de busca de imóveis")
    
    # Configurar agendamento
    configurar_agendamento()
    
    logger.info("⏰ Sistema agendado. Aguardando execução...")
    logger.info("   Pressione Ctrl+C para parar")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Verificar a cada minuto
            
    except KeyboardInterrupt:
        logger.info("🛑 Sistema interrompido pelo usuário")
        
        # Gerar relatório final
        gerar_relatorio()
        
        logger.info("👋 Sistema finalizado")

if __name__ == "__main__":
    main()
