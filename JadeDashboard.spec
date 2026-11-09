# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_all

root = Path(SPECPATH)
streamlit_datas, streamlit_binaries, streamlit_hiddenimports = collect_all(
    "streamlit"
)
psycopg_datas, psycopg_binaries, psycopg_hiddenimports = collect_all("psycopg")
binary_datas, binary_binaries, binary_hiddenimports = collect_all("psycopg_binary")
uvicorn_datas, uvicorn_binaries, uvicorn_hiddenimports = collect_all("uvicorn")

a = Analysis(
    ["app_launcher.py"],
    pathex=[str(root), str(root / "frontend")],
    binaries=(
        streamlit_binaries
        + psycopg_binaries
        + binary_binaries
        + uvicorn_binaries
    ),
    datas=streamlit_datas
    + psycopg_datas
    + binary_datas
    + uvicorn_datas
    + [
        (str(root / ".streamlit"), ".streamlit"),
        (str(root / "backend"), "backend"),
        (str(root / "frontend"), "frontend"),
        (str(root / "shared"), "shared"),
        (str(root / "jadeLogos"), "jadeLogos"),
    ],
    hiddenimports=streamlit_hiddenimports
    + psycopg_hiddenimports
    + binary_hiddenimports
    + uvicorn_hiddenimports
    + [
        "backend.main",
        "psycopg",
        "serial",
        "sqlalchemy.dialects.postgresql.psycopg",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="JadeDashboard",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name="JadeDashboard",
)
