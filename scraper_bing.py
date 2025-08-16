import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
import time
from scraper_melhorado import ScraperAntiDetection
from database import db, get_plataformas_ativas
from database_queries import get_estados, get_municipios_por_estado
from playwright.async_api import Page

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper_bing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class BingScraper(ScraperAntiDetection):
    """Scraper otimizado para Bing"""
    
    async def perform_bing_search(self, query: str, max_retries: int = 3) -> List[str]:
        """Realiza busca no Bing com menos restrições e fallback"""
        all_links = []
        original_query = query
        
        # Tenta primeiro com a query original, depois sem "site:" se necessário
        queries_to_try = [query]
        if "site:" in query:
            # Adiciona versão sem site: como fallback
            # Extrai a parte após site:dominio
            parts = query.split("site:")
            if len(parts) > 1:
                # Pega tudo após o domínio (ignora o primeiro espaço após o domínio)
                domain_and_rest = parts[1].strip()
                # Encontra o primeiro espaço para separar domínio do resto
                first_space = domain_and_rest.find(' ')
                if first_space > 0:
                    # Pega apenas o que vem depois do domínio
                    query_without_site = domain_and_rest[first_space:].strip()
                    
                    # Adiciona o nome do domínio como palavra-chave se possível
                    domain = domain_and_rest[:first_space].strip()
                    if '.' in domain:
                        # Extrai nome do site (ex: "zapimoveis" de "zapimoveis.com.br")
                        site_name = domain.split('.')[0]
                        query_without_site = f"{site_name} {query_without_site}"
                    
                    queries_to_try.append(query_without_site)
                    logger.info(f"Query fallback preparada: {query_without_site}")
        
        for query_variant in queries_to_try:
            for attempt in range(max_retries):
                browser = None
                playwright = None
                try:
                    logger.info(f"Tentativa {attempt + 1}/{max_retries} para: {query_variant}")
                    
                    # Cria navegador em modo headless
                    playwright, browser, context, page = await self.create_stealth_browser(headless=True)
                    
                    # Rate limiting mais suave para Bing
                    await self.rate_limit('bing.com', min_delay=2.0, max_delay=4.0)
                    
                    # Navega para o Bing
                    await page.goto('https://www.bing.com', wait_until='domcontentloaded', timeout=30000)
                    
                    # Aguarda um pouco para página carregar completamente
                    await asyncio.sleep(3)
                    
                    # Busca campo de pesquisa do Bing com mais seletores
                    search_selectors = [
                        'input[name="q"]',
                        'input#sb_form_q',
                        'textarea[name="q"]',
                        'input[type="search"]',
                        'input.b_searchbox',
                        '#sb_form input[type="text"]'
                    ]
                    
                    search_field = None
                    for selector in search_selectors:
                        try:
                            search_field = await page.wait_for_selector(selector, timeout=3000)
                            if search_field:
                                logger.info(f"Campo de busca encontrado: {selector}")
                                break
                        except:
                            continue
                    
                    if not search_field:
                        # Captura screenshot para debug
                        await page.screenshot(path=f'bing_debug_search_field_{attempt}.png')
                        raise Exception("Campo de busca não encontrado")
                    
                    # Digita a query de forma mais natural
                    await search_field.click()
                    await asyncio.sleep(0.5)
                    await page.keyboard.type(query_variant, delay=100)  # Digita com delay entre teclas
                    await asyncio.sleep(1)
                    
                    # Pressiona Enter
                    await page.keyboard.press('Enter')
                    
                    # Aguarda resultados do Bing com timeout maior
                    try:
                        await page.wait_for_selector('li.b_algo, div.b_algo, #b_results, .b_content', timeout=15000)
                        logger.info("Resultados carregados, aguardando mais um pouco...")
                    except:
                        logger.warning("Timeout esperando resultados, capturando screenshot e tentando extrair...")
                        await page.screenshot(path=f'bing_debug_results_{attempt}.png')
                    
                    # Aguarda mais tempo para garantir que todos resultados carreguem
                    await asyncio.sleep(5)
                    
                    # Log do HTML para debug
                    page_content = await page.content()
                    if 'b_algo' in page_content:
                        logger.info("Encontrado conteúdo b_algo na página")
                    else:
                        logger.warning("Conteúdo b_algo NÃO encontrado na página")
                    
                    # Extrai links do Bing
                    links = await self._extract_bing_links(page)
                    
                    if links:
                        logger.info(f"✅ Sucesso! {len(links)} links extraídos do Bing com query: {query_variant}")
                        all_links.extend(links)
                        
                        # Se encontrou links suficientes, retorna
                        if len(all_links) >= 5:
                            return all_links[:20]  # Limita a 20 links
                    else:
                        logger.warning(f"Nenhum link encontrado na tentativa {attempt + 1}")
                        # Captura screenshot para debug quando não encontra links
                        await page.screenshot(path=f'bing_debug_no_links_{attempt}.png')
                    
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Erro na tentativa {attempt + 1}: {e}")
                    if attempt == max_retries - 1 and "site:" in query_variant:
                        logger.info("Tentando sem 'site:' restriction...")
                    await asyncio.sleep(3)
                finally:
                    if browser:
                        await browser.close()
                    if playwright:
                        await playwright.stop()
            
            # Se encontrou alguns links, não tenta a próxima variação
            if all_links:
                break
        
        if not all_links:
            logger.error(f"Falha após todas as tentativas para: {original_query}")
        
        return all_links
    
    async def _extract_bing_links(self, page: Page) -> List[str]:
        """Extrai links dos resultados do Bing com múltiplos seletores"""
        # Primeiro, tenta extrair informações de debug
        debug_info = await page.evaluate("""
            () => {
                const info = {
                    total_b_algo: document.querySelectorAll('.b_algo').length,
                    total_li_b_algo: document.querySelectorAll('li.b_algo').length,
                    total_div_b_algo: document.querySelectorAll('div.b_algo').length,
                    total_h2_links: document.querySelectorAll('.b_algo h2 a').length,
                    total_cite_links: document.querySelectorAll('.b_algo cite').length,
                    total_any_links: document.querySelectorAll('a[href]').length
                };
                console.log('Debug Info:', info);
                return info;
            }
        """)
        
        logger.info(f"Debug - Elementos encontrados: {debug_info}")
        
        # Extrai links com múltiplos seletores
        links = await page.evaluate("""
            () => {
                const links = new Set();
                const debugLog = [];
                
                // Lista expandida de seletores para o Bing
                const selectors = [
                    // Seletores principais do Bing
                    'li.b_algo h2 a',
                    'div.b_algo h2 a',
                    '.b_algo h2 a',
                    
                    // Seletores alternativos
                    '.b_algo .b_title a',
                    '.b_algo > h2 > a',
                    '.b_content h2 a',
                    
                    // Seletores mais genéricos
                    '.b_algo a[href]',
                    '#b_results .b_algo a',
                    'ol#b_results li h2 a',
                    
                    // Novos seletores para formato atualizado do Bing
                    '.b_algo .b_algoheader a',
                    '.b_algo .b_attribution cite',
                    'article h2 a',
                    '.b_pag a.b_widePag',
                    
                    // Seletores para resultados especiais
                    '.b_ans .b_algo a',
                    '.b_web .b_algo a'
                ];
                
                // Tenta cada seletor
                for (const selector of selectors) {
                    try {
                        const elements = document.querySelectorAll(selector);
                        if (elements.length > 0) {
                            debugLog.push(`Seletor '${selector}' encontrou ${elements.length} elementos`);
                            
                            elements.forEach(element => {
                                let href = element.href;
                                
                                // Verifica se é um link válido
                                if (href && 
                                    href.startsWith('http') && 
                                    !href.includes('bing.com') && 
                                    !href.includes('microsoft.com') &&
                                    !href.includes('msn.com') &&
                                    !href.includes('javascript:') &&
                                    !href.includes('about:blank')) {
                                    
                                    // Adiciona o link
                                    links.add(href);
                                }
                            });
                        }
                    } catch (e) {
                        debugLog.push(`Erro no seletor '${selector}': ${e.message}`);
                    }
                }
                
                // Se ainda não encontrou links, tenta método alternativo com cite
                if (links.size === 0) {
                    debugLog.push('Tentando extrair URLs de elementos cite...');
                    
                    document.querySelectorAll('.b_algo cite, .b_attribution cite').forEach(element => {
                        const text = element.textContent || element.innerText;
                        if (text) {
                            // Tenta construir URL a partir do texto do cite
                            let url = text.trim();
                            if (!url.startsWith('http')) {
                                url = 'https://' + url;
                            }
                            // Remove trailing › ou outros caracteres
                            url = url.replace(/[›»].*$/, '').trim();
                            
                            try {
                                const urlObj = new URL(url);
                                if (urlObj.hostname && !urlObj.hostname.includes('bing.com')) {
                                    links.add(url);
                                    debugLog.push(`URL extraída de cite: ${url}`);
                                }
                            } catch (e) {
                                // URL inválida, ignora
                            }
                        }
                    });
                }
                
                // Último recurso: busca todos os links e filtra
                if (links.size === 0) {
                    debugLog.push('Último recurso: buscando todos os links...');
                    
                    document.querySelectorAll('a[href]').forEach(element => {
                        let href = element.href;
                        const text = element.textContent || '';
                        
                        // Apenas links que parecem ser resultados de busca
                        if (href && 
                            href.startsWith('http') && 
                            !href.includes('bing.com') && 
                            !href.includes('microsoft.com') &&
                            !href.includes('msn.com') &&
                            !href.includes('javascript:') &&
                            !href.includes('#') &&
                            text.length > 10) {  // Tem algum texto significativo
                            
                            links.add(href);
                        }
                    });
                }
                
                // Remove duplicatas e links indesejados
                const cleanLinks = Array.from(links).filter(link => {
                    return !link.includes('/aclk?') && 
                           !link.includes('googleadservices') &&
                           !link.includes('doubleclick') &&
                           !link.includes('bing.com/ck/a') &&
                           !link.includes('account.microsoft') &&
                           !link.includes('login.live.com') &&
                           link.length < 500;  // Remove links muito longos (geralmente tracking)
                });
                
                console.log('Debug Log:', debugLog);
                console.log('Links encontrados (antes da limpeza):', Array.from(links));
                console.log('Links limpos finais:', cleanLinks);
                
                return cleanLinks;
            }
        """)
        
        logger.info(f"Total de links extraídos: {len(links)}")
        if links:
            logger.info(f"Primeiros 3 links: {links[:3]}")
        
        return links


class ScraperBingMariaDB:
    """Sistema de scraping usando Bing com MariaDB"""
    
    def __init__(self):
        self.bing_scraper = BingScraper()
        self.running = True
        self.ciclo_numero = 0
        self.tipos_busca = self.get_tipos_busca_do_banco()
        self.palavras_chave = {
            'ALUGUEL': ['apartamento aluguel', 'casa aluguel'],
            'VENDA': ['apartamento venda', 'casa venda'],
            'ALUGUEL_COMERCIAL': ['sala comercial aluguel', 'loja aluguel'],
            'VENDA_COMERCIAL': ['sala comercial venda', 'loja venda']
        }
    
    def get_tipos_busca_do_banco(self):
        """Busca tipos de busca ativos do banco"""
        try:
            result = db.execute_query("""
                SELECT id, nome FROM tipos_busca 
                ORDER BY nome
            """)
            tipos = {}
            for r in result:
                tipos[r['nome']] = r['id']
            logger.info(f"Tipos de busca encontrados: {list(tipos.keys())}")
            return tipos
        except:
            # Se não conseguir, usa padrão
            logger.warning("Usando tipos de busca padrão")
            return {'ALUGUEL': 1, 'VENDA': 2}
    
    def get_configuracoes_ativas(self) -> List[Dict]:
        """Busca configurações ativas do banco MariaDB"""
        configuracoes = []
        
        try:
            # Busca plataformas ativas
            plataformas = get_plataformas_ativas()
            logger.info(f"Encontradas {len(plataformas)} plataformas ativas")
            
            # Busca municípios ativos
            query_municipios = """
                SELECT m.id, m.nome, m.estado_id, 
                       e.nome as estado_nome, e.sigla as estado_sigla
                FROM municipios m
                JOIN estados e ON m.estado_id = e.id
                WHERE m.ativo = 1 AND e.ativo = 1
                ORDER BY e.sigla, m.nome
                LIMIT 10
            """
            municipios_ativos = db.execute_query(query_municipios)
            logger.info(f"Encontrados {len(municipios_ativos)} municípios ativos")
            
            # Gera configurações
            for plataforma in plataformas[:2]:  # 2 plataformas
                for municipio in municipios_ativos[:3]:  # 3 municípios
                    for tipo_busca_nome, tipo_busca_id in self.tipos_busca.items():
                        palavras = self.palavras_chave.get(tipo_busca_nome, ['imovel'])
                        for palavra in palavras[:1]:  # 1 palavra
                            configuracoes.append({
                                'plataforma_id': plataforma['id'],
                                'plataforma_nome': plataforma['nome'],
                                'plataforma_url': plataforma['url_base'],
                                'estado_id': municipio['estado_id'],
                                'estado_nome': municipio['estado_nome'],
                                'estado_sigla': municipio['estado_sigla'],
                                'municipio_id': municipio['id'],
                                'municipio_nome': municipio['nome'],
                                'tipo_busca': tipo_busca_nome,
                                'tipo_busca_id': tipo_busca_id,
                                'palavras_chave': palavra
                            })
            
            logger.info(f"Geradas {len(configuracoes)} configurações")
            return configuracoes
            
        except Exception as e:
            logger.error(f"Erro ao buscar configurações: {e}")
            return []
    
    def gerar_query_bing(self, config: Dict) -> str:
        """Gera query para o Bing com múltiplas variações"""
        url_base = config['plataforma_url']
        if url_base.startswith('http://'):
            url_base = url_base[7:]
        elif url_base.startswith('https://'):
            url_base = url_base[8:]
        if url_base.endswith('/'):
            url_base = url_base[:-1]
        
        # Query principal com site:
        query = f"site:{url_base} {config['palavras_chave']} {config['municipio_nome']} {config['estado_sigla']}"
        
        # Log para debug
        logger.info(f"Query gerada: {query}")
        
        return query
    
    def gerar_query_alternativa(self, config: Dict) -> str:
        """Gera query alternativa sem site: para fallback"""
        plataforma_nome = config['plataforma_nome'].lower()
        
        # Remove palavras comuns de nomes de plataformas
        plataforma_nome = plataforma_nome.replace('imóveis', '').replace('imoveis', '').strip()
        
        # Query alternativa sem site: mas com nome da plataforma
        query = f"{plataforma_nome} {config['palavras_chave']} {config['municipio_nome']} {config['estado_sigla']}"
        
        logger.info(f"Query alternativa gerada: {query}")
        
        return query
    
    def salvar_resultado(self, config: Dict, query: str, links: List[str]):
        """Salva resultado na tabela links_duckduckgo"""
        try:
            if not links:
                logger.warning("Nenhum link para salvar")
                return
            
            # Usa o tipo_busca_id que já vem da configuração
            tipo_busca_id = config.get('tipo_busca_id')
            if not tipo_busca_id:
                # Se não tiver, tenta buscar pelo nome
                try:
                    result = db.execute_query(
                        "SELECT id FROM tipos_busca WHERE nome = %s",
                        (config['tipo_busca'],)
                    )
                    if result:
                        tipo_busca_id = result[0]['id']
                except:
                    pass
            
            # Prepara dados para salvar
            saved_count = 0
            for posicao, link in enumerate(links, 1):
                try:
                    # Verifica se o link já existe
                    existe = db.execute_query(
                        "SELECT id FROM links_duckduckgo WHERE url = %s",
                        (link,)
                    )
                    
                    if not existe:
                        # Insere o link
                        insert_query = """
                            INSERT INTO links_duckduckgo 
                            (url, plataforma_id, tipo_busca_id, estado_id, municipio_id, 
                             distrito_id, termo_busca, posicao_busca, processado, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                        """
                        
                        db.execute_update(insert_query, (
                            link,
                            config['plataforma_id'],
                            tipo_busca_id,
                            config['estado_id'],
                            config['municipio_id'],
                            None,  # distrito_id
                            query,  # termo_busca completo
                            posicao,  # posição nos resultados
                            0  # processado = false
                        ))
                        saved_count += 1
                        
                except Exception as e:
                    logger.error(f"Erro ao salvar link {link}: {e}")
                    continue
            
            logger.info(f"✅ Salvos {saved_count}/{len(links)} links em links_duckduckgo")
            
            # Registra busca no log
            try:
                log_query = """
                    INSERT INTO logs_busca 
                    (motor_busca, query, plataforma_id, municipio_id, 
                     links_encontrados, links_salvos, data_execucao)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                """
                db.execute_update(log_query, (
                    'bing',
                    query,
                    config['plataforma_id'],
                    config['municipio_id'],
                    len(links),
                    saved_count
                ))
            except:
                # Se a tabela não existe, cria
                try:
                    create_log = """
                        CREATE TABLE IF NOT EXISTS logs_busca (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            motor_busca VARCHAR(50),
                            query TEXT,
                            plataforma_id INT,
                            municipio_id INT,
                            links_encontrados INT,
                            links_salvos INT,
                            data_execucao DATETIME,
                            observacao TEXT,
                            INDEX idx_data (data_execucao)
                        )
                    """
                    db.execute_update(create_log)
                    
                    # Tenta adicionar a coluna observacao se não existir
                    try:
                        db.execute_update("ALTER TABLE logs_busca ADD COLUMN observacao TEXT")
                    except:
                        pass  # Coluna já existe
                    
                    db.execute_update(log_query, (
                        'bing',
                        query,
                        config['plataforma_id'],
                        config['municipio_id'],
                        len(links),
                        saved_count
                    ))
                except Exception as e:
                    logger.debug(f"Erro ao criar/atualizar tabela logs_busca: {e}")
            
        except Exception as e:
            logger.error(f"Erro ao salvar resultado: {e}")
    
    async def processar_configuracao(self, config: Dict):
        """Processa uma configuração com fallback inteligente"""
        nome = f"{config['plataforma_nome']} - {config['municipio_nome']}/{config['estado_sigla']}"
        logger.info(f"🔍 Buscando no Bing: {nome}")
        
        # Gera query principal
        query = self.gerar_query_bing(config)
        logger.info(f"Query principal: {query}")
        
        try:
            # Busca no Bing (já tem fallback interno)
            links = await self.bing_scraper.perform_bing_search(query)
            
            # Se não encontrou links e a query tinha site:, tenta query alternativa explícita
            if not links and "site:" in query:
                logger.warning("Nenhum link encontrado com site:, tentando query alternativa...")
                query_alt = self.gerar_query_alternativa(config)
                links = await self.bing_scraper.perform_bing_search(query_alt)
                
                if links:
                    logger.info(f"✅ Query alternativa funcionou! {len(links)} links encontrados")
                    query = query_alt  # Usa a query alternativa para salvar
            
            # Salva resultado se encontrou links
            if links:
                self.salvar_resultado(config, query, links)
                logger.info(f"✅ Total de {len(links)} links processados")
            else:
                logger.warning(f"⚠️ Nenhum link encontrado para {nome}")
                
                # Registra no log mesmo sem resultados
                try:
                    log_query = """
                        INSERT INTO logs_busca 
                        (motor_busca, query, plataforma_id, municipio_id, 
                         links_encontrados, links_salvos, data_execucao, observacao)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s)
                    """
                    db.execute_update(log_query, (
                        'bing',
                        query,
                        config['plataforma_id'],
                        config['municipio_id'],
                        0,
                        0,
                        'Nenhum resultado encontrado'
                    ))
                except:
                    pass
            
            # Aguarda entre buscas (mais tempo se não encontrou nada)
            tempo_espera = 30 if not links else 20
            logger.info(f"⏳ Aguardando {tempo_espera} segundos...")
            await asyncio.sleep(tempo_espera)
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar {nome}: {e}")
            await asyncio.sleep(15)  # Espera menor em caso de erro
    
    async def executar_ciclo(self):
        """Executa ciclo de buscas"""
        self.ciclo_numero += 1
        logger.info(f"\n{'='*60}")
        logger.info(f"🔍 CICLO BING #{self.ciclo_numero}")
        logger.info(f"{'='*60}\n")
        
        configuracoes = self.get_configuracoes_ativas()
        
        if not configuracoes:
            logger.warning("Nenhuma configuração")
            return
        
        logger.info(f"📋 {len(configuracoes)} configurações")
        
        for i, config in enumerate(configuracoes, 1):
            logger.info(f"\n[{i}/{len(configuracoes)}]")
            await self.processar_configuracao(config)
        
        logger.info(f"\n✅ CICLO #{self.ciclo_numero} CONCLUÍDO\n")
    
    async def run_forever(self):
        """Loop eterno"""
        logger.info("🔄 Iniciando Bing Scraper")
        logger.info("Ctrl+C para parar\n")
        
        try:
            while self.running:
                try:
                    await self.executar_ciclo()
                    
                    proxima = datetime.now() + timedelta(hours=3)
                    logger.info(f"⏰ Próxima: {proxima.strftime('%H:%M')}")
                    logger.info("💤 Aguardando 3 horas...")
                    
                    await asyncio.sleep(3 * 60 * 60)
                    
                except Exception as e:
                    logger.error(f"Erro: {e}")
                    await asyncio.sleep(300)
                    
        except KeyboardInterrupt:
            logger.info("\n👋 Finalizado")
            self.running = False


async def main():
    scraper = ScraperBingMariaDB()
    await scraper.run_forever()


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🔍 BING SCRAPER - MARIADB")
    print("="*60)
    print("✅ Usa Bing em vez de Google (menos bloqueios)")
    print("✅ Navegador visível para debug")
    print("✅ Salva no banco MariaDB")
    print("\nCtrl+C para parar")
    print("="*60 + "\n")
    
    asyncio.run(main())