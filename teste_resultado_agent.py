#!/usr/bin/env python3
"""
Teste detalhado do resultado do Agent
"""

import asyncio
import os
from browser_use import Agent, Browser, BrowserConfig
from src.utils.llm_provider import get_llm_model
import json

async def teste_detalhado():
    """Testa extração detalhada do resultado"""
    
    llm = get_llm_model(
        provider="openai",
        model="gpt-4o",
        temperature=0.1,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    task = """
    Faça uma busca real na internet para encontrar o link oficial da plataforma CHAVES-NA-MAO 
    para aluguel de imóveis em Araucária, PR.
    
    INSTRUÇÕES:
    1. Vá para https://duckduckgo.com
    2. Pesquise por: "CHAVES-NA-MAO aluguel imóveis Araucária PR"
    3. Encontre o link oficial da plataforma CHAVES-NA-MAO nos resultados
    4. Clique no link para navegar até o site
    5. Verifique se há imóveis listados na página
    6. Capture o URL atual da página
    
    Retorne um JSON com:
    {
        "plataforma": "CHAVES-NA-MAO",
        "cidade": "Araucária",
        "estado": "PR",
        "tipo_busca": "ALUGUEL",
        "link": "URL da página",
        "titulo": "título da página",
        "tem_imoveis": true/false,
        "total_imoveis": "quantidade se visível"
    }
    """
    
    try:
        config = BrowserConfig(headless=True)
        browser = Browser(config=config)
        agent = Agent(task=task, llm=llm, browser=browser)
        result = await agent.run(max_steps=30)
        
        print("\n" + "="*80)
        print("ANÁLISE DETALHADA DO RESULTADO")
        print("="*80)
        
        print(f"\n1. Tipo do resultado: {type(result)}")
        print(f"2. is_done: {result.is_done}")
        print(f"3. is_successful: {result.is_successful}")
        print(f"4. has_errors: {result.has_errors}")
        
        if result.errors:
            print(f"5. Erros: {result.errors}")
        
        print(f"\n6. extracted_content existe? {result.extracted_content is not None}")
        if result.extracted_content:
            print(f"   Tipo: {type(result.extracted_content)}")
            print(f"   Valor: {result.extracted_content}")
        
        print(f"\n7. final_result existe? {result.final_result is not None}")
        if result.final_result:
            print(f"   Tipo: {type(result.final_result)}")
            print(f"   Valor: {result.final_result}")
        
        print(f"\n8. model_outputs:")
        for i, output in enumerate(result.model_outputs):
            print(f"   Output {i}: {output[:200] if isinstance(output, str) else output}")
        
        print(f"\n9. action_results:")
        for i, action in enumerate(result.action_results):
            print(f"   Action {i}: {action}")
            
        print(f"\n10. last_action: {result.last_action}")
        
        # Tentar extrair JSON de todas as fontes possíveis
        print("\n" + "="*80)
        print("TENTANDO EXTRAIR JSON")
        print("="*80)
        
        json_found = False
        
        # De extracted_content
        if result.extracted_content:
            content = str(result.extracted_content)
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end > start:
                try:
                    json_str = content[start:end]
                    dados = json.loads(json_str)
                    print(f"\n✅ JSON encontrado em extracted_content:")
                    print(json.dumps(dados, indent=2, ensure_ascii=False))
                    json_found = True
                except:
                    pass
        
        # De final_result
        if not json_found and result.final_result:
            content = str(result.final_result)
            start = content.find('{')
            end = content.rfind('}') + 1
            if start != -1 and end > start:
                try:
                    json_str = content[start:end]
                    dados = json.loads(json_str)
                    print(f"\n✅ JSON encontrado em final_result:")
                    print(json.dumps(dados, indent=2, ensure_ascii=False))
                    json_found = True
                except:
                    pass
        
        # De model_outputs
        if not json_found:
            for output in result.model_outputs:
                if output:
                    content = str(output)
                    start = content.find('{')
                    end = content.rfind('}') + 1
                    if start != -1 and end > start:
                        try:
                            json_str = content[start:end]
                            dados = json.loads(json_str)
                            print(f"\n✅ JSON encontrado em model_outputs:")
                            print(json.dumps(dados, indent=2, ensure_ascii=False))
                            json_found = True
                            break
                        except:
                            pass
        
        if not json_found:
            print("\n❌ Nenhum JSON válido encontrado!")
            
    except Exception as e:
        print(f"ERRO: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(teste_detalhado())