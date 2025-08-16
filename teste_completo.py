#!/usr/bin/env python3
"""
Teste completo do sistema de busca e salvamento no banco
"""

import requests
import json
import time
from database import db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def testar_busca_e_salvamento():
    """Testa busca de link e salvamento no banco"""
    
    logger.info("="*70)
    logger.info("🚀 TESTE COMPLETO DO SISTEMA")
    logger.info("="*70)
    
    # 1. Verificar status da API
    logger.info("\n1️⃣ Verificando status da API...")
    try:
        response = requests.get("http://127.0.0.1:8002/status")
        if response.status_code == 200:
            status = response.json()
            logger.info(f"✅ API Online")
            logger.info(f"   Database conectado: {status['database_connected']}")
            logger.info(f"   Cidades ativas: {status['cidades_ativas']}")
            logger.info(f"   Plataformas ativas: {status['plataformas_ativas']}")
        else:
            logger.error("❌ API não está respondendo corretamente")
            return
    except Exception as e:
        logger.error(f"❌ Erro ao conectar com API: {e}")
        logger.info("   Certifique-se de que a API está rodando: python api_imoveis_mariadb.py")
        return
    
    # 2. Fazer busca de link único
    logger.info("\n2️⃣ Buscando link único para Araucária/PR...")
    
    payload = {
        "cidade": "Araucária",
        "estado": "PR",
        "tipo_operacao": "venda",
        "plataforma": "VivaReal"
    }
    
    try:
        response = requests.post(
            "http://127.0.0.1:8002/buscar-link-unico",
            json=payload,
            timeout=120
        )
        
        if response.status_code == 200:
            resultado = response.json()
            logger.info("✅ Link encontrado com sucesso!")
            logger.info(f"   Link: {resultado['link_unico']}")
            logger.info(f"   Título: {resultado['titulo_pagina']}")
            logger.info(f"   Total imóveis: {resultado.get('total_imoveis', 'N/A')}")
            logger.info(f"   Status: {resultado['status']}")
            
            link_capturado = resultado['link_unico']
        else:
            logger.error(f"❌ Erro na busca: {response.status_code}")
            logger.error(f"   Resposta: {response.text}")
            return
            
    except Exception as e:
        logger.error(f"❌ Erro na requisição: {e}")
        return
    
    # 3. Verificar se foi salvo no banco
    logger.info("\n3️⃣ Verificando salvamento no banco de dados...")
    
    time.sleep(2)  # Aguardar um pouco para garantir que foi salvo
    
    try:
        # Buscar o link no banco
        query = """
            SELECT l.id, l.url, l.created_at, l.updated_at,
                   p.nome as plataforma, t.nome as tipo_busca,
                   e.sigla as estado, m.nome as cidade
            FROM links_duckduckgo l
            JOIN plataformas p ON l.plataforma_id = p.id
            LEFT JOIN tipos_busca t ON l.tipo_busca_id = t.id
            LEFT JOIN estados e ON l.estado_id = e.id
            LEFT JOIN municipios m ON l.municipio_id = m.id
            WHERE l.url LIKE %s
            ORDER BY l.created_at DESC
            LIMIT 1
        """
        
        resultado_banco = db.execute_query(query, (f"%{link_capturado}%",))
        
        if resultado_banco:
            registro = resultado_banco[0]
            logger.info("✅ Link encontrado no banco de dados!")
            logger.info(f"   ID: {registro['id']}")
            logger.info(f"   URL: {registro['url']}")
            logger.info(f"   Plataforma: {registro['plataforma']}")
            logger.info(f"   Tipo: {registro['tipo_busca']}")
            logger.info(f"   Local: {registro['cidade']}, {registro['estado']}")
            logger.info(f"   Criado em: {registro['created_at']}")
            logger.info(f"   Atualizado em: {registro['updated_at']}")
        else:
            logger.warning("⚠️ Link não encontrado no banco")
            
            # Tentar buscar qualquer link de Araucária
            query_alt = """
                SELECT l.id, l.url, p.nome as plataforma
                FROM links_duckduckgo l
                JOIN plataformas p ON l.plataforma_id = p.id
                WHERE l.url LIKE '%araucaria%'
                ORDER BY l.created_at DESC
                LIMIT 5
            """
            
            outros_links = db.execute_query(query_alt)
            
            if outros_links:
                logger.info("📋 Outros links de Araucária encontrados:")
                for link in outros_links:
                    logger.info(f"   - [{link['plataforma']}] {link['url'][:80]}...")
            else:
                logger.info("   Nenhum link de Araucária encontrado no banco")
                
    except Exception as e:
        logger.error(f"❌ Erro ao verificar banco: {e}")
    
    # 4. Estatísticas finais
    logger.info("\n4️⃣ Estatísticas do banco...")
    
    try:
        stats_query = """
            SELECT 
                COUNT(*) as total_links,
                COUNT(DISTINCT p.nome) as total_plataformas,
                COUNT(DISTINCT CONCAT(m.nome, '/', e.sigla)) as total_cidades
            FROM links_duckduckgo l
            JOIN plataformas p ON l.plataforma_id = p.id
            LEFT JOIN estados e ON l.estado_id = e.id
            LEFT JOIN municipios m ON l.municipio_id = m.id
        """
        
        stats = db.execute_query(stats_query)
        
        if stats:
            stat = stats[0]
            logger.info("📊 Estatísticas gerais:")
            logger.info(f"   Total de links: {stat['total_links']}")
            logger.info(f"   Plataformas únicas: {stat['total_plataformas']}")
            logger.info(f"   Cidades únicas: {stat['total_cidades']}")
            
    except Exception as e:
        logger.error(f"❌ Erro ao buscar estatísticas: {e}")
    
    logger.info("\n" + "="*70)
    logger.info("✅ TESTE COMPLETO FINALIZADO!")
    logger.info("="*70)

if __name__ == "__main__":
    testar_busca_e_salvamento()