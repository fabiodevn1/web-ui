#!/usr/bin/env python3
"""
Teste de uma única busca
"""

import asyncio
import logging
from automacao_completa import AutomacaoBuscaCompleta
from database import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def teste():
    automacao = AutomacaoBuscaCompleta()
    
    # Fazer apenas uma busca
    resultado = await automacao.buscar_link_plataforma(
        "Curitiba", "PR", "CHAVES-NA-MAO", "ALUGUEL"
    )
    
    logger.info(f"Resultado da busca: {resultado}")
    
    if resultado:
        # Tentar salvar
        sucesso = automacao.salvar_link(
            resultado,
            municipio_id=4106902,  # Curitiba
            estado_id=41,          # PR
            plataforma_id=3,       # CHAVES-NA-MAO
            tipo_busca_id=1        # ALUGUEL
        )
        
        if sucesso:
            logger.info("✅ Link salvo com sucesso!")
            
            # Verificar no banco
            total = db.execute_query("SELECT COUNT(*) as total FROM links_duckduckgo")
            logger.info(f"Total de links no banco: {total[0]['total']}")
        else:
            logger.error("❌ Falha ao salvar")
    else:
        logger.error("❌ Nenhum resultado obtido")

if __name__ == "__main__":
    asyncio.run(teste())