#!/bin/bash
# Kit Select IA — Dashboard (macOS)
# Fórum Negócios Select

cd "$(dirname "$0")"

echo ""
echo "============================================================"
echo "  Kit Select IA — Dashboard"
echo "  Fórum Negócios Select"
echo "============================================================"
echo ""

# Verificar Python
if ! command -v python3 &>/dev/null; then
    echo "  ATENÇÃO: Python não encontrado."
    echo ""
    echo "  Instale em: https://www.python.org/downloads/"
    echo "  Ou via Homebrew: brew install python3"
    echo ""
    read -p "  Pressione Enter para sair..."
    exit 1
fi

# Instalar dependências se necessário
echo "  Verificando dependências..."
python3 -c "import flask" 2>/dev/null || {
    echo "  Instalando Flask (primeira vez, aguarde)..."
    pip3 install flask flask-cors --quiet
}

echo "  Iniciando servidor..."
echo "  O dashboard abrirá no seu navegador em instantes."
echo ""
echo "  Para encerrar: feche esta janela."
echo "============================================================"
echo ""

python3 dashboard-server.py
