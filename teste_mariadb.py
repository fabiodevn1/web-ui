#!/usr/bin/env python3
"""
Script de teste para verificar integração com MariaDB
"""

import requests
import json
from datetime import datetime
from database import db, get_plataformas_ativas
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def testar_conexao_banco():
    """Testa conexão com o banco MariaDB"""
    print("🔌 Testando conexão com banco MariaDB...")
    
    try:
        # Testa query simples
        result = db.execute_query("SELECT 1 as teste")
        if result and result[0]['teste'] == 1:
            print("✅ Conexão com banco OK")
            return True
        else:
            print("❌ Conexão com banco falhou")
            return False
    except Exception as e:
        print(f"❌ Erro na conexão: {e}")
        return False

def testar_estrutura_banco():
    """Testa se as tabelas necessárias existem"""
    print("\n📋 Testando estrutura do banco...")
    
    tabelas_necessarias = [
        'municipios',
        'estados', 
        'plataformas',
        'tipos_busca',
        'links_duckduckgo'
    ]
    
    todas_ok = True
    
    for tabela in tabelas_necessarias:
        try:
            result = db.execute_query(f"SELECT COUNT(*) as total FROM {tabela}")
            if result:
                count = result[0]['total']
                print(f"✅ Tabela {tabela}: {count} registros")
            else:
                print(f"⚠️ Tabela {tabela}: sem registros")
        except Exception as e:
            print(f"❌ Tabela {tabela}: erro - {e}")
            todas_ok = False
    
    return todas_ok

def testar_cidades_ativas():
    """Testa busca de cidades ativas"""
    print("\n🏙️ Testando busca de cidades ativas...")
    
    try:
        query = """
            SELECT m.nome, e.sigla, e.nome as estado_nome
            FROM municipios m
            JOIN estados e ON m.estado_id = e.id
            WHERE m.ativo = 1 AND e.ativo = 1
            ORDER BY e.sigla, m.nome
            LIMIT 5
        """
        
        cidades = db.execute_query(query)
        
        if cidades:
            print(f"✅ Encontradas {len(cidades)} cidades ativas:")
            for cidade in cidades:
                print(f"   - {cidade['nome']}/{cidade['sigla']} ({cidade['estado_nome']})")
            return True
        else:
            print("⚠️ Nenhuma cidade ativa encontrada")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao buscar cidades: {e}")
        return False

def testar_plataformas():
    """Testa busca de plataformas"""
    print("\n🌐 Testando busca de plataformas...")
    
    try:
        plataformas = get_plataformas_ativas()
        
        if plataformas:
            print(f"✅ Encontradas {len(plataformas)} plataformas:")
            for plataforma in plataformas:
                print(f"   - {plataforma['nome']}: {plataforma['url_base']}")
            return True
        else:
            print("⚠️ Nenhuma plataforma ativa encontrada")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao buscar plataformas: {e}")
        return False

def testar_tipos_busca():
    """Testa busca de tipos de busca"""
    print("\n🏷️ Testando tipos de busca...")
    
    try:
        query = "SELECT id, nome FROM tipos_busca ORDER BY nome"
        tipos = db.execute_query(query)
        
        if tipos:
            print(f"✅ Encontrados {len(tipos)} tipos de busca:")
            for tipo in tipos:
                print(f"   - {tipo['nome']} (ID: {tipo['id']})")
            return True
        else:
            print("⚠️ Nenhum tipo de busca encontrado")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao buscar tipos de busca: {e}")
        return False

def testar_api_status():
    """Testa se a API está funcionando"""
    print("\n🌐 Testando status da API...")
    
    try:
        response = requests.get("http://127.0.0.1:8002/status", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ API está funcionando")
            print(f"   Status: {data['status']}")
            print(f"   Cidades ativas: {data['cidades_ativas']}")
            print(f"   Plataformas ativas: {data['plataformas_ativas']}")
            return True
        else:
            print(f"❌ API retornou status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao conectar com API: {e}")
        print("   💡 Execute primeiro: python api_imoveis_mariadb.py")
        return False

def testar_busca_unica():
    """Testa busca única de imóveis"""
    print("\n🔍 Testando busca única de imóveis...")
    
    try:
        payload = {
            "cidade": "Araucaria",
            "estado": "PR",
            "tipo_operacao": "venda",
            "plataforma": "VivaReal"
        }
        
        print(f"   Enviando requisição para /buscar-link-unico")
        print(f"   Payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(
            "http://127.0.0.1:8002/buscar-link-unico",
            json=payload,
            timeout=300  # 5 minutos
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Busca única realizada com sucesso!")
            print(f"   Cidade: {data['cidade']}")
            print(f"   Estado: {data['estado']}")
            print(f"   Tipo: {data['tipo_operacao']}")
            print(f"   Link único: {data['link_unico']}")
            print(f"   Título: {data['titulo_pagina']}")
            print(f"   Total imóveis: {data.get('total_imoveis', 'N/A')}")
            
            # Salvar resultado em arquivo
            with open('teste_busca_unica.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print("   💾 Resultado salvo em 'teste_busca_unica.json'")
            
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
        print("⏰ Timeout na busca (pode demorar alguns minutos)")
        return False
    except Exception as e:
        print(f"❌ Erro na busca: {e}")
        return False

def verificar_links_salvos():
    """Verifica se os links foram salvos no banco"""
    print("\n💾 Verificando links salvos no banco...")
    
    try:
        response = requests.get("http://127.0.0.1:8002/links-salvos", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Encontrados {data['total']} links salvos no banco")
            
            if data['links']:
                print("   📋 Últimos links salvos:")
                for i, link in enumerate(data['links'][:3], 1):
                    print(f"      {i}. {link['cidade']}/{link['estado']} - {link['tipo_busca']}")
                    print(f"         URL: {link['url']}")
                    print(f"         Plataforma: {link['plataforma']}")
                    print()
            
            return True
        else:
            print(f"❌ Erro ao buscar links salvos: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao verificar links salvos: {e}")
        return False

def main():
    """Função principal de teste"""
    print("🚀 TESTE DE INTEGRAÇÃO MARIA DB - VIVA REAL")
    print("=" * 60)
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Executar testes
    testes = [
        ("Conexão com banco", testar_conexao_banco),
        ("Estrutura do banco", testar_estrutura_banco),
        ("Cidades ativas", testar_cidades_ativas),
        ("Plataformas", testar_plataformas),
        ("Tipos de busca", testar_tipos_busca),
        ("Status da API", testar_api_status),
        ("Busca única", testar_busca_unica),
        ("Links salvos", verificar_links_salvos)
    ]
    
    resultados = []
    
    for nome, teste in testes:
        print(f"🧪 {nome}...")
        try:
            sucesso = teste()
            resultados.append((nome, sucesso))
        except Exception as e:
            print(f"❌ Erro no teste: {e}")
            resultados.append((nome, False))
        print()
    
    # Resumo final
    print("=" * 60)
    print("📊 RESUMO DOS TESTES")
    print("=" * 60)
    
    total = len(resultados)
    sucessos = sum(1 for _, sucesso in resultados if sucesso)
    
    for nome, sucesso in resultados:
        status = "✅ PASSOU" if sucesso else "❌ FALHOU"
        print(f"   {nome}: {status}")
    
    print(f"\n   Total: {total} testes")
    print(f"   Sucessos: {sucessos}")
    print(f"   Falhas: {total - sucessos}")
    print(f"   Taxa de sucesso: {(sucessos/total)*100:.1f}%")
    
    if sucessos == total:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
        print("✅ Sistema integrado funcionando perfeitamente")
        print("\n📚 Próximos passos:")
        print("   1. Execute: python busca_unica.py")
        print("   2. Configure automação se necessário")
        print("   3. Monitore os logs")
    else:
        print(f"\n⚠️ {total - sucessos} TESTE(S) FALHARAM")
        print("🔧 Verifique as configurações e tente novamente")
    
    print(f"\n⏰ Teste finalizado em {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
