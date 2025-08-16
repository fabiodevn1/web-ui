# 🚀 Sistema de Automação Completa - Busca de Links de Imóveis

## 📋 Descrição

Sistema automatizado que busca links de imóveis em todas as plataformas ativas, para todas as cidades e tipos de busca configurados no banco de dados MariaDB.

## ✨ Características

- ✅ Busca real na internet usando browser_use (WebUI)
- ✅ Processa todas as combinações de: Cidades × Plataformas × Tipos (venda/aluguel)
- ✅ Executa em loop contínuo com intervalo de 12 horas
- ✅ Pula links já atualizados nas últimas 24 horas
- ✅ Salva estatísticas de cada ciclo
- ✅ Gera relatórios automáticos
- ✅ Tratamento de erros e retry automático

## 🔧 Pré-requisitos

1. **Python 3.8+** instalado
2. **OpenAI API Key** configurada no arquivo `.env`
3. **Banco MariaDB** configurado e acessível
4. **Dependências Python** instaladas:
   ```bash
   pip install -r requirements.txt
   ```

## 📦 Arquivos Principais

- `automacao_completa.py` - Script principal da automação
- `start_automacao.sh` - Script facilitador para iniciar
- `automacao-imoveis.service` - Arquivo de serviço systemd
- `.env` - Configurações de ambiente (criar se não existir)

## 🚀 Como Executar

### Método 1: Usando o Script Facilitador (RECOMENDADO)

```bash
# Dar permissão de execução
chmod +x start_automacao.sh

# Executar
./start_automacao.sh
```

O script oferece 4 opções:
1. **Foreground** - Ver logs em tempo real
2. **Background com nohup** - Executa em background simples
3. **Background com screen** - Executa em sessão screen (recomendado)
4. **Teste** - Executa apenas um ciclo para teste

### Método 2: Execução Direta

```bash
# Executar em foreground (ver logs)
python3 automacao_completa.py

# Executar em background com nohup
nohup python3 automacao_completa.py > automacao.log 2>&1 &

# Executar em screen (recomendado)
screen -dmS automacao python3 automacao_completa.py
```

### Método 3: Como Serviço do Sistema (Linux)

```bash
# Copiar arquivo de serviço
sudo cp automacao-imoveis.service /etc/systemd/system/

# Criar diretório de logs
sudo mkdir -p /var/log/automacao-imoveis
sudo chown $USER:$USER /var/log/automacao-imoveis

# Recarregar daemon
sudo systemctl daemon-reload

# Iniciar serviço
sudo systemctl start automacao-imoveis

# Habilitar início automático
sudo systemctl enable automacao-imoveis

# Ver status
sudo systemctl status automacao-imoveis

# Ver logs
sudo journalctl -u automacao-imoveis -f
```

## 📊 Monitoramento

### Ver Logs em Tempo Real

```bash
# Se usando arquivo de log
tail -f automacao_completa.log

# Se usando screen
screen -r automacao_imoveis

# Se usando systemd
sudo journalctl -u automacao-imoveis -f
```

### Ver Estatísticas

```bash
# Estatísticas dos ciclos
cat estatisticas_automacao.json | python -m json.tool

# Última execução
tail -n 100 automacao_completa.log
```

## ⚙️ Configurações

### Arquivo `.env`

```env
# API Key do OpenAI (obrigatório)
OPENAI_API_KEY=sk-...

# Outras configurações (opcional)
HEADLESS_BROWSER=false  # true para não mostrar navegador
LOG_LEVEL=INFO          # DEBUG, INFO, WARNING, ERROR
```

### Configurações no Script

Edite `automacao_completa.py` para ajustar:

```python
self.intervalo_horas = 12      # Intervalo entre ciclos (horas)
self.delay_entre_buscas = 30   # Delay entre cada busca (segundos)
```

## 🛑 Como Parar

### Se executando em foreground
```bash
# Pressione Ctrl+C
```

### Se executando com nohup
```bash
# Encontrar o PID
ps aux | grep automacao_completa.py

# Matar o processo
kill <PID>
```

### Se executando com screen
```bash
# Listar sessões
screen -ls

# Parar a sessão
screen -X -S automacao_imoveis quit
```

### Se executando como serviço
```bash
# Parar
sudo systemctl stop automacao-imoveis

# Desabilitar início automático
sudo systemctl disable automacao-imoveis
```

## 📈 Fluxo de Execução

1. **Busca Configurações**: Lê cidades, plataformas e tipos ativos do banco
2. **Gera Combinações**: Cria todas as combinações possíveis
3. **Para cada combinação**:
   - Verifica se já existe link recente (24h)
   - Se não, faz busca real na internet
   - Navega até o site da plataforma
   - Captura o link oficial
   - Salva no banco de dados
   - Aguarda 30 segundos
4. **Gera Relatório**: Salva estatísticas do ciclo
5. **Aguarda 12 horas** e repete

## 📝 Logs e Relatórios

### Arquivos Gerados

- `automacao_completa.log` - Log detalhado de execução
- `estatisticas_automacao.json` - Estatísticas de cada ciclo
- `logs/` - Diretório com logs históricos

### Exemplo de Estatísticas

```json
{
  "ciclo": 1,
  "inicio": "2024-01-15T10:00:00",
  "fim": "2024-01-15T14:30:00",
  "duracao": "4:30:00",
  "total_processados": 150,
  "total_sucesso": 145,
  "total_pulados": 50,
  "total_erros": 5
}
```

## 🔍 Verificar Funcionamento

```bash
# Ver quantos links foram salvos hoje
mysql -h 147.79.107.233 -u mariadb -p avalion_painel -e "
SELECT COUNT(*) as total_hoje 
FROM links_duckduckgo 
WHERE DATE(created_at) = CURDATE() 
   OR DATE(updated_at) = CURDATE();"

# Ver últimos links salvos
mysql -h 147.79.107.233 -u mariadb -p avalion_painel -e "
SELECT url, created_at 
FROM links_duckduckgo 
ORDER BY created_at DESC 
LIMIT 10;"
```

## ⚠️ Avisos Importantes

1. **Consumo de API**: Cada busca consome tokens da API do OpenAI
2. **Tempo de Execução**: Um ciclo completo pode levar várias horas
3. **Navegador**: O browser_use abrirá navegadores reais durante a execução
4. **Recursos**: Certifique-se de ter RAM suficiente (mínimo 4GB recomendado)

## 🐛 Solução de Problemas

### Erro: "OPENAI_API_KEY não configurada"
- Edite o arquivo `.env` e adicione sua chave da OpenAI

### Erro: "Address already in use"
- Mate processos antigos: `pkill -f automacao_completa.py`

### Erro: "Connection refused" no banco
- Verifique as credenciais do banco em `database.py`
- Teste a conexão: `mysql -h 147.79.107.233 -u mariadb -p`

### Browser não abre
- Instale dependências: `playwright install chromium`

## 📞 Suporte

Em caso de problemas, verifique:
1. Os logs em `automacao_completa.log`
2. As estatísticas em `estatisticas_automacao.json`
3. A conectividade com o banco de dados
4. Se a API Key do OpenAI está válida

---

**Desenvolvido para busca automatizada de links de imóveis** 🏠