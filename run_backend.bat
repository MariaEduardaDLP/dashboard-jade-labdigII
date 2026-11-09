@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Ambiente Python ausente. Execute setup_windows.bat primeiro.
    pause
    exit /b 1
)
if not exist ".env" (
    echo Arquivo .env ausente. Execute setup_windows.bat e configure JADE_DATABASE_URL.
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m backend.serial_worker
if errorlevel 1 (
    echo.
    echo O coletor foi encerrado com erro. Leia a mensagem acima.
    pause
)
