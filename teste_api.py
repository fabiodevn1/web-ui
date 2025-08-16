#!/usr/bin/env python3
"""
Script de teste para a API de Imóveis
"""

import requests
import json
from datetime import datetime

def testar_api():
    """Testa a API de imóveis"""
    
    base_url = "http://127.0.0.1:8000"
    
    print("🧪 Testando API de Imóveis VivaReal")
    print("=" * 50)
    
    # 1. Testar status
    print("\n1️⃣ Testando endpoint /status...")
    try:
        response = requests.get(f"{base_url}/status", timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Status: {data['status']}")
            print(f"   LLM configurado: {data['llm_configured']}")
            print(f"   Browser disponível: {data['browser_available']}")
        else:
            print(f"❌ Status retornou {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erro ao testar status: {e}")
        return False
    
    # 2. Testar busca de imóveis
    print("\n2️⃣ Testando busca de imóveis...")
    
    payload = {
        "cidade": "Araucaria",
        "estado": "PR",
        "tipo_operacao": "venda",
        "max_paginas": 1  # Apenas 1 página para teste rápido
    }
    
    try:
        print(f"   Enviando requisição para {base_url}/buscar-imoveis")
        print(f"   Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(
            f"{base_url}/buscar-imoveis",
            json=payload,
            timeout=300  # 5 minutos para a busca
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Busca realizada com sucesso!")
            print(f"   Cidade: {data['cidade']}")
            print(f"   Estado: {data['estado']}")
            print(f"   Tipo: {data['tipo_operacao']}")
            print(f"   Total de imóveis: {data['total_imoveis']}")
            print(f"   Data da busca: {data['data_busca']}")
            
            # Mostrar alguns imóveis
            if data['imoveis']:
                print(f"\n   📋 Primeiros imóveis encontrados:")
                for i, imovel in enumerate(data['imoveis'][:3], 1):
                    print(f"      {i}. {imovel['titulo']}")
                    print(f"         Preço: {imovel['preco']}")
                    print(f"         Área: {imovel['area']}")
                    print(f"         Quartos: {imovel['quartos']}")
                    print()
            
            # Salvar resultado em arquivo
            with open('teste_api_resultado.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"   💾 Resultado salvo em 'teste_api_resultado.json'")
            
            return True
            
        else:
            print(f"❌ Busca falhou com status {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Erro: {error_data.get('detail', 'Erro desconhecido')}")
            except:
                print(f"   Resposta: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Timeout na busca (pode demorar alguns minutos)")
        return False
    except Exception as e:
        print(f"❌ Erro na busca: {e}")
        return False

def testar_documentacao():
    """Testa se a documentação está acessível"""
    print("\n3️⃣ Testando documentação da API...")
    
    try:
        response = requests.get("http://127.0.0.1:8000/docs", timeout=10)
        if response.status_code == 200:
            print("✅ Documentação acessível em http://127.0.0.1:8000/docs")
            return True
        else:
            print(f"❌ Documentação retornou status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erro ao acessar documentação: {e}")
        return False

def main():
    """Função principal de teste"""
    print("🚀 Iniciando testes da API de Imóveis")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Verificar se API está rodando
    try:
        response = requests.get("http://127.0.0.1:8000", timeout=5)
        print("✅ API está rodando")
    except:
        print("❌ API não está rodando. Execute primeiro: python api_imoveis.py")
        return
    
    # Executar testes
    sucesso = True
    
    if not testar_api():
        sucesso = False
    
    if not testar_documentacao():
        sucesso = False
    
    # Resultado final
    print("\n" + "=" * 50)
    if sucesso:
        print("🎉 Todos os testes passaram com sucesso!")
        print("✅ A API está funcionando perfeitamente")
        print("\n📚 Próximos passos:")
        print("   1. Acesse http://127.0.0.1:8000/docs para documentação")
        print("   2. Use a API para buscar imóveis")
        print("   3. Execute python salvar_banco.py para salvar no banco")
        print("   4. Execute python automacao_busca.py para automação")
    else:
        print("❌ Alguns testes falharam")
        print("🔧 Verifique os logs e configurações")
    
    print(f"\n⏰ Teste finalizado em {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
