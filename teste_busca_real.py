#!/usr/bin/env python3
"""
Teste da API com busca real usando WebUI
"""

import requests
import json
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def testar_busca_real():
    """Testa a busca real com WebUI"""
    
    logger.info("="*70)
    logger.info("🚀 TESTE DE BUSCA REAL COM WEBUI")
    logger.info("="*70)
    logger.info("⚠️ Este teste abrirá um navegador real e fará buscas na internet")
    logger.info("⏳ Pode levar 1-2 minutos para completar")
    logger.info("-"*70)
    
    # Aguardar API iniciar
    time.sleep(5)
    
    # 1. Verificar status
    logger.info("\n1️⃣ Verificando status da API...")
    try:
        response = requests.get("http://127.0.0.1:8003/status")
        if response.status_code == 200:
            logger.info("✅ API online e pronta")
        else:
            logger.error("❌ API não está respondendo")
            return
    except Exception as e:
        logger.error(f"❌ Erro ao conectar: {e}")
        logger.info("Certifique-se que a API está rodando: python api_imoveis_webui.py")
        return
    
    # 2. Fazer busca real
    logger.info("\n2️⃣ Iniciando busca real para Curitiba/PR...")
    logger.info("🌐 O navegador será aberto automaticamente...")
    
    payload = {
        "cidade": "Curitiba",
        "estado": "PR",
        "tipo_operacao": "aluguel",
        "plataforma": "VivaReal"
    }
    
    try:
        logger.info("📡 Enviando requisição para API...")
        response = requests.post(
            "http://127.0.0.1:8003/buscar-link-unico",
            json=payload,
            timeout=180  # 3 minutos de timeout
        )
        
        if response.status_code == 200:
            resultado = response.json()
            logger.info("\n✅ BUSCA REAL CONCLUÍDA COM SUCESSO!")
            logger.info("-"*50)
            logger.info(f"🏙️ Cidade: {resultado['cidade']}, {resultado['estado']}")
            logger.info(f"🏠 Tipo: {resultado['tipo_operacao']}")
            logger.info(f"🔗 Link encontrado: {resultado['link_unico']}")
            logger.info(f"📄 Título: {resultado['titulo_pagina']}")
            logger.info(f"📊 Total de imóveis: {resultado.get('total_imoveis', 'N/A')}")
            logger.info(f"💬 Observações: {resultado.get('observacoes', 'N/A')}")
            logger.info("-"*50)
            
            # Verificar se o link é válido (não é construído manualmente)
            if 'curitiba' in resultado['link_unico'].lower() and 'aluguel' in resultado['link_unico'].lower():
                logger.info("✅ Link parece ser válido e específico para a busca")
            else:
                logger.warning("⚠️ Link pode não corresponder à busca realizada")
                
            return resultado
            
        else:
            logger.error(f"❌ Erro na busca: {response.status_code}")
            try:
                error = response.json()
                logger.error(f"   Detalhes: {error.get('detail', 'Erro desconhecido')}")
            except:
                logger.error(f"   Resposta: {response.text}")
                
    except requests.exceptions.Timeout:
        logger.error("⏰ Timeout - a busca demorou mais de 3 minutos")
    except Exception as e:
        logger.error(f"❌ Erro: {e}")
    
    logger.info("\n" + "="*70)
    logger.info("Teste finalizado")
    logger.info("="*70)

if __name__ == "__main__":
    # Aviso antes de iniciar
    print("\n" + "⚠️"*30)
    print("ATENÇÃO: Este teste abrirá um navegador real!")
    print("O browser_use irá navegar automaticamente")
    print("NÃO interfira com o navegador durante o teste")
    print("⚠️"*30)
    print("\nPressione Enter para continuar ou Ctrl+C para cancelar...")
    input()
    
    testar_busca_real()