#!/usr/bin/env python3
"""
Teste para debug do resultado do Agent
"""

import asyncio
import logging
import os
from browser_use import Agent, Browser
from src.utils.llm_provider import get_llm_model
import json

# Configurar logging em DEBUG
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def teste_agent():
    """Testa a extração do resultado do Agent"""
    
    # Configurar LLM
    llm = get_llm_model(
        provider="openai",
        model="gpt-4o",
        temperature=0.1,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # Task simples para teste
    task = """
    Vá para https://www.chavesnamao.com.br e retorne um JSON com:
    {
        "plataforma": "CHAVES-NA-MAO",
        "link": "URL da página",
        "titulo": "título da página"
    }
    """
    
    try:
        # Criar browser headless
        browser = Browser(headless=True)
        agent = Agent(task=task, llm=llm, browser=browser)
        result = await agent.run(max_steps=10)
        
        print(f"\n=== RESULTADO DO AGENT ===")
        print(f"Tipo: {type(result)}")
        print(f"Valor: {result}")
        
        if result:
            print(f"\n=== TENTANDO EXTRAIR JSON ===")
            
            # Se for string
            if isinstance(result, str):
                print("É uma string!")
                start = result.find('{')
                end = result.rfind('}') + 1
                if start != -1 and end > start:
                    json_str = result[start:end]
                    print(f"JSON extraído: {json_str}")
                    dados = json.loads(json_str)
                    print(f"Dados parseados: {dados}")
            
            # Se for dict
            elif isinstance(result, dict):
                print("É um dict!")
                print(f"Dados: {result}")
            
            # Converter para string
            else:
                resultado_str = str(result)
                print(f"Convertido para string: {resultado_str[:200]}...")
                
    except Exception as e:
        print(f"ERRO: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(teste_agent())