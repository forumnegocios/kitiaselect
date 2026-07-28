@echo off
title Kit Select IA — Dashboard
color 1F

echo.
echo  ============================================================
echo   Kit Select IA — Dashboard
echo   Forum Negocios Select
echo  ============================================================
echo.

:: Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  ATENCAO: Python nao encontrado.
    echo.
    echo  Para usar o dashboard, instale o Python em:
    echo  https://www.python.org/downloads/
    echo.
    echo  Marque a opcao "Add Python to PATH" durante a instalacao.
    echo.
    pause
    exit /b 1
)

:: Instalar dependências se necessário
echo  Verificando dependencias...
pip show flask >nul 2>&1
if %errorlevel% neq 0 (
    echo  Instalando Flask (primeira vez, aguarde)...
    pip install flask flask-cors --quiet
)

:: reportlab: usado para o download em PDF dos resultados
pip show reportlab >nul 2>&1
if %errorlevel% neq 0 (
    echo  Instalando gerador de PDF (aguarde)...
    pip install reportlab --quiet
)

echo  Iniciando servidor...
echo  O dashboard abrira no seu navegador em instantes.
echo.
echo  Para encerrar: feche esta janela.
echo  ============================================================
echo.

python dashboard-server.py
pause
