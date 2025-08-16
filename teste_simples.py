#!/usr/bin/env python3
"""
Teste simples e direto
"""

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
    
    # Task mais simples e direta
    task = """
    Navigate to https://www.chavesnamao.com.br/imoveis-para-alugar/pr-araucaria/
    
    Return a JSON with:
    {
        "link": "current URL",
        "title": "page title"
    }
    """
    
    config = BrowserConfig(headless=True)
    browser = Browser(config=config)
    agent = Agent(task=task, llm=llm, browser=browser)
    result = await agent.run(max_steps=10)
    
    print(f"Type: {type(result)}")
    print(f"Done: {result.is_done}")
    print(f"Success: {result.is_successful}")
    
    # Verificar todos os atributos possíveis
    attrs_to_check = ['extracted_content', 'final_result', 'model_outputs', 'action_results']
    
    for attr in attrs_to_check:
        if hasattr(result, attr):
            value = getattr(result, attr)
            print(f"\n{attr}:")
            print(f"  Type: {type(value)}")
            if value:
                print(f"  Value: {str(value)[:500]}")

if __name__ == "__main__":
    asyncio.run(teste())