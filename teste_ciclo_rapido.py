#!/usr/bin/env python3
"""
Teste rápido de um ciclo de busca
"""

import asyncio
import logging
from automacao_completa import AutomacaoBuscaCompleta
from database import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def teste_ciclo():
    """Testa um ciclo reduzido"""
    
    automacao = AutomacaoBuscaCompleta()
    automacao.delay_entre_buscas = 5  # Reduzir delay para teste
    
    # Obter configurações
    config = automacao.get_configuracoes_ativas()
    
    if not config:
        logger.error("Erro ao obter configurações")
        return
    
    # Testar apenas a primeira combinação
    cidade = config['cidades'][0]
    plataforma = config['plataformas'][0]
    tipo_busca = config['tipos_busca'][0]
    
    logger.info(f"Testando busca para:")
    logger.info(f"  Cidade: {cidade['cidade']}/{cidade['estado_sigla']}")
    logger.info(f"  Plataforma: {plataforma['nome']}")
    logger.info(f"  Tipo: {tipo_busca['nome']}")
    
    # Fazer a busca
    resultado = await automacao.buscar_link_plataforma(
        cidade['cidade'],
        cidade['estado_sigla'],
        plataforma['nome'],
        tipo_busca['nome']
    )
    
    if resultado:
        logger.info(f"✅ Resultado obtido: {resultado}")
        
        # Tentar salvar
        sucesso = automacao.salvar_link(
            resultado,
            cidade['municipio_id'],
            cidade['estado_id'],
            plataforma['id'],
            tipo_busca['id']
        )
        
        if sucesso:
            logger.info("✅ Link salvo com sucesso!")
            
            # Verificar no banco
            total = db.execute_query("SELECT COUNT(*) as total FROM links_duckduckgo")
            logger.info(f"📊 Total de links no banco: {total[0]['total']}")
        else:
            logger.error("❌ Falha ao salvar link")
    else:
        logger.warning("⚠️ Nenhum resultado obtido")

if __name__ == "__main__":
    asyncio.run(teste_ciclo())