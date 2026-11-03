#!/usr/bin/env bash
set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
    echo "Instale Python 3.11+ antes de gerar o aplicativo." >&2
    exit 1
fi
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'; then
    echo "O build requer Python 3.11 ou superior." >&2
    exit 1
fi

python3 -m venv .venv-build
python=".venv-build/bin/python"
"$python" -m pip install --upgrade pip
"$python" -m pip install -r requirements.txt pyinstaller
"$python" -m PyInstaller --noconfirm --clean JadeDashboard.spec
tar -czf dist/JadeDashboard-linux-x86_64.tar.gz -C dist JadeDashboard

printf '\nExecutável: %s\nPacote: %s\n' \
    "$PWD/dist/JadeDashboard/JadeDashboard" \
    "$PWD/dist/JadeDashboard-linux-x86_64.tar.gz"
