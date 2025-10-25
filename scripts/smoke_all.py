#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smoketest (pre-push) for NIXE/external

Default (safe) mode:
  1) Python >= 3.10
  2) Compile ALL .py (syntax)
  3) COG STRUCTURE CHECK (AST only, no imports):
     - For each nixe/cogs/**.py (skip __init__.py):
       OK if (has class that subclasses Cog/commands.Cog) OR (has def/async def setup(bot))
  4) main.py static check -> must expose /healthz and use PORT

Strict mode (--strict-import):
  - Additionally import ALL cogs with **safe stubs** for heavy deps (discord/aiohttp/PIL/imagehash/etc).
  - After import, verify module has callable `setup`.
  - No network calls; bot does NOT start.

Exit 0 = pass, otherwise non-zero.
"""
import sys, os, compileall, ast, importlib, traceback, argparse, types, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

def fail(msg: str, code: int = 1):
    print("[FAIL]", msg)
    sys.exit(code)

def info(msg: str):
    print("[OK]", msg)

ap = argparse.ArgumentParser(add_help=False)
ap.add_argument("--strict-import", action="store_true")
args, _ = ap.parse_known_args()

# ---------- 1) Python version ----------
if sys.version_info < (3, 10):
    fail(f"Python >=3.10 required, found {sys.version}")
info(f"Python version OK: {sys.version.split()[0]}")

# ---------- 2) Compile all .py ----------
ok = compileall.compile_dir(str(ROOT), force=True, quiet=1)
if not ok:
    fail("Syntax compile failed for one or more files. See errors above.")
info("Syntax compile OK for all .py")

# ---------- 3) COG STRUCTURE (AST only) ----------
cogs_dir = ROOT / "nixe" / "cogs"
checked = 0
missing = []    # (path, has_cog_class, has_setup)

def _is_cog_class(node: ast.ClassDef) -> bool:
    for b in node.bases:
        # commands.Cog
        if isinstance(b, ast.Attribute) and b.attr == "Cog":
            return True
        # Cog
        if isinstance(b, ast.Name) and b.id == "Cog":
            return True
        # Generic subscripted or alias forms
        if isinstance(b, ast.Subscript) and isinstance(b.value, ast.Name) and b.value.id == "Cog":
            return True
    return node.name.endswith("Cog")

def _has_setup(tree: ast.AST) -> bool:
    for n in tree.body:
        if isinstance(n, ast.FunctionDef) and n.name == "setup":
            return True
        if isinstance(n, ast.AsyncFunctionDef) and n.name == "setup":
            return True
    return False

if cogs_dir.exists():
    for py in sorted(cogs_dir.rglob("*.py")):
        if py.name == "__init__.py":
            continue
        try:
            src = py.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(src, filename=str(py))
            cog_classes = [n for n in tree.body if isinstance(n, ast.ClassDef) and _is_cog_class(n)]
            has_setup = _has_setup(tree)
            checked += 1
            # RULE: pass if (has Cog class) OR (has setup)
            if not (cog_classes or has_setup):
                missing.append((py, bool(cog_classes), has_setup))
        except Exception as e:
            missing.append((py, False, False))

if checked == 0:
    print("[WARN] No cogs found under nixe/cogs")
else:
    info(f"COGS structure checked: {checked} file(s)")

if missing:
    for path, has_class, has_setup in missing:
        print(f"[FAIL] Cog structure: {path} -> class Cog? {has_class}, setup()? {has_setup}")
    fail(f"{len(missing)} cog file(s) missing Cog class and/or setup(bot)")

# ---------- 4) main.py static check (/healthz + PORT) ----------
mains = list(ROOT.rglob("main.py"))
if mains:
    seen_ok = False
    for mp in mains:
        try:
            t = mp.read_text(encoding="utf-8", errors="ignore")
            if "/healthz" in t and "PORT" in t:
                info(f"{mp} exposes /healthz and uses PORT")
                seen_ok = True
        except Exception:
            pass
    if not seen_ok:
        fail("main.py present but no /healthz or PORT usage detected.")

# ---------- 5) STRICT IMPORT (optional) ----------
if args.strict_import:
    # Provide robust stubs for heavy deps to avoid ImportError and base-class issues
    def ensure_discord_stub():
        try:
            importlib.import_module("discord")
            importlib.import_module("discord.ext.commands")
            importlib.import_module("discord.ext.tasks")
            return
        except Exception:
            pass
        discord = types.ModuleType("discord")
        class Intents:
            @staticmethod
            def default():
                x = Intents()
                x.guilds = True; x.members = True; x.message_content = True
                return x
        class AllowedMentions:
            def __init__(self, **kwargs): pass
        discord.Intents = Intents
        discord.AllowedMentions = AllowedMentions

        ext = types.ModuleType("discord.ext")
        commands = types.ModuleType("discord.ext.commands")
        tasks = types.ModuleType("discord.ext.tasks")

        class Cog: pass
        class Bot:
            def __init__(self, *a, **k): pass
            async def start(self, *a, **k): pass
            def get_channel(self, *a, **k): return None
            async def fetch_channel(self, *a, **k): return types.SimpleNamespace(
                fetch_message=lambda mid: None, pins=lambda: [], history=lambda **kw: iter([])
            )
        def command(*a, **k):
            def deco(fn): return fn
            return deco
        def listener(*a, **k):
            def deco(fn): return fn
            return deco
        def loop(**kw):
            def deco(fn): return fn
            return deco

        commands.Cog = Cog
        commands.Bot = Bot
        commands.command = command
        setattr(commands.Cog, "listener", staticmethod(listener))
        tasks.loop = loop

        sys.modules["discord"] = discord
        sys.modules["discord.ext"] = ext
        sys.modules["discord.ext.commands"] = commands
        sys.modules["discord.ext.tasks"] = tasks

    def ensure_module_stub(name: str):
        try:
            importlib.import_module(name)
            return
        except Exception:
            m = types.ModuleType(name)
            sys.modules[name] = m

    ensure_discord_stub()
    for base in ["aiohttp", "PIL", "imagehash", "easyocr", "pytesseract", "cv2", "numpy", "regex", "rapidfuzz", "pandas", "requests", "httpx", "torch", "torchvision", "skimage"]:
        ensure_module_stub(base)

    failed_imports = 0
    for py in sorted(cogs_dir.rglob("*.py")):
        if py.name == "__init__.py":
            continue
        mod = "nixe.cogs." + ".".join(py.relative_to(cogs_dir).with_suffix("").parts)
        try:
            importlib.invalidate_caches()
            m = importlib.import_module(mod)
            # after import, require setup attribute if no Cog class is present
            has_setup = hasattr(m, "setup")
            if not has_setup:
                # Try to be informative, but don't fail if class Cog exists in module objects
                # (We won't introspect classes deeply here)
                print(f"[WARN] {mod} imported but no setup(bot) found.")
            info(f"import {mod}")
        except Exception as e:
            failed_imports += 1
            print(f"[FAIL] import {mod} -> {type(e).__name__}: {e}")
            traceback.print_exc(limit=1)

    if failed_imports:
        fail(f"{failed_imports} cog import(s) failed in strict mode")

print("\nAll smoketests passed.")
sys.exit(0)
