$ErrorActionPreference = "Stop"

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Instale Python 3.11+ para Windows antes de gerar o aplicativo."
}

py -3.11 -m venv .venv-build
if ($LASTEXITCODE -ne 0) { throw "Falha ao criar o ambiente virtual." }
$python = Join-Path $PWD ".venv-build\Scripts\python.exe"
& $python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Falha ao atualizar o pip." }
& $python -m pip install -r requirements.txt pyinstaller
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar as dependências." }
& $python -m PyInstaller --noconfirm --clean JadeDashboard.spec
if ($LASTEXITCODE -ne 0) { throw "Falha ao empacotar o aplicativo." }

Write-Host ""
Write-Host "Aplicativo gerado em: $PWD\dist\JadeDashboard\JadeDashboard.exe"
