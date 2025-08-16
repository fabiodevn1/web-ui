# 🏠 API de Imóveis VivaReal

API automatizada para busca e extração de dados de imóveis do VivaReal, com integração para salvar em banco de dados.

## 🚀 Funcionalidades

- ✅ **Busca Automatizada**: Usa IA para navegar e extrair dados do VivaReal
- ✅ **API REST**: Endpoint para buscar imóveis por cidade/estado
- ✅ **Banco de Dados**: Salva automaticamente em SQLite (configurável para outros)
- ✅ **Automação**: Scripts para busca periódica e agendada
- ✅ **JSON Estruturado**: Retorna dados organizados e prontos para uso

## 📋 Pré-requisitos

- Python 3.11+
- WebUI rodando na porta 7788
- Chave de API OpenAI configurada
- Playwright com Chromium instalado

## 🛠️ Instalação

1. **Instalar dependências**:
```bash
uv pip install fastapi uvicorn schedule requests
```

2. **Configurar variáveis de ambiente**:
```bash
cp .env.example .env
# Editar .env com sua chave OpenAI
```

## 🚀 Como Usar

### 1. Iniciar a API

```bash
# Terminal 1: WebUI (já rodando)
python webui.py --ip 127.0.0.1 --port 7788

# Terminal 2: API de Imóveis
python api_imoveis.py
```

A API estará disponível em: http://127.0.0.1:8000

### 2. Documentação Automática

Acesse: http://127.0.0.1:8000/docs

### 3. Exemplo de Uso

```python
import requests

# Buscar imóveis para venda em Araucária, PR
payload = {
    "cidade": "Araucaria",
    "estado": "PR",
    "tipo_operacao": "venda",
    "max_paginas": 3
}

response = requests.post(
    "http://127.0.0.1:8000/buscar-imoveis",
    json=payload
)

if response.status_code == 200:
    dados = response.json()
    print(f"Encontrados {dados['total_imoveis']} imóveis")
    
    for imovel in dados['imoveis']:
        print(f"- {imovel['titulo']}: {imovel['preco']}")
```

## 📊 Estrutura dos Dados

### Endpoint: POST /buscar-imoveis

**Request**:
```json
{
    "cidade": "Araucaria",
    "estado": "PR",
    "tipo_operacao": "venda",
    "max_paginas": 3
}
```

**Response**:
```json
{
    "cidade": "Araucaria",
    "estado": "PR",
    "tipo_operacao": "venda",
    "total_imoveis": 45,
    "imoveis": [
        {
            "titulo": "Casa 3 quartos com garagem",
            "preco": "R$ 350.000",
            "endereco": "Rua das Flores, 123",
            "area": "120m²",
            "quartos": "3",
            "banheiros": "2",
            "vagas": "2",
            "link": "https://www.vivareal.com.br/imovel/...",
            "data_anuncio": "2024-01-15",
            "descricao": "Casa bem localizada..."
        }
    ],
    "data_busca": "2024-01-20T10:30:00",
    "url_fonte": "https://www.vivareal.com.br/venda/parana/araucaria/"
}
```

## 💾 Banco de Dados

### SQLite (Padrão)

```python
from salvar_banco import BancoImoveis

# Criar instância
banco = BancoImoveis("imoveis.db")

# Salvar dados da API
dados_api = response.json()
total_salvos = banco.salvar_imoveis(dados_api)

# Buscar imóveis
imoveis = banco.buscar_imoveis(
    cidade="Araucaria",
    estado="PR",
    tipo="venda"
)

# Estatísticas
stats = banco.estatisticas()
print(f"Total: {stats['total_imoveis']}")
```

### Outros Bancos

Edite `config_banco.py` para configurar:
- PostgreSQL
- MySQL
- MongoDB
- Redis

## 🤖 Automação

### Busca Periódica

```bash
python automacao_busca.py
```

**Configurações** (em `automacao_busca.py`):
- Cidades: Araucária, Curitiba, Pinhais
- Tipos: Venda e Aluguel
- Horários: 8h, 12h, 18h, 22h
- Relatório diário às 23h

### Busca Manual

```python
from salvar_banco import buscar_e_salvar

# Buscar e salvar automaticamente
resultado = buscar_e_salvar(
    cidade="Araucaria",
    estado="PR",
    tipo_operacao="venda",
    max_paginas=2
)
```

## 📁 Estrutura de Arquivos

```
web-ui/
├── api_imoveis.py          # API FastAPI principal
├── salvar_banco.py         # Classe para banco de dados
├── config_banco.py         # Configurações de banco
├── automacao_busca.py      # Script de automação
├── imoveis.db              # Banco SQLite (criado automaticamente)
├── historico_buscas.json   # Log das buscas
└── relatorio_imoveis.json  # Relatório de estatísticas
```

## 🔧 Configurações

### Variáveis de Ambiente

```bash
# .env
OPENAI_API_KEY=sua_chave_aqui
DB_TYPE=sqlite  # ou postgresql, mysql, mongodb
DB_HOST=localhost
DB_PORT=5432
DB_NAME=imoveis
DB_USER=usuario
DB_PASSWORD=senha
```

### Personalizar Buscas

Edite `automacao_busca.py`:

```python
CIDADES_BUSCA = [
    {"cidade": "SuaCidade", "estado": "SE", "tipo": "venda"},
    {"cidade": "SuaCidade", "estado": "SE", "tipo": "aluguel"},
]

HORARIOS_BUSCA = [
    "09:00",  # Personalizar horários
    "15:00",
    "21:00"
]
```

## 📈 Monitoramento

### Logs

- `automacao_imoveis.log`: Log detalhado das execuções
- `historico_buscas.json`: Histórico de todas as buscas
- `relatorio_imoveis.json`: Estatísticas atualizadas

### Status da API

```bash
curl http://127.0.0.1:8000/status
```

## 🚨 Troubleshooting

### API não responde
1. Verificar se WebUI está rodando na porta 7788
2. Verificar chave OpenAI no .env
3. Verificar logs da API

### Erro de banco de dados
1. Verificar permissões de escrita no diretório
2. Verificar se SQLite está funcionando
3. Verificar configurações em config_banco.py

### Busca falha
1. Verificar conectividade com internet
2. Verificar se VivaReal está acessível
3. Ajustar max_paginas se necessário

## 📞 Suporte

Para problemas ou dúvidas:
1. Verificar logs em `automacao_imoveis.log`
2. Verificar status da API: `/status`
3. Verificar documentação: `/docs`

## 🔄 Próximos Passos

- [ ] Integração com outros sites (Zap, OLX)
- [ ] Dashboard web para visualização
- [ ] Alertas por email/WhatsApp
- [ ] Análise de preços e tendências
- [ ] API para consultas avançadas
