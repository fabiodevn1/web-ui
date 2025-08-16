#!/usr/bin/env python3

import asyncio
import os
from browser_use import Agent, Browser, BrowserConfig
from src.utils.llm_provider import get_llm_model
import json

async def teste():
    llm = get_llm_model(
        provider="openai",
        model="gpt-4o",
        temperature=0.1,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    task = """
    Navigate to https://www.chavesnamao.com.br/imoveis-para-alugar/pr-araucaria/
    Return: {"link": "URL", "title": "page title"}
    """
    
    config = BrowserConfig(headless=True)
    browser = Browser(config=config)
    agent = Agent(task=task, llm=llm, browser=browser)
    result = await agent.run(max_steps=10)
    
    print(f"is_done(): {result.is_done()}")
    print(f"is_successful(): {result.is_successful()}")
    
    content = result.extracted_content()
    print(f"\nextracted_content(): {content}")
    
    final = result.final_result()
    print(f"\nfinal_result(): {final}")
    
    # Tentar extrair JSON
    if content:
        try:
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end > start:
                json_str = content[start:end]
                dados = json.loads(json_str)
                print(f"\n✅ JSON EXTRAÍDO: {dados}")
                return dados
        except Exception as e:
            print(f"Erro: {e}")
    
    return None

if __name__ == "__main__":
    result = asyncio.run(teste())
    if result:
        print(f"\n🎉 SUCESSO! Link: {result.get('link')}")
    else:
        print("\n❌ FALHOU!")