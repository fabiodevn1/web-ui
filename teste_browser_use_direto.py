#!/usr/bin/env python3
"""
Teste direto do browser_use para buscar links do VivaReal
"""

import asyncio
import os
from browser_use import Agent
from src.utils.llm_provider import get_llm_model
from dotenv import load_dotenv
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def buscar_vivareal_direto():
    """Busca direta usando browser_use"""
    
    logger.info("="*70)
    logger.info("🚀 TESTE DIRETO DO BROWSER_USE")
    logger.info("="*70)
    
    # Configurar LLM
    llm = get_llm_model(
        provider="openai",
        model="gpt-4o",
        temperature=0.1,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # Tarefa para o Agent
    task = """
    Faça uma busca real na internet para encontrar o link do VivaReal para aluguel de imóveis em Curitiba, PR.
    
    PASSOS:
    1. Vá para https://duckduckgo.com
    2. Pesquise por: "VivaReal aluguel Curitiba PR"
    3. Encontre o link oficial do VivaReal nos resultados
    4. Clique no link para navegar até o site
    5. Verifique se há imóveis listados na página
    6. Capture o URL atual da página
    
    Retorne um JSON com:
    - link: URL da página do VivaReal
    - titulo: título da página
    - tem_imoveis: true/false se há imóveis na página
    """
    
    logger.info("🤖 Iniciando Agent...")
    logger.info("🌐 O navegador será aberto...")
    
    try:
        # Criar e executar o Agent
        agent = Agent(
            task=task,
            llm=llm
        )
        
        logger.info("▶️ Executando busca...")
        result = await agent.run(max_steps=30)
        
        logger.info("✅ Busca concluída!")
        
        # Mostrar resultados
        if result and hasattr(result, 'all_results'):
            logger.info(f"📊 Total de ações: {len(result.all_results)}")
            
            for i, action in enumerate(result.all_results):
                if action.is_done and action.extracted_content:
                    logger.info(f"\n📄 Resultado final:")
                    logger.info(str(action.extracted_content))
                    break
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("\n⚠️ Este teste abrirá um navegador real!")
    print("O browser_use navegará automaticamente")
    print("-"*60)
    
    # Executar o teste
    asyncio.run(buscar_vivareal_direto())