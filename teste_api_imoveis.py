#!/usr/bin/env python3
"""
Teste da API de busca de links únicos de imóveis
"""

import asyncio
import httpx
import json
from datetime import datetime

# Configuração da API
API_URL = "http://127.0.0.1:8002"

async def testar_status():
    """Testa o endpoint de status"""
    print("\n🔍 Testando status da API...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(f"{API_URL}/status")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Erro ao testar status: {e}")
            return False

async def testar_busca_unica(cidade="Curitiba", estado="PR", tipo_operacao="venda"):
    """Testa a busca de link único"""
    print(f"\n🏠 Testando busca de link único para {tipo_operacao} em {cidade}, {estado}...")
    
    payload = {
        "cidade": cidade,
        "estado": estado,
        "tipo_operacao": tipo_operacao,
        "plataforma": "VivaReal"
    }
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            print(f"Payload: {json.dumps(payload, indent=2)}")
            response = await client.post(
                f"{API_URL}/buscar-link-unico",
                json=payload
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                resultado = response.json()
                print(f"\n✅ Busca bem-sucedida!")
                print(f"Link capturado: {resultado.get('link_unico')}")
                print(f"Título: {resultado.get('titulo_pagina')}")
                print(f"Total de imóveis: {resultado.get('total_imoveis')}")
                print(f"Status: {resultado.get('status')}")
                print(f"Observações: {resultado.get('observacoes')}")
                return True
            else:
                print(f"❌ Erro na resposta: {response.text}")
                return False
                
        except httpx.TimeoutException:
            print("⏱️ Timeout na requisição (limite de 120 segundos)")
            return False
        except Exception as e:
            print(f"❌ Erro ao testar busca: {e}")
            return False

async def testar_links_salvos():
    """Testa listagem de links salvos"""
    print("\n📋 Testando listagem de links salvos...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(f"{API_URL}/links-salvos")
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                dados = response.json()
                print(f"Total de links salvos: {dados.get('total', 0)}")
                
                if dados.get('links'):
                    print("\nÚltimos 3 links:")
                    for link in dados['links'][:3]:
                        print(f"  - {link.get('cidade')}/{link.get('estado')}: {link.get('url')}")
                return True
            else:
                print(f"❌ Erro: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Erro ao listar links: {e}")
            return False

async def main():
    """Função principal de teste"""
    print("=" * 60)
    print("🚀 Iniciando testes da API de Imóveis")
    print(f"📅 Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 URL da API: {API_URL}")
    print("=" * 60)
    
    # Testar status
    status_ok = await testar_status()
    
    if not status_ok:
        print("\n⚠️ API não está respondendo corretamente. Verifique se está rodando.")
        print(f"Execute: cd /home/ftgk/Documentos/GitHub/avalion-getlinks/web-ui && python3 api_imoveis_mariadb.py")
        return
    
    # Testar busca única
    print("\n" + "=" * 60)
    busca_ok = await testar_busca_unica("Araucária", "PR", "venda")
    
    # Testar listagem de links
    print("\n" + "=" * 60)
    links_ok = await testar_links_salvos()
    
    # Resumo
    print("\n" + "=" * 60)
    print("📊 RESUMO DOS TESTES")
    print("=" * 60)
    print(f"✅ Status da API: {'OK' if status_ok else 'FALHOU'}")
    print(f"✅ Busca de link único: {'OK' if busca_ok else 'FALHOU'}")
    print(f"✅ Listagem de links: {'OK' if links_ok else 'FALHOU'}")
    
    if status_ok and busca_ok and links_ok:
        print("\n🎉 Todos os testes passaram com sucesso!")
    else:
        print("\n⚠️ Alguns testes falharam. Verifique os logs acima.")

if __name__ == "__main__":
    asyncio.run(main())