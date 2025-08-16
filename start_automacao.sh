#!/bin/bash
#
# Script para iniciar a automação completa de busca de imóveis
#

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}🚀 SISTEMA DE AUTOMAÇÃO DE BUSCA${NC}"
echo -e "${GREEN}========================================${NC}"

# Verificar se Python está instalado
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 não está instalado${NC}"
    exit 1
fi

# Verificar arquivo .env
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️ Arquivo .env não encontrado${NC}"
    echo "Criando arquivo .env de exemplo..."
    cat > .env << 'EOL'
# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here

# Outras configurações (opcional)
HEADLESS_BROWSER=false
LOG_LEVEL=INFO
EOL
    echo -e "${YELLOW}Por favor, configure o arquivo .env com sua OPENAI_API_KEY${NC}"
    exit 1
fi

# Verificar se a API key está configurada
if ! grep -q "OPENAI_API_KEY=sk-" .env; then
    echo -e "${RED}❌ OPENAI_API_KEY não está configurada no arquivo .env${NC}"
    exit 1
fi

# Criar diretório de logs se não existir
mkdir -p logs

# Verificar se há processos rodando
PIDS=$(pgrep -f "automacao_completa.py" | tr '\n' ' ')
if [ ! -z "$PIDS" ]; then
    echo -e "${YELLOW}⚠️ Processos de automação já em execução (PIDs: $PIDS)${NC}"
    echo "Deseja parar os processos anteriores? (s/n)"
    read -p "Resposta: " resp
    if [ "$resp" = "s" ] || [ "$resp" = "S" ]; then
        pkill -f "automacao_completa.py"
        echo -e "${GREEN}✅ Processos anteriores encerrados${NC}"
        sleep 2
    fi
fi

# Opções de execução
echo ""
echo "Escolha o modo de execução:"
echo "1) Executar em foreground (ver logs em tempo real)"
echo "2) Executar em background com nohup"
echo "3) Executar em background com screen (recomendado)"
echo "4) Apenas testar um ciclo"
echo "5) Parar todos os processos"
echo ""
read -p "Opção [1-5]: " opcao

case $opcao in
    1)
        echo -e "${GREEN}▶️ Executando em foreground (modo headless)...${NC}"
        echo -e "${YELLOW}Pressione Ctrl+C para parar${NC}"
        echo ""
        export HEADLESS_MODE=true
        source .venv/bin/activate && python3 automacao_completa.py
        ;;
    
    2)
        echo -e "${GREEN}▶️ Executando em background com nohup...${NC}"
        source .venv/bin/activate && nohup python3 automacao_completa.py > logs/automacao_$(date +%Y%m%d_%H%M%S).log 2>&1 &
        PID=$!
        echo -e "${GREEN}✅ Processo iniciado com PID: $PID${NC}"
        echo "Para parar: kill $PID"
        echo "Para ver logs: tail -f logs/automacao_*.log"
        ;;
    
    3)
        # Verificar se screen está instalado
        if ! command -v screen &> /dev/null; then
            echo -e "${YELLOW}Screen não está instalado. Instalando...${NC}"
            sudo apt-get update && sudo apt-get install -y screen
        fi
        
        echo -e "${GREEN}▶️ Executando em background com screen...${NC}"
        screen -dmS automacao_imoveis bash -c 'source .venv/bin/activate && python3 automacao_completa.py'
        echo -e "${GREEN}✅ Sessão screen 'automacao_imoveis' criada${NC}"
        echo ""
        echo "Comandos úteis:"
        echo "  Ver logs:     screen -r automacao_imoveis"
        echo "  Sair da tela: Ctrl+A, depois D"
        echo "  Listar telas: screen -ls"
        echo "  Parar:        screen -X -S automacao_imoveis quit"
        ;;
    
    4)
        echo -e "${GREEN}▶️ Executando teste de um ciclo...${NC}"
        source .venv/bin/activate && python3 -c "
import asyncio
from automacao_completa import AutomacaoBuscaCompleta

async def teste():
    automacao = AutomacaoBuscaCompleta()
    automacao.intervalo_horas = 0  # Não repetir
    await automacao.executar_ciclo_completo()
    automacao.gerar_relatorio_final()

asyncio.run(teste())
"
        ;;
    
    5)
        echo -e "${YELLOW}⏹️ Parando todos os processos...${NC}"
        pkill -f "automacao_completa.py"
        screen -X -S automacao_imoveis quit 2>/dev/null
        echo -e "${GREEN}✅ Todos os processos foram parados${NC}"
        ;;
    
    *)
        echo -e "${RED}Opção inválida${NC}"
        exit 1
        ;;
esac