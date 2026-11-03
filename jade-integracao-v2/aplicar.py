#!/usr/bin/env python3
"""Aplicador conservador da integração UART Jade.

Independente de hash de Git: identifica elementos por AST e modifica apenas
blocos reconhecidos. Padrao: somente mostra as mudancas (dry-run).
"""

from __future__ import annotations

import argparse
import ast
import difflib
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = Path(__file__).resolve().parent


class IncompatibleCode(RuntimeError):
    pass


def get_segment(src: str, node: ast.AST) -> str:
    result = ast.get_source_segment(src, node)
    if result is None:
        raise IncompatibleCode("Não consegui localizar um bloco de código com segurança.")
    return result


def replace_single(src: str, old: str, new: str, description: str) -> str:
    occurrences = src.count(old)
    if occurrences != 1:
        raise IncompatibleCode(f"{description}: ocorrência esperada uma vez, encontrada {occurrences}.")
    return src.replace(old, new, 1)


def patch_serial(src: str) -> str:
    tree = ast.parse(src)
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "SerialListener"]
    if len(classes) != 1:
        raise IncompatibleCode("serial_listener.py: classe SerialListener não identificada unicamente.")
    methods = [n for n in classes[0].body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "_read_frames"]
    if len(methods) != 1:
        raise IncompatibleCode("serial_listener.py: método _read_frames não identificado unicamente.")
    calls = [n for n in ast.walk(methods[0]) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "Serial" and isinstance(n.func.value, ast.Name) and n.func.value.id == "serial"]
    if len(calls) != 1:
        raise IncompatibleCode(f"serial_listener.py: esperava exatamente uma abertura serial.Serial(), encontrei {len(calls)}.")
    call = calls[0]
    desired = {"bytesize": "serial.SEVENBITS", "parity": "serial.PARITY_EVEN", "stopbits": "serial.STOPBITS_ONE"}
    existing = {k.arg: ast.unparse(k.value) for k in call.keywords}
    for key, expected in desired.items():
        if key in existing and existing[key] != expected:
            raise IncompatibleCode(f"serial_listener.py: '{key}={existing[key]}' é diferente do esperado. Revisão manual necessária.")
    missing = {k: v for k, v in desired.items() if k not in existing}
    if not missing:
        return src
    segment = get_segment(src, call)
    import re
    match = re.search(r"(?m)^(?P<indent>[ \t]*)timeout\s*=", segment)
    if not match:
        raise IncompatibleCode("serial_listener.py: não encontrei timeout= na chamada serial.Serial; revisar manualmente.")
    indent = match.group("indent")
    insertion = "".join(f"{indent}{k}={v},\n" for k, v in missing.items())
    new_segment = segment[:match.start()] + insertion + segment[match.start():]
    return replace_single(src, segment, new_segment, "serial_listener.py: chamada Serial")


def patch_events(src: str) -> str:
    tree = ast.parse(src)
    cls = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Event"]
    if len(cls) != 1:
        raise IncompatibleCode("events.py: classe Event não identificada.")
    fields = {n.target.id: n for n in cls[0].body if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)}
    for name in ("requested_at", "attended_at"):
        node = fields.get(name)
        if node is None or not isinstance(node.value, ast.Call):
            raise IncompatibleCode(f"events.py: campo {name} não identificado como mapped_column(...).")
        val = node.value
        if not isinstance(val.func, ast.Name) or val.func.id != "mapped_column":
            raise IncompatibleCode(f"events.py: campo {name} não utiliza mapped_column(...).")
        found = any(isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id in {"DateTime", "TIMESTAMP"} for arg in val.args)
        if found:
            args = [arg for arg in val.args if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id in {"DateTime", "TIMESTAMP"}]
            if len(args) != 1 or not any(kw.arg == "timezone" and isinstance(kw.value, ast.Constant) and kw.value.value is True for kw in args[0].keywords):
                raise IncompatibleCode(f"events.py: {name} já declara tipo temporal diferente. Revisar manualmente.")
            continue
        # Existing custom SQL type? Do not modify without review.
        if val.args:
            raise IncompatibleCode(f"events.py: {name} já declara argumentos posicionais em mapped_column. Revisar manualmente.")
    # Modify from bottom up by reparsing each time to preserve AST offsets.
    for name in ("attended_at", "requested_at"):
        tree = ast.parse(src)
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Event")
        node = next(n for n in cls.body if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and n.target.id == name)
        val = node.value
        if val.args:
            continue
        segment = get_segment(src, val)
        if not segment.startswith("mapped_column("):
            raise IncompatibleCode(f"events.py: formato inesperado de mapped_column para {name}.")
        new_segment = segment.replace("mapped_column(", "mapped_column(DateTime(timezone=True), ", 1)
        src = replace_single(src, segment, new_segment, f"events.py: {name}")
    # Ensure import; a separate import keeps existing import style intact.
    tree = ast.parse(src)
    imported_datetime = any(isinstance(n, ast.ImportFrom) and n.module in ("sqlalchemy", "sqlalchemy.types", "sqlalchemy.sql.sqltypes") and any(x.name == "DateTime" for x in n.names) for n in tree.body)
    if not imported_datetime:
        import_node = next((n for n in tree.body if isinstance(n, ast.ImportFrom) and n.module == "sqlalchemy"), None)
        if import_node is None:
            raise IncompatibleCode("events.py: importação SQLAlchemy não identificada.")
        lines = src.splitlines(keepends=True)
        lines.insert(import_node.lineno - 1, "from sqlalchemy import DateTime\n")
        src = "".join(lines)
    # Normalize old UTC-naive values when comparing attended and requested timestamps.
    tree = ast.parse(src)
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "process_serial_message"]
    if len(funcs) != 1:
        raise IncompatibleCode("events.py: process_serial_message não identificado.")
    function = funcs[0]
    comparisons = [n for n in ast.walk(function) if isinstance(n, ast.Compare) and len(n.ops) == 1 and isinstance(n.ops[0], ast.Lt) and ast.unparse(n.left) == "event_time" and len(n.comparators) == 1 and ast.unparse(n.comparators[0]) == "event.requested_at"]
    if len(comparisons) == 1:
        cmpnode = comparisons[0]
        lines = src.splitlines(keepends=True)
        line_index = cmpnode.lineno - 1
        line = lines[line_index]
        import re
        match = re.match(r"^(\s*)if\s+event_time\s*<\s*event\.requested_at\s*:\s*$", line.rstrip("\r\n"))
        if not match:
            raise IncompatibleCode("events.py: comparação de horários possui forma inesperada; revisar manualmente.")
        indent = match.group(1)
        new = (f"{indent}requested_at = event.requested_at\n"
               f"{indent}if requested_at.tzinfo is None:\n"
               f"{indent}    requested_at = requested_at.replace(tzinfo=timezone.utc)\n"
               f"{indent}if event_time < requested_at:\n")
        lines[line_index] = new
        src = "".join(lines)
    elif not comparisons:
        # May already be normalized. Check rather than overwrite differing logic.
        body = get_segment(src, function)
        if not ("event_time < requested_at" in body and "requested_at.tzinfo is None" in body):
            raise IncompatibleCode("events.py: regra de comparação de horários mudou; preservada para revisão manual.")
    else:
        raise IncompatibleCode("events.py: múltiplas comparações de horário encontradas.")
    return src


def patch_env(src: str) -> str:
    if "JADE_SERIAL_BAUDRATE=115200" in src:
        return src
    old = "# JADE_SERIAL_BAUDRATE=<baud rate configurado no dispositivo>"
    if old in src:
        return src.replace(old, "# JADE_SERIAL_BAUDRATE=115200  # Jade DE0-CV: 115200, 7E1", 1)
    # Unknown env layout: leave unchanged rather than overriding current setting.
    return src


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--apply", action="store_true", help="Aplicar alterações; padrão: apenas mostrar o diff")
    args = p.parse_args()
    if not all((ROOT / file).exists() for file in ("backend/events.py", "backend/serial_listener.py", ".env.example")):
        print(f"ERRO: coloque a pasta {PACKAGE.name} dentro da raiz do repositório (onde está backend/).", file=sys.stderr)
        return 1
    original = {name: (ROOT / name).read_text(encoding="utf-8") for name in ("backend/events.py", "backend/serial_listener.py", ".env.example")}
    try:
        updated = {
            "backend/events.py": patch_events(original["backend/events.py"]),
            "backend/serial_listener.py": patch_serial(original["backend/serial_listener.py"]),
            ".env.example": patch_env(original[".env.example"]),
        }
        for name in ("backend/events.py", "backend/serial_listener.py"):
            ast.parse(updated[name], filename=name)
        files_new = {}
        for rel in ("scripts/jade_uart_probe.py", "tests/test_uart_jade.py"):
            data = (PACKAGE / rel).read_text(encoding="utf-8")
            destination = ROOT / rel
            if destination.exists() and destination.read_text(encoding="utf-8") != data:
                raise IncompatibleCode(f"{rel} já existe com conteúdo diferente. Revisão manual necessária.")
            if not destination.exists():
                files_new[rel] = data
    except (IncompatibleCode, SyntaxError) as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        print("Nenhum arquivo foi modificado. Envie os arquivos backend/events.py e backend/serial_listener.py para uma adaptação específica.", file=sys.stderr)
        return 2
    changed = {name: text for name, text in updated.items() if text != original[name]}
    for name, new_content in changed.items():
        print("".join(difflib.unified_diff(original[name].splitlines(keepends=True), new_content.splitlines(keepends=True), fromfile=f"a/{name}", tofile=f"b/{name}")), end="")
    for name in files_new:
        print(f"NOVO: {name}")
    if not args.apply:
        print("\nModo de revisão: nada foi modificado. Para aplicar: python jade-integracao-v2/aplicar.py --apply")
        return 0
    if not changed and not files_new:
        print("As alterações já estavam presentes. Nenhum arquivo foi modificado.")
        return 0
    backup_dir = PACKAGE / "backups"
    backup_dir.mkdir(exist_ok=True)
    for name in changed:
        dst = backup_dir / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, dst)
    # All validation and backup steps precede the first write.
    for name, new_content in changed.items():
        (ROOT / name).write_text(new_content, encoding="utf-8")
    for name, text in files_new.items():
        dst = ROOT / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(text, encoding="utf-8")
    print(f"\nAlterações aplicadas. Backups dos arquivos modificados em {backup_dir}")
    print("Confira: git diff --check && git diff --stat")
    print("Teste: python -m pytest tests/test_serial_protocol.py tests/test_uart_jade.py -q")
    print("Atenção: confira a migração dos timestamps no PostgreSQL se a tabela events já existia.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
