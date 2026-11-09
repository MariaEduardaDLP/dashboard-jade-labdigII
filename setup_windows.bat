@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
    echo Python 3.11 ou superior nao foi encontrado.
    echo Instale Python pelo site python.org e marque "Add Python to PATH".
    pause
    exit /b 1
)
py -3 -c "import sys; raise SystemExit(sys.version_info < (3, 11))"
if errorlevel 1 (
    echo O projeto requer Python 3.11 ou superior.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    py -3 -m venv .venv
    if errorlevel 1 (
        echo Falha ao criar o ambiente Python.
        pause
        exit /b 1
    )
)

".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
    echo Falha ao preparar o pip.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo Falha ao instalar as dependencias.
    pause
    exit /b 1
)

if not exist ".env" copy ".env.example" ".env" >nul
echo.
echo Preparacao concluida. Edite o arquivo .env e configure JADE_DATABASE_URL.
echo Depois, execute run_backend.bat para iniciar o coletor da placa.
pause
