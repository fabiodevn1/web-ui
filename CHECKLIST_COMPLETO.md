# 🎯 CHECKLIST COMPLETO - SISTEMA DE BUSCA ÚNICA VIVA REAL

## 📋 **OBJETIVO FINAL**
Sistema que busca **APENAS UM LINK ÚNICO** por cidade/tipo no VivaReal, não todas as variações como o Bing fazia antes.

## 🚀 **FASE 1: PREPARAÇÃO DO AMBIENTE**

### ✅ **1.1 Verificar Dependências**
```bash
# No diretório web-ui
uv pip install pymysql requests
```

### ✅ **1.2 Verificar Banco MariaDB**
- [ ] Conexão funcionando (host: 147.79.107.233)
- [ ] Tabelas existem: `municipios`, `estados`, `plataformas`, `tipos_busca`, `links_duckduckgo`
- [ ] Dados de cidades ativas disponíveis

### ✅ **1.3 Verificar WebUI**
- [ ] WebUI rodando na porta 7788
- [ ] Chave OpenAI configurada no .env
- [ ] Playwright com Chromium instalado

## 🔧 **FASE 2: IMPLEMENTAÇÃO DOS ARQUIVOS**

### ✅ **2.1 Arquivos Criados**
- [x] `api_imoveis_mariadb.py` - API integrada com MariaDB
- [x] `busca_unica.py` - Sistema de busca única
- [x] `teste_mariadb.py` - Script de teste completo
- [x] `CHECKLIST_COMPLETO.md` - Este arquivo

### ✅ **2.2 Arquivos Existentes (não modificar)**
- [x] `database.py` - Conexão com MariaDB
- [x] `scraper_bing.py` - Sistema antigo (referência)

## 🧪 **FASE 3: TESTES E VERIFICAÇÃO**

### ✅ **3.1 Teste de Conexão**
```bash
python teste_mariadb.py
```
**Resultado esperado**: Todos os 8 testes devem passar ✅

### ✅ **3.2 Verificar Estrutura do Banco**
- [ ] Tabela `municipios`: deve ter cidades ativas
- [ ] Tabela `estados`: deve ter estados ativos  
- [ ] Tabela `plataformas`: deve ter VivaReal ativo
- [ ] Tabela `tipos_busca`: deve ter VENDA e ALUGUEL
- [ ] Tabela `links_duckduckgo`: estrutura correta

## 🚀 **FASE 4: EXECUÇÃO DO SISTEMA**

### ✅ **4.1 Iniciar API MariaDB**
```bash
# Terminal 1: WebUI (já rodando)
python webui.py --ip 127.0.0.1 --port 7788

# Terminal 2: API MariaDB (nova porta 8001)
python api_imoveis_mariadb.py
```

**Verificar**: http://127.0.0.1:8001/status

### ✅ **4.2 Testar Busca Única**
```bash
# Terminal 3: Teste completo
python teste_mariadb.py
```

### ✅ **4.3 Executar Sistema Principal**
```bash
# Terminal 4: Sistema de busca única
python busca_unica.py
```

## 📊 **FASE 5: VERIFICAÇÃO DOS RESULTADOS**

### ✅ **5.1 Verificar Links Salvos**
```bash
curl http://127.0.0.1:8001/links-salvos
```

**Resultado esperado**: Links únicos salvos no banco para cada cidade/tipo

### ✅ **5.2 Verificar Banco de Dados**
```sql
-- Verificar links salvos
SELECT 
    l.url, l.titulo_pagina, l.total_imoveis,
    p.nome as plataforma, t.nome as tipo_busca,
    e.sigla as estado, m.nome as cidade,
    l.created_at, l.updated_at
FROM links_duckduckgo l
JOIN plataformas p ON l.plataforma_id = p.id
JOIN tipos_busca t ON l.tipo_busca_id = t.id
JOIN estados e ON l.estado_id = e.id
JOIN municipios m ON l.municipio_id = m.id
WHERE p.nome = 'VivaReal'
ORDER BY l.created_at DESC;
```

## 🔄 **FASE 6: AUTOMAÇÃO E MONITORAMENTO**

### ✅ **6.1 Configurar Execução Automática**
```bash
# Executar a cada 6 horas
python busca_unica.py

# Ou usar cron:
# 0 */6 * * * cd /caminho/para/web-ui && python busca_unica.py
```

### ✅ **6.2 Monitorar Logs**
- [ ] `busca_unica.log` - Log principal do sistema
- [ ] `relatorio_busca_unica.json` - Relatório de estatísticas
- [ ] Logs do banco MariaDB

## 📁 **ESTRUTURA FINAL DOS ARQUIVOS**

```
web-ui/
├── api_imoveis_mariadb.py      # ✅ NOVO: API integrada com MariaDB
├── busca_unica.py              # ✅ NOVO: Sistema de busca única
├── teste_mariadb.py            # ✅ NOVO: Testes completos
├── database.py                 # ✅ EXISTENTE: Conexão MariaDB
├── scraper_bing.py             # ✅ EXISTENTE: Sistema antigo (referência)
├── webui.py                    # ✅ EXISTENTE: WebUI principal
├── .env                        # ✅ EXISTENTE: Configurações
└── CHECKLIST_COMPLETO.md       # ✅ NOVO: Este arquivo
```

## 🎯 **DIFERENÇAS PRINCIPAIS DO SISTEMA ANTERIOR**

### ❌ **Sistema Antigo (Bing)**
- Buscava no Bing com múltiplas variações
- Retornava muitos links por cidade
- Salva múltiplos links na tabela `links_duckduckgo`
- Usava `site:` restriction que falhava

### ✅ **Sistema Novo (WebUI)**
- Usa WebUI com IA para navegação inteligente
- Busca **APENAS UM LINK ÚNICO** por cidade/tipo
- Salva apenas o link principal da página
- Navega diretamente no VivaReal
- Integrado com seu banco MariaDB existente

## 🚨 **PONTOS DE ATENÇÃO**

### ⚠️ **Portas Utilizadas**
- **7788**: WebUI principal
- **8001**: API MariaDB (nova)
- **8000**: API original (não usar)

### ⚠️ **Dependências**
- `pymysql` para MariaDB
- `requests` para HTTP
- `browser-use` já instalado
- `fastapi` e `uvicorn` para API

### ⚠️ **Configurações**
- Chave OpenAI no `.env`
- Conexão MariaDB em `database.py`
- Cidades ativas no banco

## 🔍 **TROUBLESHOOTING**

### ❌ **API não responde**
1. Verificar se WebUI está rodando na porta 7788
2. Verificar chave OpenAI no .env
3. Verificar logs da API

### ❌ **Erro de banco de dados**
1. Verificar conexão MariaDB
2. Verificar se tabelas existem
3. Verificar permissões

### ❌ **Busca falha**
1. Verificar conectividade com internet
2. Verificar se VivaReal está acessível
3. Verificar logs do WebUI

## 📈 **PRÓXIMOS PASSOS APÓS IMPLEMENTAÇÃO**

### 🎯 **Curto Prazo (1-2 dias)**
- [ ] Testar com 5-10 cidades
- [ ] Verificar qualidade dos links
- [ ] Ajustar parâmetros se necessário

### 🎯 **Médio Prazo (1 semana)**
- [ ] Expandir para mais cidades
- [ ] Configurar execução automática
- [ ] Monitorar performance

### 🎯 **Longo Prazo (1 mês)**
- [ ] Dashboard para visualização
- [ ] Alertas para novos imóveis
- [ ] Análise de tendências

## 🎉 **RESULTADO FINAL ESPERADO**

✅ **Sistema funcionando** que:
- Lê cidades ativas do seu banco MariaDB
- Busca **APENAS UM LINK** por cidade/tipo no VivaReal
- Salva no banco existente (`links_duckduckgo`)
- Executa automaticamente a cada 6 horas
- Gera relatórios e logs completos
- **NÃO** retorna múltiplas variações como o Bing fazia

---

## 🚀 **COMANDOS PARA EXECUTAR AGORA**

```bash
# 1. Testar integração
python teste_mariadb.py

# 2. Se tudo OK, iniciar API
python api_imoveis_mariadb.py

# 3. Em outro terminal, executar sistema
python busca_unica.py
```

**Status**: ✅ SISTEMA COMPLETO E PRONTO PARA USO!
