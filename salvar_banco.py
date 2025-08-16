import requests
import json
import sqlite3
from datetime import datetime
from typing import List, Dict

class BancoImoveis:
    def __init__(self, db_path: str = "imoveis.db"):
        self.db_path = db_path
        self.criar_tabela()
    
    def criar_tabela(self):
        """Cria a tabela de imóveis se não existir"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS imoveis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                titulo TEXT NOT NULL,
                preco TEXT,
                endereco TEXT,
                area TEXT,
                quartos TEXT,
                banheiros TEXT,
                vagas TEXT,
                link TEXT UNIQUE,
                data_anuncio TEXT,
                descricao TEXT,
                cidade TEXT,
                estado TEXT,
                tipo_operacao TEXT,
                data_busca TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                url_fonte TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        print(f"✅ Tabela criada/verificada em {self.db_path}")
    
    def salvar_imoveis(self, dados_api: Dict) -> int:
        """Salva os imóveis retornados pela API no banco"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        total_salvos = 0
        
        for imovel in dados_api.get('imoveis', []):
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO imoveis 
                    (titulo, preco, endereco, area, quartos, banheiros, vagas, 
                     link, data_anuncio, descricao, cidade, estado, tipo_operacao, url_fonte)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    imovel.get('titulo', ''),
                    imovel.get('preco', ''),
                    imovel.get('endereco', ''),
                    imovel.get('area', ''),
                    imovel.get('quartos', ''),
                    imovel.get('banheiros', ''),
                    imovel.get('vagas', ''),
                    imovel.get('link', ''),
                    imovel.get('data_anuncio', ''),
                    imovel.get('descricao', ''),
                    dados_api.get('cidade', ''),
                    dados_api.get('estado', ''),
                    dados_api.get('tipo_operacao', ''),
                    dados_api.get('url_fonte', '')
                ))
                total_salvos += 1
                
            except sqlite3.IntegrityError as e:
                print(f"⚠️ Imóvel já existe (link duplicado): {imovel.get('titulo', '')}")
            except Exception as e:
                print(f"❌ Erro ao salvar imóvel: {e}")
        
        conn.commit()
        conn.close()
        
        print(f"✅ {total_salvos} imóveis salvos no banco de dados")
        return total_salvos
    
    def buscar_imoveis(self, cidade: str = None, estado: str = None, tipo: str = None) -> List[Dict]:
        """Busca imóveis no banco de dados"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM imoveis WHERE 1=1"
        params = []
        
        if cidade:
            query += " AND cidade LIKE ?"
            params.append(f"%{cidade}%")
        
        if estado:
            query += " AND estado LIKE ?"
            params.append(f"%{estado}%")
        
        if tipo:
            query += " AND tipo_operacao = ?"
            params.append(tipo)
        
        query += " ORDER BY data_busca DESC"
        
        cursor.execute(query, params)
        colunas = [desc[0] for desc in cursor.description]
        
        imoveis = []
        for row in cursor.fetchall():
            imoveis.append(dict(zip(colunas, row)))
        
        conn.close()
        return imoveis
    
    def estatisticas(self) -> Dict:
        """Retorna estatísticas do banco de dados"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total de imóveis
        cursor.execute("SELECT COUNT(*) FROM imoveis")
        total = cursor.fetchone()[0]
        
        # Por cidade
        cursor.execute("SELECT cidade, COUNT(*) FROM imoveis GROUP BY cidade")
        por_cidade = dict(cursor.fetchall())
        
        # Por tipo de operação
        cursor.execute("SELECT tipo_operacao, COUNT(*) FROM imoveis GROUP BY tipo_operacao")
        por_tipo = dict(cursor.fetchall())
        
        # Última atualização
        cursor.execute("SELECT MAX(data_busca) FROM imoveis")
        ultima_atualizacao = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_imoveis": total,
            "por_cidade": por_cidade,
            "por_tipo": por_tipo,
            "ultima_atualizacao": ultima_atualizacao
        }

def buscar_e_salvar(cidade: str, estado: str, tipo_operacao: str = "venda", max_paginas: int = 3):
    """Função principal para buscar e salvar imóveis"""
    
    # 1. Chamar a API
    print(f"🔍 Buscando imóveis para {tipo_operacao} em {cidade}, {estado}...")
    
    url = "http://127.0.0.1:8000/buscar-imoveis"
    payload = {
        "cidade": cidade,
        "estado": estado,
        "tipo_operacao": tipo_operacao,
        "max_paginas": max_paginas
    }
    
    try:
        response = requests.post(url, json=payload, timeout=300)  # 5 minutos timeout
        response.raise_for_status()
        
        dados = response.json()
        print(f"✅ API retornou {dados.get('total_imoveis', 0)} imóveis")
        
        # 2. Salvar no banco
        banco = BancoImoveis()
        total_salvos = banco.salvar_imoveis(dados)
        
        # 3. Mostrar estatísticas
        stats = banco.estatisticas()
        print(f"\n📊 Estatísticas do banco:")
        print(f"   Total de imóveis: {stats['total_imoveis']}")
        print(f"   Por cidade: {stats['por_cidade']}")
        print(f"   Por tipo: {stats['por_tipo']}")
        
        return dados
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Erro na requisição: {e}")
        return None
    except Exception as e:
        print(f"❌ Erro geral: {e}")
        return None

if __name__ == "__main__":
    # Exemplo de uso
    print("🚀 Iniciando busca e salvamento de imóveis...")
    
    # Buscar imóveis em Araucária, PR
    resultado = buscar_e_salvar(
        cidade="Araucaria",
        estado="PR",
        tipo_operacao="venda",
        max_paginas=2
    )
    
    if resultado:
        print(f"\n🎯 Busca concluída com sucesso!")
        print(f"   Cidade: {resultado['cidade']}")
        print(f"   Estado: {resultado['estado']}")
        print(f"   Tipo: {resultado['tipo_operacao']}")
        print(f"   Total encontrado: {resultado['total_imoveis']}")
    else:
        print("❌ Falha na busca")
