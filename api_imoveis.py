from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import asyncio
import json
from datetime import datetime
from browser_use import BrowserUseAgent
from browser_use.utils import get_llm_model
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

app = FastAPI(title="API de Imóveis VivaReal", version="1.0.0")

class BuscaImoveis(BaseModel):
    cidade: str
    estado: str
    tipo_operacao: str = "venda"  # venda ou aluguel
    max_paginas: int = 3

class Imovel(BaseModel):
    titulo: str
    preco: str
    endereco: str
    area: str
    quartos: str
    banheiros: str
    vagas: str
    link: str
    data_anuncio: str
    descricao: str

class ResultadoBusca(BaseModel):
    cidade: str
    estado: str
    tipo_operacao: str
    total_imoveis: int
    imoveis: List[Imovel]
    data_busca: str
    url_fonte: str

# Configuração do LLM
def get_llm():
    try:
        return get_llm_model(
            provider="openai",
            model="gpt-4o",
            temperature=0.1,
            api_key=os.getenv("OPENAI_API_KEY")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao configurar LLM: {str(e)}")

@app.get("/")
async def root():
    return {"message": "API de Imóveis VivaReal - Use /docs para documentação"}

@app.post("/buscar-imoveis", response_model=ResultadoBusca)
async def buscar_imoveis(busca: BuscaImoveis):
    """
    Busca imóveis no VivaReal e retorna dados estruturados em JSON
    """
    try:
        # Configurar o agente
        llm = get_llm()
        
        # Criar tarefa para o agente
        task = f"""
        Acesse o site do VivaReal e busque imóveis para {busca.tipo_operacao} em {busca.cidade}, {busca.estado}.
        
        Instruções específicas:
        1. Vá para https://www.vivareal.com.br/{busca.tipo_operacao}/{busca.estado.lower()}/{busca.cidade.lower()}/
        2. Extraia informações dos primeiros {busca.max_paginas * 20} imóveis (aproximadamente {busca.max_paginas} páginas)
        3. Para cada imóvel, colete:
           - Título do anúncio
           - Preço
           - Endereço
           - Área
           - Número de quartos
           - Número de banheiros
           - Número de vagas de garagem
           - Link do anúncio
           - Data do anúncio
           - Descrição resumida
        
        4. Retorne os dados em formato JSON estruturado
        5. Se houver paginação, navegue pelas páginas para coletar mais dados
        
        Formato de retorno esperado:
        {{
            "cidade": "{busca.cidade}",
            "estado": "{busca.estado}",
            "tipo_operacao": "{busca.tipo_operacao}",
            "total_imoveis": 0,
            "imoveis": [
                {{
                    "titulo": "",
                    "preco": "",
                    "endereco": "",
                    "area": "",
                    "quartos": "",
                    "banheiros": "",
                    "vagas": "",
                    "link": "",
                    "data_anuncio": "",
                    "descricao": ""
                }}
            ],
            "data_busca": "",
            "url_fonte": ""
        }}
        """
        
        # Executar a tarefa
        agent = BrowserUseAgent(
            task=task,
            llm=llm,
            headless=False,  # False para debug, True para produção
            verbose=True
        )
        
        # Executar e aguardar resultado
        result = await agent.run()
        
        # Processar resultado
        if result and hasattr(result, 'output'):
            try:
                # Tentar extrair JSON do resultado
                output_text = str(result.output)
                
                # Procurar por JSON no output
                start_idx = output_text.find('{')
                end_idx = output_text.rfind('}') + 1
                
                if start_idx != -1 and end_idx != -1:
                    json_str = output_text[start_idx:end_idx]
                    dados = json.loads(json_str)
                    
                    # Validar e retornar
                    return ResultadoBusca(**dados)
                else:
                    # Se não encontrar JSON, criar estrutura básica
                    return ResultadoBusca(
                        cidade=busca.cidade,
                        estado=busca.estado,
                        tipo_operacao=busca.tipo_operacao,
                        total_imoveis=0,
                        imoveis=[],
                        data_busca=datetime.now().isoformat(),
                        url_fonte=f"https://www.vivareal.com.br/{busca.tipo_operacao}/{busca.estado.lower()}/{busca.cidade.lower()}/"
                    )
                    
            except json.JSONDecodeError as e:
                raise HTTPException(status_code=500, detail=f"Erro ao processar JSON: {str(e)}")
        else:
            raise HTTPException(status_code=500, detail="Agente não retornou resultado válido")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro na busca: {str(e)}")

@app.get("/status")
async def status():
    """Verificar status da API e conectividade"""
    return {
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "llm_configured": bool(os.getenv("OPENAI_API_KEY")),
        "browser_available": True
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
