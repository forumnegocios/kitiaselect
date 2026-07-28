@echo off
title Kit Select IA — Dashboard
color 1F

echo.
echo  ============================================================
echo   Kit Select IA — Dashboard
echo   Forum Negocios Select
echo  ============================================================
echo.

set LOGFILE=%~dp0dados\dashboard-log.txt
if not exist "%~dp0dados" mkdir "%~dp0dados"
echo ==== Execucao iniciada %date% %time% ==== > "%LOGFILE%"

:: Verificar Python
python --version >> "%LOGFILE%" 2>&1
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
python -m pip show flask >> "%LOGFILE%" 2>&1
if %errorlevel% neq 0 (
    echo  Instalando Flask e Flask-CORS ^(primeira vez, aguarde^)...
    python -m pip install flask flask-cors >> "%LOGFILE%" 2>&1
    if %errorlevel% neq 0 (
        echo.
        echo  ERRO ao instalar as dependencias. Veja o log em:
        echo  %LOGFILE%
        echo.
        pause
        exit /b 1
    )
)

echo  Dependencias OK.
echo  Iniciando servidor...
echo  O dashboard abrira no seu navegador em instantes.
echo.
echo  Para encerrar: feche esta janela.
echo  ============================================================
echo.

python dashboard-server.py
echo.
echo  O servidor foi encerrado (codigo %errorlevel%).
echo  Se isso foi inesperado, veja o log em: %LOGFILE%
pause
