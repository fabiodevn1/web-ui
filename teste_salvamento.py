#!/usr/bin/env python3
"""
Script de teste para verificar salvamento de links no banco
"""

import asyncio
import logging
from automacao_completa import AutomacaoBuscaCompleta
from database import db

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def teste_salvamento():
    """Testa o salvamento de um link no banco"""
    
    automacao = AutomacaoBuscaCompleta()
    
    # Dados de teste
    dados_teste = {
        "plataforma": "TESTE-PLATAFORMA",
        "cidade": "Curitiba",
        "estado": "PR",
        "tipo_busca": "ALUGUEL",
        "link": "https://teste.com.br/imoveis/curitiba",
        "titulo": "Teste de Imóveis",
        "tem_imoveis": True,
        "total_imoveis": "100"
    }
    
    # IDs de teste (usando valores existentes no banco)
    municipio_id = 1  # Ajuste conforme seu banco
    estado_id = 1     # Ajuste conforme seu banco
    plataforma_id = 1 # Ajuste conforme seu banco
    tipo_busca_id = 1 # Ajuste conforme seu banco
    
    logger.info(f"Testando salvamento com dados: {dados_teste}")
    
    # Tentar salvar
    resultado = automacao.salvar_link(
        dados_teste,
        municipio_id,
        estado_id,
        plataforma_id,
        tipo_busca_id
    )
    
    if resultado:
        logger.info("✅ Link salvo com sucesso!")
        
        # Verificar no banco
        links = db.execute_query(
            "SELECT * FROM links_duckduckgo WHERE url = %s",
            (dados_teste['link'],)
        )
        
        if links:
            logger.info(f"✅ Link verificado no banco: {links[0]}")
        else:
            logger.error("❌ Link não encontrado no banco após salvamento")
    else:
        logger.error("❌ Falha ao salvar link")
    
    # Verificar total de links
    total = db.execute_query("SELECT COUNT(*) as total FROM links_duckduckgo")
    logger.info(f"📊 Total de links no banco: {total[0]['total']}")

if __name__ == "__main__":
    asyncio.run(teste_salvamento())