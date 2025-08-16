#!/usr/bin/env python3
"""
Teste da função de captura direta de links
"""

import asyncio
from playwright.async_api import async_playwright
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def capturar_link_direto(cidade: str, estado: str, tipo_operacao: str) -> dict:
    """
    Função para capturar o link diretamente usando Playwright
    """
    playwright = None
    browser = None
    page = None
    
    try:
        # Formatar URL
        cidade_formatada = cidade.lower().replace(" ", "-")
        estado_formatado = estado.lower()
        url = f"https://www.vivareal.com.br/{tipo_operacao}/{estado_formatado}/{cidade_formatada}/"
        
        logger.info(f"🌐 Acessando: {url}")
        
        # Iniciar navegador
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        
        # Criar contexto com user agent
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        page = await context.new_page()
        
        # Configurar timeout
        page.set_default_timeout(30000)
        
        # Navegar para a URL
        logger.info("📄 Navegando para a página...")
        response = await page.goto(url, wait_until='domcontentloaded')
        
        # Aguardar um pouco para garantir carregamento
        await page.wait_for_timeout(5000)
        
        # Capturar informações
        titulo = await page.title()
        url_atual = page.url
        
        logger.info(f"📍 URL atual: {url_atual}")
        logger.info(f"📝 Título: {titulo}")
        
        # Tentar capturar total de imóveis
        total_imoveis = None
        try:
            # Tentar vários seletores possíveis
            seletores = [
                '[data-testid="results-title"]',
                'h1[class*="results"]',
                'span[class*="results"]',
                'div[class*="results-summary"]',
                'div[class*="listing-counter"]',
                'strong[class*="results"]',
                'h1',
                '.results__title',
                '[class*="Title"]'
            ]
            
            for seletor in seletores:
                try:
                    elementos = await page.query_selector_all(seletor)
                    for elemento in elementos:
                        texto = await elemento.text_content()
                        if texto and ('imóve' in texto.lower() or 'resultado' in texto.lower() or 'anúncio' in texto.lower()):
                            total_imoveis = texto.strip()
                            logger.info(f"📊 Total encontrado com seletor {seletor}: {total_imoveis}")
                            break
                    if total_imoveis:
                        break
                except:
                    continue
            
            if not total_imoveis:
                logger.info("📊 Tentando capturar via texto da página...")
                # Tentar capturar via texto visível
                page_text = await page.evaluate('() => document.body.innerText')
                import re
                match = re.search(r'(\d+[\.\d]*)\s*(imóveis?|resultados?|anúncios?)', page_text, re.IGNORECASE)
                if match:
                    total_imoveis = match.group(0)
                    logger.info(f"📊 Total encontrado via regex: {total_imoveis}")
                    
        except Exception as e:
            logger.warning(f"⚠️ Não foi possível capturar total de imóveis: {e}")
        
        # Tirar screenshot para debug
        await page.screenshot(path="/tmp/vivareal_teste.png")
        logger.info("📸 Screenshot salvo em /tmp/vivareal_teste.png")
        
        # Limpar URL
        if '?' in url_atual:
            url_atual = url_atual.split('?')[0]
        if not url_atual.endswith('/'):
            url_atual += '/'
        
        logger.info(f"✅ Captura bem-sucedida!")
        
        return {
            'link_capturado': url_atual,
            'titulo': titulo,
            'total_imoveis': total_imoveis,
            'sucesso': True
        }
        
    except Exception as e:
        logger.error(f"❌ Erro na captura: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            'sucesso': False,
            'erro': str(e)
        }
    
    finally:
        # Limpar recursos
        if page:
            await page.close()
        if browser:
            await browser.close()
        if playwright:
            await playwright.stop()

async def main():
    """Testar a captura direta"""
    print("=" * 60)
    print("🔍 Teste de Captura Direta de Links - VivaReal")
    print("=" * 60)
    
    # Testar com diferentes cidades
    testes = [
        ("Curitiba", "PR", "venda"),
        ("Araucária", "PR", "aluguel"),
        ("São Paulo", "SP", "venda")
    ]
    
    for cidade, estado, tipo_operacao in testes:
        print(f"\n📍 Testando: {tipo_operacao} em {cidade}, {estado}")
        print("-" * 40)
        
        resultado = await capturar_link_direto(cidade, estado, tipo_operacao)
        
        if resultado.get('sucesso'):
            print(f"✅ Link capturado: {resultado['link_capturado']}")
            print(f"📝 Título: {resultado['titulo']}")
            print(f"📊 Total de imóveis: {resultado.get('total_imoveis', 'N/A')}")
        else:
            print(f"❌ Erro: {resultado.get('erro')}")
        
        print("-" * 40)
        
        # Aguardar um pouco entre testes
        await asyncio.sleep(2)
    
    print("\n" + "=" * 60)
    print("✅ Testes concluídos!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())