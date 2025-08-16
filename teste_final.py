#!/usr/bin/env python3
"""
Teste final com múltiplas cidades e tipos
"""

import requests
import json
import time
from database import db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def testar_multiplas_buscas():
    """Testa múltiplas buscas para verificar consistência"""
    
    logger.info("="*70)
    logger.info("🚀 TESTE FINAL - MÚLTIPLAS BUSCAS")
    logger.info("="*70)
    
    # Configurações de teste
    testes = [
        {"cidade": "Curitiba", "estado": "PR", "tipo": "aluguel"},
        {"cidade": "Pinhais", "estado": "PR", "tipo": "venda"},
    ]
    
    resultados_sucesso = []
    resultados_falha = []
    
    for i, teste in enumerate(testes, 1):
        logger.info(f"\n📍 Teste {i}/{len(testes)}: {teste['tipo']} em {teste['cidade']}, {teste['estado']}")
        logger.info("-"*50)
        
        payload = {
            "cidade": teste['cidade'],
            "estado": teste['estado'],
            "tipo_operacao": teste['tipo'],
            "plataforma": "VivaReal"
        }
        
        try:
            # Fazer a busca
            response = requests.post(
                "http://127.0.0.1:8002/buscar-link-unico",
                json=payload,
                timeout=120
            )
            
            if response.status_code == 200:
                resultado = response.json()
                logger.info(f"✅ Link capturado: {resultado['link_unico']}")
                
                # Verificar no banco
                time.sleep(2)
                query = """
                    SELECT l.id, l.url, p.nome as plataforma
                    FROM links_duckduckgo l
                    JOIN plataformas p ON l.plataforma_id = p.id
                    WHERE l.url = %s
                    LIMIT 1
                """
                
                banco_result = db.execute_query(query, (resultado['link_unico'],))
                
                if banco_result:
                    logger.info(f"✅ Salvo no banco com ID: {banco_result[0]['id']}")
                    resultados_sucesso.append({
                        "teste": teste,
                        "link": resultado['link_unico'],
                        "id_banco": banco_result[0]['id']
                    })
                else:
                    logger.warning("⚠️ Não encontrado no banco")
                    resultados_falha.append({
                        "teste": teste,
                        "erro": "Não salvo no banco"
                    })
                    
            else:
                logger.error(f"❌ Erro na busca: {response.status_code}")
                resultados_falha.append({
                    "teste": teste,
                    "erro": f"Status {response.status_code}"
                })
                
        except Exception as e:
            logger.error(f"❌ Erro: {e}")
            resultados_falha.append({
                "teste": teste,
                "erro": str(e)
            })
        
        # Aguardar entre testes
        if i < len(testes):
            logger.info("⏳ Aguardando 5 segundos...")
            time.sleep(5)
    
    # Resumo final
    logger.info("\n" + "="*70)
    logger.info("📊 RESUMO DO TESTE FINAL")
    logger.info("="*70)
    
    logger.info(f"\n✅ SUCESSOS: {len(resultados_sucesso)}/{len(testes)}")
    for sucesso in resultados_sucesso:
        teste = sucesso['teste']
        logger.info(f"   • {teste['cidade']}/{teste['estado']} ({teste['tipo']})")
        logger.info(f"     Link: {sucesso['link']}")
        logger.info(f"     ID no banco: {sucesso['id_banco']}")
    
    if resultados_falha:
        logger.info(f"\n❌ FALHAS: {len(resultados_falha)}/{len(testes)}")
        for falha in resultados_falha:
            teste = falha['teste']
            logger.info(f"   • {teste['cidade']}/{teste['estado']} ({teste['tipo']})")
            logger.info(f"     Erro: {falha['erro']}")
    
    # Estatísticas do banco
    logger.info("\n📈 ESTATÍSTICAS FINAIS DO BANCO:")
    
    query_vivareal = """
        SELECT COUNT(*) as total,
               COUNT(DISTINCT municipio_id) as cidades_unicas,
               COUNT(DISTINCT tipo_busca_id) as tipos_unicos
        FROM links_duckduckgo l
        JOIN plataformas p ON l.plataforma_id = p.id
        WHERE p.nome LIKE '%VIVA%REAL%'
    """
    
    stats = db.execute_query(query_vivareal)
    if stats:
        stat = stats[0]
        logger.info(f"   Links VivaReal no banco: {stat['total']}")
        logger.info(f"   Cidades únicas: {stat['cidades_unicas']}")
        logger.info(f"   Tipos únicos: {stat['tipos_unicos']}")
    
    # Verificar taxa de sucesso
    taxa_sucesso = (len(resultados_sucesso) / len(testes)) * 100
    
    logger.info("\n" + "="*70)
    if taxa_sucesso == 100:
        logger.info("🎉 TESTE FINAL APROVADO - 100% DE SUCESSO!")
    elif taxa_sucesso >= 80:
        logger.info(f"✅ TESTE FINAL APROVADO - {taxa_sucesso:.0f}% DE SUCESSO!")
    else:
        logger.info(f"⚠️ TESTE FINAL COM PROBLEMAS - {taxa_sucesso:.0f}% DE SUCESSO")
    logger.info("="*70)

if __name__ == "__main__":
    testar_multiplas_buscas()