#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Nixe-only cogs structure smoke (no network, no QnA checks).
- Verifies import purity for each cog.
- Ensures each cog defines setup(bot).
- Forbids 'satpambot' imports.
- Flags module-level side-effects (create_task/Client/basicConfig).
- Ensures required templates exist.
- Warns on duplicate Cog class names.
- Checks runtime_env.json for Nixe-critical keys only.
"""
import ast, os, re, sys, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "nixe"
COGS_DIR = PKG / "cogs"
TEMPLATES = [
    ROOT / "templates" / "pinned_phash_db_template.txt",
    ROOT / "templates" / "pinned_link_blacklist_template.txt",
]
ENV_JSON = PKG / "config" / "runtime_env.json"

PASS=WARN=FAIL=0
def _res(ok, label, extra=""):
    global PASS,WARN,FAIL
    if ok: PASS += 1; lvl="PASS"
    else: FAIL += 1; lvl="FAIL"
    line = f"[{lvl}] {label}"
    if extra: line += f": {extra}"
    print(line)

def _warn(label, extra=""):
    global WARN
    WARN += 1
    msg = f"[WARN] {label}"
    if extra: msg += f": {extra}"
    print(msg)

def _read(p: Path):
    try:
        return p.read_text(encoding="utf-8")
    except Exception as e:
        _res(False, f"read {p}", str(e))
        return ""

def check_core_imports():
    ok = True
    for mod in ("nixe.config", "nixe.helpers.safeawait", "nixe.helpers.urltools"):
        try:
            __import__(mod)
        except Exception as e:
            ok = False
            _res(False, f"import {mod}", repr(e))
        else:
            _res(True, f"import {mod}")
    return ok

def scan_cog_file(path: Path):
    src = _read(path)
    if not src:
        return

    try:
        tree = ast.parse(src, filename=str(path))
    except Exception as e:
        _res(False, f"parse {path.relative_to(ROOT)}", repr(e))
        return

    # forbid satpambot import
    if re.search(r"\bfrom\s+satpambot\b|\bimport\s+satpambot\b", src):
        _res(False, f"{path.relative_to(ROOT)} imports satpambot")
    else:
        _res(True, f"{path.relative_to(ROOT)} no satpambot import")

    # setup(bot) presence
    def has_setup(tree):
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "setup":
                if node.args.args and node.args.args[0].arg == "bot":
                    return True
        return False
    if has_setup(tree):
        _res(True, f"{path.relative_to(ROOT)} has setup(bot)")
    else:
        _res(False, f"{path.relative_to(ROOT)} missing setup(bot)")

    # module-level side effects
    for node in getattr(tree, "body", []):
        if isinstance(node, ast.Expr) and isinstance(getattr(node, "value", None), ast.Call):
            func = node.value.func
            if isinstance(func, ast.Attribute) and func.attr == "create_task":
                _res(False, f"{path.relative_to(ROOT)} module-level asyncio.create_task")
            if isinstance(func, ast.Attribute) and func.attr == "basicConfig":
                _warn(f"{path.relative_to(ROOT)} logging.basicConfig at import")
    if re.search(r"\bdiscord\.Client\s*\(", src) or re.search(r"\bbot\.run\s*\(", src):
        _warn(f"{path.relative_to(ROOT)} discord client/run at import")

def scan_duplicate_cog_classes():
    classes = {}
    for p in COGS_DIR.glob("*.py"):
        if p.name.startswith("_"): 
            continue
        try:
            tree = ast.parse(_read(p), filename=str(p))
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.setdefault(node.name, []).append(p)
    dups = {k:v for k,v in classes.items() if len(v)>1}
    if dups:
        for name, files in dups.items():
            _warn(f"DUPLICATE_CLASS {name}", ", ".join(str(f.relative_to(ROOT)) for f in files))
    else:
        _res(True, "duplicate class scan")

def check_templates():
    ok=True
    for t in TEMPLATES:
        if t.exists():
            _res(True, f"template exists {t.relative_to(ROOT)}")
        else:
            ok=False
            _res(False, f"template missing {t.relative_to(ROOT)}")
    return ok

def check_env_json():
    if not ENV_JSON.exists():
        _warn("runtime_env.json missing (ok for dev if using .env or overrides)")
        return
    try:
        data = json.loads(_read(ENV_JSON))
    except Exception as e:
        _res(False, "runtime_env.json parse", repr(e))
        return

    required = [
        "DISCORD_TOKEN",
        "LOG_CHANNEL_ID",
        "PHASH_DB_THREAD_ID",
        "PHISH_LOG_CHAN_ID",
        "NIXE_PHISH_LOG_CHAN_ID",
        "PHASH_IMAGEPHISH_THREAD_ID",
        "STRICT_PHASH_EDIT",
        "GACHA_GUARD_ENABLED",
        "GACHA_REDIRECT_CHANNEL_ID",
    ]
    for k in required:
        v = str(data.get(k, "")).strip()
        if v in ("", "0", "None", "null"):
            _warn(f"ENV {k} is empty")
        else:
            _res(True, f"ENV {k} present")

    # Optional ML keys (no warn if missing)
    for opt in ("GEMINI_API_KEY","GROQ_API_KEY"):
        v = str(data.get(opt, "")).strip()
        if v:
            _res(True, f"ENV {opt} present (optional)")

def main():
    print("=== NIXE COGS STRUCTURE SMOKE (pure) ===")
    check_core_imports()
    if not COGS_DIR.exists():
        _res(False, "cogs dir", f"not found: {COGS_DIR}")
    else:
        for p in sorted(COGS_DIR.glob("*.py")):
            if p.name.startswith("_"): 
                continue
            scan_cog_file(p)

    scan_duplicate_cog_classes()
    check_templates()
    check_env_json()

    print("\n=== SUMMARY ===")
    print(f"PASS : {PASS}")
    print(f"WARN : {WARN}")
    print(f"FAIL : {FAIL}")
    print(f"TOTAL: {PASS + WARN + FAIL}")

if __name__ == "__main__":
    main()
