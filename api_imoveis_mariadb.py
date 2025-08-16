from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import json
from datetime import datetime
from browser_use import Agent
from browser_use.browser.context import BrowserContext
from playwright.async_api import async_playwright
from src.utils.llm_provider import get_llm_model
import os
from dotenv import load_dotenv
from database import db, get_plataformas_ativas
import logging
import urllib.parse
import unicodedata

# Carregar variáveis de ambiente
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="API de Imóveis VivaReal - MariaDB", version="2.0.0")

class BuscaUnica(BaseModel):
    """Modelo para busca única de imóveis"""
    cidade: str
    estado: str
    tipo_operacao: str = "venda"  # venda ou aluguel
    plataforma: str = "VivaReal"  # plataforma específica

class ResultadoBuscaUnica(BaseModel):
    """Resultado da busca única"""
    cidade: str
    estado: str
    tipo_operacao: str
    plataforma: str
    link_unico: str
    titulo_pagina: str
    total_imoveis: Optional[str] = None
    data_busca: str
    status: str
    observacoes: Optional[str] = None

def get_llm():
    """Configura e retorna o modelo LLM"""
    try:
        return get_llm_model(
            provider="openai",
            model="gpt-4o",
            temperature=0.1,
            api_key=os.getenv("OPENAI_API_KEY")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao configurar LLM: {str(e)}")

def get_cidades_ativas():
    """Busca cidades ativas do banco MariaDB"""
    try:
        query = """
            SELECT m.id, m.nome, m.estado_id, 
                   e.nome as estado_nome, e.sigla as estado_sigla
            FROM municipios m
            JOIN estados e ON m.estado_id = e.id
            WHERE m.ativo = 1 AND e.ativo = 1
            ORDER BY e.sigla, m.nome
        """
        return db.execute_query(query)
    except Exception as e:
        logger.error(f"Erro ao buscar cidades ativas: {e}")
        return []

def get_plataforma_id(nome_plataforma: str):
    """Busca ID da plataforma no banco"""
    try:
        # Tentar buscar pelo nome exato primeiro
        result = db.execute_query(
            "SELECT id FROM plataformas WHERE nome = %s AND ativo = 1",
            (nome_plataforma,)
        )
        
        # Se não encontrar, tentar variações
        if not result:
            # Tentar com hífen
            nome_alternativo = nome_plataforma.replace("VivaReal", "VIVA-REAL")
            result = db.execute_query(
                "SELECT id FROM plataformas WHERE nome = %s AND ativo = 1",
                (nome_alternativo,)
            )
        
        # Se ainda não encontrar, tentar com LIKE
        if not result:
            result = db.execute_query(
                "SELECT id FROM plataformas WHERE nome LIKE %s AND ativo = 1",
                (f"%{nome_plataforma.replace('-', '')}%",)
            )
        
        if result:
            logger.info(f"✅ Plataforma encontrada: ID={result[0]['id']}")
            return result[0]['id']
        else:
            logger.error(f"❌ Plataforma '{nome_plataforma}' não encontrada no banco")
            return None
    except Exception as e:
        logger.error(f"Erro ao buscar plataforma {nome_plataforma}: {e}")
        return None

def get_tipo_busca_id(nome_tipo: str):
    """Busca ID do tipo de busca no banco"""
    try:
        result = db.execute_query(
            "SELECT id FROM tipos_busca WHERE nome = %s",
            (nome_tipo.upper(),)
        )
        return result[0]['id'] if result else None
    except Exception as e:
        logger.error(f"Erro ao buscar tipo de busca {nome_tipo}: {e}")
        return None

async def capturar_link_direto(cidade: str, estado: str, tipo_operacao: str) -> dict:
    """
    Função auxiliar para capturar o link diretamente usando Playwright
    sem usar o Agent, como fallback mais simples
    """
    playwright = None
    browser = None
    page = None
    
    try:
        # Formatar URL - usar normalização melhor para caracteres especiais
        cidade_formatada = cidade.lower().replace(" ", "-")
        # Remover acentos e caracteres especiais
        cidade_formatada = ''.join(
            c for c in unicodedata.normalize('NFD', cidade_formatada)
            if unicodedata.category(c) != 'Mn'
        )
        estado_formatado = estado.lower()
        url = f"https://www.vivareal.com.br/{tipo_operacao}/{estado_formatado}/{cidade_formatada}/"
        
        logger.info(f"🌐 Captura direta: Acessando {url}")
        
        # Iniciar navegador
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox'
            ]
        )
        
        # Criar contexto com user agent real
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        
        page = await context.new_page()
        
        # Configurar timeout
        page.set_default_timeout(30000)
        
        # Navegar para a URL
        response = await page.goto(url, wait_until='domcontentloaded')
        
        # Aguardar carregamento completo
        try:
            # Aguardar algum elemento específico do VivaReal
            await page.wait_for_selector('body', state='visible', timeout=5000)
            await page.wait_for_timeout(3000)
        except:
            pass
        
        # Capturar informações
        titulo = await page.title()
        url_atual = page.url
        
        # Se título vazio, tentar capturar de outras formas
        if not titulo or titulo == "":
            try:
                # Tentar meta title
                meta_title = await page.query_selector('meta[property="og:title"]')
                if meta_title:
                    titulo = await meta_title.get_attribute('content')
                
                # Se ainda vazio, tentar h1
                if not titulo:
                    h1 = await page.query_selector('h1')
                    if h1:
                        titulo = await h1.text_content()
                
                # Se ainda vazio, criar título padrão
                if not titulo:
                    titulo = f"Imóveis para {tipo_operacao} em {cidade}, {estado}"
            except:
                titulo = f"Imóveis para {tipo_operacao} em {cidade}, {estado}"
        
        logger.info(f"📝 Título capturado: {titulo}")
        
        # Tentar capturar total de imóveis
        total_imoveis = None
        try:
            # Aguardar um pouco mais para elementos dinâmicos
            await page.wait_for_timeout(2000)
            
            # Seletores comuns para contador de imóveis no VivaReal
            seletores = [
                '[data-testid="results-title"]',
                'h1[class*="results"]',
                'span[class*="results"]',
                'div[class*="results-summary"]',
                'div[class*="listing-counter"]',
                'strong[class*="results"]',
                '.results__title',
                '[class*="Title"]',
                'h1',
                'h2'
            ]
            
            for seletor in seletores:
                try:
                    elementos = await page.query_selector_all(seletor)
                    for elemento in elementos:
                        texto = await elemento.text_content()
                        if texto and ('imóve' in texto.lower() or 'resultado' in texto.lower() or 'anúncio' in texto.lower()):
                            total_imoveis = texto.strip()
                            logger.info(f"📊 Total encontrado: {total_imoveis}")
                            break
                    if total_imoveis:
                        break
                except:
                    continue
            
            # Se ainda não encontrou, tentar capturar via JavaScript
            if not total_imoveis:
                try:
                    total_imoveis = await page.evaluate('''
                        () => {
                            const elements = document.querySelectorAll('*');
                            for (let el of elements) {
                                const text = el.textContent || '';
                                if (text.match(/\\d+\\s*(imóveis?|resultados?|anúncios?)/i)) {
                                    return text.trim();
                                }
                            }
                            return null;
                        }
                    ''')
                    if total_imoveis:
                        logger.info(f"📊 Total encontrado via JS: {total_imoveis}")
                except:
                    pass
                    
        except Exception as e:
            logger.warning(f"⚠️ Não foi possível capturar total de imóveis: {e}")
        
        # Limpar e normalizar URL
        # Decodificar caracteres especiais
        url_atual = urllib.parse.unquote(url_atual)
        
        # Remover parâmetros de query
        if '?' in url_atual:
            url_atual = url_atual.split('?')[0]
        
        # Garantir que termina com /
        if not url_atual.endswith('/'):
            url_atual += '/'
        
        logger.info(f"✅ Captura direta bem-sucedida: {url_atual}")
        
        return {
            'link_capturado': url_atual,
            'titulo': titulo or f"Imóveis para {tipo_operacao} em {cidade}, {estado}",
            'total_imoveis': total_imoveis
        }
        
    except Exception as e:
        logger.error(f"❌ Erro na captura direta: {e}")
        return None
    
    finally:
        # Limpar recursos
        if page:
            await page.close()
        if browser:
            await browser.close()
        if playwright:
            await playwright.stop()

def salvar_link_unico(resultado: ResultadoBuscaUnica):
    """Salva o link único no banco MariaDB"""
    try:
        # Busca IDs necessários
        plataforma_id = get_plataforma_id(resultado.plataforma)
        tipo_busca_id = get_tipo_busca_id(resultado.tipo_operacao)
        
        if not plataforma_id or not tipo_busca_id:
            logger.error(f"Plataforma ou tipo de busca não encontrado")
            return False
        
        # Busca cidade e estado
        cidade_result = db.execute_query(
            "SELECT m.id as municipio_id, e.id as estado_id FROM municipios m JOIN estados e ON m.estado_id = e.id WHERE m.nome = %s AND e.sigla = %s",
            (resultado.cidade, resultado.estado)
        )
        
        if not cidade_result:
            logger.error(f"Cidade {resultado.cidade}/{resultado.estado} não encontrada")
            return False
        
        municipio_id = cidade_result[0]['municipio_id']
        estado_id = cidade_result[0]['estado_id']
        
        # Verifica se já existe um link para esta combinação
        existe = db.execute_query(
            "SELECT id FROM links_duckduckgo WHERE plataforma_id = %s AND tipo_busca_id = %s AND estado_id = %s AND municipio_id = %s",
            (plataforma_id, tipo_busca_id, estado_id, municipio_id)
        )
        
        if existe:
            # Atualiza o link existente
            update_query = """
                UPDATE links_duckduckgo 
                SET url = %s, updated_at = NOW()
                WHERE plataforma_id = %s AND tipo_busca_id = %s AND estado_id = %s AND municipio_id = %s
            """
            db.execute_update(update_query, (
                resultado.link_unico,
                plataforma_id, tipo_busca_id, estado_id, municipio_id
            ))
            logger.info(f"Link atualizado para {resultado.cidade}/{resultado.estado}")
        else:
            # Insere novo link
            insert_query = """
                INSERT INTO links_duckduckgo 
                (url, plataforma_id, tipo_busca_id, estado_id, municipio_id, 
                 distrito_id, termo_busca, posicao_busca, processado, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """
            db.execute_update(insert_query, (
                resultado.link_unico,
                plataforma_id,
                tipo_busca_id,
                estado_id,
                municipio_id,
                None,  # distrito_id
                f"{resultado.tipo_operacao} {resultado.cidade} {resultado.estado}",  # termo_busca
                1,  # posicao_busca (sempre 1 para link único)
                0  # processado
            ))
            logger.info(f"Novo link inserido para {resultado.cidade}/{resultado.estado}")
        
        # Registra no log de busca
        try:
            log_query = """
                INSERT INTO logs_busca 
                (motor_busca, query, plataforma_id, municipio_id, 
                 links_encontrados, links_salvos, data_execucao, observacao)
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s)
            """
            db.execute_update(log_query, (
                'webui',
                f"{resultado.tipo_operacao} {resultado.cidade} {resultado.estado}",
                plataforma_id,
                municipio_id,
                1,  # sempre 1 link único
                1,  # sempre 1 link salvo
                f"Link único encontrado: {resultado.link_unico}"
            ))
        except Exception as e:
            logger.warning(f"Erro ao salvar log: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"Erro ao salvar link único: {e}")
        return False

@app.get("/")
async def root():
    return {
        "message": "API de Imóveis VivaReal - MariaDB",
        "version": "2.0.0",
        "endpoints": {
            "status": "/status",
            "cidades": "/cidades-ativas",
            "buscar-unico": "/buscar-link-unico",
            "docs": "/docs"
        }
    }

@app.get("/status")
async def status():
    """Verificar status da API e conectividade com banco"""
    try:
        # Testa conexão com banco
        cidades = get_cidades_ativas()
        plataformas = get_plataformas_ativas()
        
        return {
            "status": "online",
            "timestamp": datetime.now().isoformat(),
            "llm_configured": bool(os.getenv("OPENAI_API_KEY")),
            "browser_available": True,
            "database_connected": True,
            "cidades_ativas": len(cidades),
            "plataformas_ativas": len(plataformas)
        }
    except Exception as e:
        return {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

@app.get("/cidades-ativas")
async def cidades_ativas():
    """Lista todas as cidades ativas do banco"""
    try:
        cidades = get_cidades_ativas()
        return {
            "total": len(cidades),
            "cidades": cidades
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar cidades: {str(e)}")

@app.post("/buscar-link-unico", response_model=ResultadoBuscaUnica)
async def buscar_link_unico(busca: BuscaUnica):
    """
    Busca APENAS O LINK ÚNICO da página principal de imóveis
    para uma cidade específica, não todas as variações
    """
    browser_context = None
    playwright = None
    use_agent = True  # Flag para decidir se usa Agent ou captura direta
    
    try:
        logger.info(f"🔍 Buscando link único: {busca.tipo_operacao} em {busca.cidade}, {busca.estado}")
        
        # Construir URL esperada
        cidade_formatada = busca.cidade.lower().replace(" ", "-")
        estado_formatado = busca.estado.lower()
        url_esperada = f"https://www.vivareal.com.br/{busca.tipo_operacao}/{estado_formatado}/{cidade_formatada}/"
        
        logger.info(f"📍 URL esperada: {url_esperada}")
        
        json_data = None
        
        # Tentar primeiro com captura direta (mais rápido e confiável)
        if not use_agent or True:  # Forçar uso da captura direta por enquanto
            logger.info("🎯 Usando captura direta com Playwright...")
            dados_capturados = await capturar_link_direto(
                busca.cidade, 
                busca.estado, 
                busca.tipo_operacao
            )
            
            if dados_capturados:
                json_data = dados_capturados
                logger.info(f"✅ Captura direta bem-sucedida: {json_data}")
        
        # Se a captura direta falhar, tentar com o Agent
        if not json_data and use_agent:
            logger.info("🤖 Tentando com Agent browser_use...")
            
            try:
                # Configurar o agente
                llm = get_llm()
                
                # Criar contexto do navegador explicitamente
                logger.info("🌐 Iniciando navegador para Agent...")
                playwright = await async_playwright().start()
                browser = await playwright.chromium.launch(headless=True)
                browser_context = await BrowserContext.from_browser(browser)
                
                # Criar tarefa simplificada
                task = f"""
                Acesse {url_esperada} e capture:
                1. A URL atual da página
                2. O título da página
                3. O número total de imóveis (se disponível)
                
                Retorne APENAS um JSON:
                {{
                    "link_capturado": "URL_DA_PAGINA",
                    "titulo": "TITULO",
                    "total_imoveis": "NUMERO_OU_NULL"
                }}
                """
                
                # Executar a tarefa
                agent = Agent(
                    task=task,
                    llm=llm,
                    browser_context=browser_context
                )
                
                result = await agent.run()
                
                # Processar resultado do Agent
                logger.info(f"📊 Tipo de resultado do Agent: {type(result)}")
                
                # Tentar extrair dados do Agent
                if isinstance(result, str):
                    logger.info("📝 Resultado é string direta")
                    try:
                        start_idx = result.find('{')
                        end_idx = result.rfind('}') + 1
                        if start_idx != -1 and end_idx > start_idx:
                            json_str = result[start_idx:end_idx]
                            json_data = json.loads(json_str)
                            logger.info(f"✅ JSON extraído da string: {json_data}")
                    except Exception as e:
                        logger.warning(f"⚠️ Erro ao extrair JSON da string: {e}")
                
                elif hasattr(result, 'final_result'):
                    logger.info("📝 Resultado tem final_result")
                    try:
                        final = result.final_result
                        if isinstance(final, str):
                            start_idx = final.find('{')
                            end_idx = final.rfind('}') + 1
                            if start_idx != -1 and end_idx > start_idx:
                                json_str = final[start_idx:end_idx]
                                json_data = json.loads(json_str)
                                logger.info(f"✅ JSON extraído do final_result: {json_data}")
                        elif isinstance(final, dict):
                            json_data = final
                            logger.info(f"✅ final_result já é dict: {json_data}")
                    except Exception as e:
                        logger.warning(f"⚠️ Erro ao processar final_result: {e}")
                
                elif hasattr(result, 'all_results'):
                    logger.info(f"📝 Resultado tem all_results: {len(result.all_results)} itens")
                    for action_result in reversed(result.all_results):
                        if hasattr(action_result, 'extracted_content') and action_result.extracted_content:
                            try:
                                content = str(action_result.extracted_content)
                                logger.info(f"📄 Tentando extrair de: {content[:200]}...")
                                start_idx = content.find('{')
                                end_idx = content.rfind('}') + 1
                                if start_idx != -1 and end_idx > start_idx:
                                    json_str = content[start_idx:end_idx]
                                    json_data = json.loads(json_str)
                                    logger.info(f"✅ JSON extraído de all_results: {json_data}")
                                    break
                            except Exception as e:
                                logger.warning(f"⚠️ Erro ao processar action_result: {e}")
                                continue
                
            except Exception as e:
                logger.error(f"❌ Erro ao usar Agent: {e}")
        
        # Se conseguimos extrair dados JSON
        if json_data:
            try:
                # Processar dados capturados
                link_capturado = json_data.get('link_capturado', '')
                titulo = json_data.get('titulo', '')
                total_imoveis = json_data.get('total_imoveis')
                
                # Validar e limpar o link
                if not link_capturado or 'vivareal.com.br' not in link_capturado:
                    # Se não capturou corretamente, usar o link esperado
                    cidade_formatada = busca.cidade.lower().replace(" ", "-")
                    estado_formatado = busca.estado.lower()
                    link_capturado = f"https://www.vivareal.com.br/{busca.tipo_operacao}/{estado_formatado}/{cidade_formatada}/"
                    logger.warning(f"⚠️ Link não capturado corretamente, usando padrão: {link_capturado}")
                
                # Limpar o link (remover parâmetros desnecessários)
                if '?' in link_capturado:
                    link_capturado = link_capturado.split('?')[0]
                
                # Garantir que termina com /
                if not link_capturado.endswith('/'):
                    link_capturado += '/'
                
                logger.info(f"✅ Link final processado: {link_capturado}")
                
                # Criar objeto de resultado
                resultado_obj = ResultadoBuscaUnica(
                    cidade=busca.cidade,
                    estado=busca.estado,
                    tipo_operacao=busca.tipo_operacao,
                    plataforma=busca.plataforma,
                    link_unico=link_capturado,
                    titulo_pagina=titulo or f"Imóveis para {busca.tipo_operacao} em {busca.cidade}, {busca.estado}",
                    total_imoveis=str(total_imoveis) if total_imoveis else "N/A",
                    data_busca=datetime.now().isoformat(),
                    status="sucesso",
                    observacoes="Link capturado com sucesso pelo agente"
                )
                
                # Salvar no banco MariaDB
                if salvar_link_unico(resultado_obj):
                    logger.info(f"✅ Link único salvo no banco: {resultado_obj.link_unico}")
                else:
                    logger.warning("⚠️ Erro ao salvar no banco, mas retornando resultado")
                
                return resultado_obj
                
            except Exception as e:
                logger.error(f"❌ Erro ao processar dados JSON: {e}")
        
        # Se não conseguimos extrair nada, criar resultado padrão
        logger.warning("⚠️ Não foi possível extrair dados do agente, usando link padrão")
        cidade_formatada = busca.cidade.lower().replace(" ", "-")
        estado_formatado = busca.estado.lower()
        link_padrao = f"https://www.vivareal.com.br/{busca.tipo_operacao}/{estado_formatado}/{cidade_formatada}/"
        
        resultado_padrao = ResultadoBuscaUnica(
            cidade=busca.cidade,
            estado=busca.estado,
            tipo_operacao=busca.tipo_operacao,
            plataforma=busca.plataforma,
            link_unico=link_padrao,
            titulo_pagina=f"Imóveis para {busca.tipo_operacao} em {busca.cidade}, {busca.estado}",
            total_imoveis="N/A",
            data_busca=datetime.now().isoformat(),
            status="sucesso",
            observacoes="Link padrão gerado (agente não retornou dados)"
        )
        
        # Tentar salvar no banco
        salvar_link_unico(resultado_padrao)
        
        return resultado_padrao
            
    except Exception as e:
        logger.error(f"❌ Erro na busca: {e}")
        import traceback
        logger.error(f"Stack trace: {traceback.format_exc()}")
        
        # Em caso de erro, ainda tentar retornar um link padrão
        try:
            cidade_formatada = busca.cidade.lower().replace(" ", "-")
            estado_formatado = busca.estado.lower()
            link_padrao = f"https://www.vivareal.com.br/{busca.tipo_operacao}/{estado_formatado}/{cidade_formatada}/"
            
            resultado_erro = ResultadoBuscaUnica(
                cidade=busca.cidade,
                estado=busca.estado,
                tipo_operacao=busca.tipo_operacao,
                plataforma=busca.plataforma,
                link_unico=link_padrao,
                titulo_pagina=f"Imóveis para {busca.tipo_operacao} em {busca.cidade}, {busca.estado}",
                total_imoveis="N/A",
                data_busca=datetime.now().isoformat(),
                status="erro",
                observacoes=f"Erro no agente: {str(e)[:200]}. Link padrão retornado."
            )
            
            # Tentar salvar mesmo com erro
            salvar_link_unico(resultado_erro)
            
            return resultado_erro
        except:
            raise HTTPException(status_code=500, detail=f"Erro na busca: {str(e)}")
    
    finally:
        # Limpar recursos do navegador
        if browser_context:
            try:
                await browser_context.close()
                logger.info("🧹 Contexto do navegador fechado")
            except:
                pass
        if playwright:
            try:
                await playwright.stop()
                logger.info("🧹 Playwright finalizado")
            except:
                pass

@app.get("/links-salvos")
async def links_salvos():
    """Lista todos os links únicos salvos no banco"""
    try:
        query = """
            SELECT l.url, l.created_at, l.updated_at, l.termo_busca,
                   p.nome as plataforma, t.nome as tipo_busca, 
                   e.sigla as estado, m.nome as cidade
            FROM links_duckduckgo l
            JOIN plataformas p ON l.plataforma_id = p.id
            JOIN tipos_busca t ON l.tipo_busca_id = t.id
            JOIN estados e ON l.estado_id = e.id
            JOIN municipios m ON l.municipio_id = m.id
            ORDER BY l.created_at DESC
        """
        links = db.execute_query(query)
        
        return {
            "total": len(links),
            "links": links
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar links: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8002)  # Porta 8002 para não conflitar
