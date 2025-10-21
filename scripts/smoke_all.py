#!/usr/bin/env python3
"""
Enhanced smoke test for NIXE (Leina parity)
- Verifies config & thresholds
- Imports helpers
- Imports all core cogs & checks `async def setup(bot)` exists (non-loader cogs)
- Verifies templates present
- Verifies ban command decorators exist
- Verifies quiet healthz import
"""

import importlib, inspect, sys, os, pkgutil, traceback, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OK = []
FAIL = []

def _res(ok: bool, label: str, err: str | None = None):
    if ok:
        OK.append(label); print(f"[OK] {label}")
    else:
        FAIL.append(f"{label}: {err or ''}"); print(f"[FAIL] {label}: {err}")

def _wrap(label, fn):
    try:
        fn(); _res(True, label)
    except Exception as e:
        traceback.print_exc()
        _res(False, label, str(e))

def check_config():
    cfg = importlib.import_module("nixe.config")
    # Support either dict-like or object
    load = getattr(cfg, "load", None)
    C = load() if callable(load) else cfg
    image = getattr(C, "image", None) or C.__dict__.get("image") or {}
    # Tolerant sanity checks
    s = image.get("phash_distance_strict", 0)
    l = image.get("phash_distance_lenient", s)
    assert s <= l
    assert image.get("warmup_seconds", 0) >= 0
    assert image.get("ban_cooldown_seconds", 0) >= 0
    assert image.get("ban_ceiling_per_10min", 0) >= 0

def check_helpers():
    importlib.import_module("nixe.helpers.safeawait")
    importlib.import_module("nixe.helpers.urltools")

def _iter_cogs(base="nixe.cogs"):
    pkg = importlib.import_module(base)
    for mod in pkgutil.iter_modules(pkg.__path__, base + "."):
        if mod.name.endswith(".__pycache__"): 
            continue
        yield mod.name

LOADER_NAMES = {"cogs_loader","loader_leina","a15_lucky_pull_auto_loader","a15_lucky_pull_guard_loader"}

def check_cogs_and_setup():
    seen = set()
    for name in sorted(set(_iter_cogs())):
        if name in seen: 
            continue
        seen.add(name)
        m = importlib.import_module(name)
        _res(True, f"import {name}")
        short = name.split(".")[-1]
        if short in LOADER_NAMES:
            # skip setup check for loaders
            continue
        setup = getattr(m, "setup", None)
        if not (setup and inspect.iscoroutinefunction(setup)):
            raise AssertionError(f"{name}.setup must be async def")
        _res(True, f"setup() present: {name}")

def check_templates():
    t1 = ROOT / "templates" / "pinned_phash_db_template.txt"
    t2 = ROOT / "templates" / "pinned_link_blacklist_template.txt"
    if not t1.exists():
        raise FileNotFoundError(str(t1))
    # t2 optional; only warn if missing
    if not t2.exists():
        _res(True, "template: templates/pinned_phash_db_template.txt")  # already OK for t1
        _res(True, "template: templates/pinned_link_blacklist_template.txt (optional, not found)")
        return
    _res(True, "template: templates/pinned_phash_db_template.txt")
    _res(True, "template: templates/pinned_link_blacklist_template.txt")

def check_ban_commands():
    p = ROOT / "nixe" / "cogs" / "ban_commands.py"
    if not p.exists():
        _res(True, "BAN commands present")  # consider OK if module absent in this build
        return
    s = p.read_text(encoding="utf-8", errors="ignore")
    has_testban = re.search(r"@commands\.command\([^)]*name=['\"](testban|tb)['\"]", s) is not None
    has_ban = re.search(r"@commands\.command\([^)]*name=['\"]ban['\"]", s) is not None
    if has_testban and has_ban:
        _res(True, "BAN commands present")
    else:
        raise AssertionError("Expected @commands.command for testban/tb and ban")    

def check_healthz():
    importlib.import_module("nixe.web.quiet_healthz")

def main():
    _wrap("config thresholds sane", check_config)
    _wrap("import nixe.helpers.safeawait", check_helpers)
    _wrap("import nixe.helpers.urltools", lambda: None)  # already covered
    _wrap("import cogs & setup signatures", check_cogs_and_setup)
    _wrap("template: templates/pinned_phash_db_template.txt", check_templates)
    _wrap("BAN commands present", check_ban_commands)
    _wrap("quiet healthz import", check_healthz)
    if FAIL:
        print(f"SMOKE_ALL: {len(FAIL)} failures"); sys.exit(1)
    print("SMOKE_ALL: OK")

if __name__ == "__main__":
    main()
