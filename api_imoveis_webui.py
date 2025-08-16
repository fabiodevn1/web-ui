#!/usr/bin/env python3
"""
API de busca de imóveis usando WebUI (browser_use) para busca real na internet
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import json
from datetime import datetime
from browser_use import Agent
from src.utils.llm_provider import get_llm_model
import os
from dotenv import load_dotenv
from database import db, get_plataformas_ativas
import logging
from urllib.parse import quote, unquote

# Carregar variáveis de ambiente
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="API de Imóveis WebUI - Busca Real", version="3.0.0")

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
        
        return True
        
    except Exception as e:
        logger.error(f"Erro ao salvar link único: {e}")
        return False

@app.get("/")
async def root():
    return {
        "message": "API de Imóveis WebUI - Busca Real",
        "version": "3.0.0",
        "endpoints": {
            "status": "/status",
            "buscar-unico": "/buscar-link-unico",
            "docs": "/docs"
        }
    }

@app.get("/status")
async def status():
    """Verificar status da API"""
    try:
        return {
            "status": "online",
            "timestamp": datetime.now().isoformat(),
            "llm_configured": bool(os.getenv("OPENAI_API_KEY")),
            "browser_available": True,
            "database_connected": True
        }
    except Exception as e:
        return {
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }

@app.post("/buscar-link-unico", response_model=ResultadoBuscaUnica)
async def buscar_link_unico(busca: BuscaUnica):
    """
    Busca o link oficial do VivaReal através de pesquisa real na internet
    usando o browser_use Agent para navegar e encontrar a página correta
    """
    try:
        logger.info(f"🔍 Iniciando busca real para: {busca.tipo_operacao} em {busca.cidade}, {busca.estado}")
        
        # Configurar o agente
        llm = get_llm()
        
        # Criar tarefa detalhada para o Agent fazer busca real
        task = f"""
        Você é um assistente que precisa encontrar o link oficial do VivaReal para {busca.tipo_operacao} de imóveis em {busca.cidade}, {busca.estado}.

        INSTRUÇÕES DETALHADAS PASSO A PASSO:

        1. PESQUISE NA INTERNET:
           - Abra o DuckDuckGo (https://duckduckgo.com)
           - Pesquise por: "VivaReal {busca.tipo_operacao} imóveis {busca.cidade} {busca.estado}"
           - Ou pesquise: "site:vivareal.com.br {busca.tipo_operacao} {busca.cidade}"

        2. ENCONTRE O LINK CORRETO:
           - Nos resultados da busca, procure pelo link oficial do VivaReal
           - O link deve ser do domínio vivareal.com.br
           - Deve ser uma página de listagem de imóveis, não um imóvel específico
           - Clique no link para navegar até a página

        3. VERIFIQUE A PÁGINA:
           - Confirme que você está na página correta do VivaReal
           - Verifique se é a página de {busca.tipo_operacao} em {busca.cidade}
           - IMPORTANTE: Verifique se existem imóveis listados na página
           - Se não houver imóveis, tente buscar variações do nome da cidade

        4. CAPTURE AS INFORMAÇÕES:
           - URL da página atual (este é o link oficial que precisamos)
           - Título da página
           - Quantidade de imóveis disponíveis (geralmente aparece como "X imóveis encontrados")
           - Confirme que há imóveis reais sendo mostrados

        5. SE NÃO ENCONTRAR IMÓVEIS:
           - Tente buscar sem acentos: Araucária → Araucaria
           - Tente buscar com hífen: São Paulo → Sao-Paulo
           - Tente navegar manualmente no site do VivaReal usando o campo de busca

        IMPORTANTE:
        - NÃO construa o URL manualmente
        - SEMPRE faça a busca real e navegue até encontrar a página
        - VERIFIQUE se existem imóveis antes de retornar
        - Se não encontrar imóveis, tente diferentes variações

        Retorne APENAS um JSON com o seguinte formato:
        {{
            "cidade": "{busca.cidade}",
            "estado": "{busca.estado}",
            "tipo_operacao": "{busca.tipo_operacao}",
            "plataforma": "VivaReal",
            "link_unico": "[URL REAL DA PÁGINA QUE VOCÊ ESTÁ VENDO]",
            "titulo_pagina": "[TÍTULO DA PÁGINA]",
            "total_imoveis": "[QUANTIDADE DE IMÓVEIS ENCONTRADOS]",
            "data_busca": "{datetime.now().isoformat()}",
            "status": "sucesso",
            "observacoes": "Encontrados X imóveis na página"
        }}
        """
        
        logger.info("🤖 Iniciando Agent com browser_use...")
        
        # Executar a tarefa com o Agent
        agent = Agent(
            task=task,
            llm=llm
        )
        
        # Executar com mais passos para permitir navegação completa
        logger.info("🌐 Agent navegando e buscando...")
        result = await agent.run(max_steps=50)
        
        # Processar resultado
        if result and hasattr(result, 'all_results'):
            logger.info(f"📄 Agent retornou {len(result.all_results)} resultados")
            
            # Procurar pelo resultado final com JSON
            for action_result in result.all_results:
                if action_result.is_done and action_result.success and action_result.extracted_content:
                    content = str(action_result.extracted_content)
                    
                    # Tentar extrair JSON do conteúdo
                    try:
                        # Procurar por JSON no conteúdo
                        start_idx = content.find('{')
                        end_idx = content.rfind('}') + 1
                        
                        if start_idx != -1 and end_idx > start_idx:
                            json_str = content[start_idx:end_idx]
                            dados = json.loads(json_str)
                            
                            logger.info(f"✅ JSON extraído com sucesso")
                            logger.info(f"   Link: {dados.get('link_unico')}")
                            logger.info(f"   Total imóveis: {dados.get('total_imoveis')}")
                            
                            # Criar objeto de resultado
                            resultado = ResultadoBuscaUnica(**dados)
                            
                            # Salvar no banco
                            if salvar_link_unico(resultado):
                                logger.info(f"✅ Link salvo no banco de dados")
                            
                            return resultado
                            
                    except json.JSONDecodeError as e:
                        logger.warning(f"⚠️ Não foi possível extrair JSON: {e}")
                        continue
            
            # Se não encontrou JSON válido
            logger.error("❌ Agent não retornou um JSON válido")
            raise HTTPException(
                status_code=500,
                detail="Agent não conseguiu capturar as informações necessárias"
            )
        else:
            logger.error("❌ Agent não retornou resultado")
            raise HTTPException(
                status_code=500,
                detail="Agent não conseguiu completar a busca"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro na busca: {e}")
        raise HTTPException(status_code=500, detail=f"Erro na busca: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    print("🚀 Iniciando API de Busca Real com WebUI...")
    print("📌 Esta API faz buscas reais na internet usando browser_use")
    print("🌐 O navegador será aberto para realizar as buscas")
    print("⏳ Cada busca pode levar 1-2 minutos para ser concluída")
    print("-" * 60)
    uvicorn.run(app, host="127.0.0.1", port=8003)