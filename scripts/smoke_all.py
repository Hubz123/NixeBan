#!/usr/bin/env python3
"""
Enhanced smoke test for NIXE (Leina parity)
- Verifies config (sections + thresholds sane)
- Imports helpers
- Imports all core cogs & checks `async def setup(bot)` exists
- Scans ban_commands source to verify command names (!testban/!tb and !ban)
- Verifies templates present
- Verifies quiet healthz module importable
"""

import importlib, inspect, sys, os, pkgutil, json, re, pathlib, types, traceback

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

OK = []
FAIL = []

def print_res(label, ok, err=None):
    (OK if ok else FAIL).append(label if ok else f"{label}: {err or ''}")
    print(f"[{'OK' if ok else 'FAIL'}] {label}{'' if ok else f': {err}'}")

def safe_check(label, fn):
    try:
        fn(); print_res(label, True)
    except Exception as e:
        print_res(label, False, str(e))

def check_config():
    cfg = importlib.import_module("nixe.config")
    # access styles
    C = cfg.load()
    assert hasattr(C, "image")
    img = C.image
    assert img["phash_distance_strict"] <= img["phash_distance_lenient"]
    assert img["warmup_seconds"] >= 0
    assert img["ban_cooldown_seconds"] >= 0
    assert img["ban_ceiling_per_10min"] >= 0
    print_res("config thresholds sane", True)

def check_helpers():
    importlib.import_module("nixe.helpers.safeawait")
    importlib.import_module("nixe.helpers.urltools")

def _iter_cogs(base="nixe.cogs"):
    pkg = importlib.import_module(base)
    for mod in pkgutil.iter_modules(pkg.__path__, base + "."):
        name = mod.name
        if name.endswith(".__pycache__"): continue
        yield name

CORE_COGS = {
    "nixe.cogs.ban_commands",
    "nixe.cogs.ban_embed",
    "nixe.cogs.image_phish_guard",
    "nixe.cogs.link_phish_guard",
    "nixe.cogs.phash_inbox_watcher",
    "nixe.cogs.ready_shim",
    # loaders just import-check (don't run setup to avoid extension recursion)
    "nixe.cogs.cogs_loader",
    "nixe.cogs.loader_leina",
}
OPTIONAL_COGS = set()

def check_cog_imports_and_setup():
    for name in sorted(set(CORE_COGS) | set(_iter_cogs())):
        mod = importlib.import_module(name)
        label = f"import {name}"
        print_res(label, True)
        # For loader cogs, skip setup signature enforcement to avoid side-effects
        if name.split(".")[-1] in {"cogs_loader","loader_leina"}:
            continue
        setup = getattr(mod, "setup", None)
        if setup is None or not inspect.iscoroutinefunction(setup):
            raise AssertionError(f"{name}.setup must be async def")
        print_res(f"setup() present: {name}", True)

def check_templates():
    t1 = ROOT / "templates" / "pinned_phash_db_template.txt"
    t2 = ROOT / "templates" / "pinned_link_blacklist_template.txt"
    if not t1.exists(): raise FileNotFoundError(str(t1))
    if not t2.exists(): raise FileNotFoundError(str(t2))

def check_ban_commands_source():
    p = ROOT / "nixe" / "cogs" / "ban_commands.py"
    s = p.read_text(encoding="utf-8", errors="ignore")
    # Ensure !testban/!tb and !ban are declared
    if not re.search(r"@commands\.command\([^)]*name=['\"]testban['\"]", s):
        raise AssertionError("!testban missing")
    if not re.search(r"@commands\.command\([^)]*name=['\"]ban['\"]", s):
        raise AssertionError("!ban missing")
    print_res("BAN commands present", True)

def check_quiet_healthz():
    importlib.import_module("nixe.web.quiet_healthz")

def main():
    safe_check("import nixe.config", check_config)
    safe_check("import nixe.helpers.safeawait", check_helpers)
    safe_check("import nixe.helpers.urltools", lambda: None)  # already in helpers check
    safe_check("import cogs & setup signatures", check_cog_imports_and_setup)
    safe_check("template: templates/pinned_phash_db_template.txt", check_templates)
    safe_check("BAN commands present", check_ban_commands_source)
    safe_check("quiet healthz import", check_quiet_healthz)
    if FAIL:
        print("SMOKE_ALL:", len(FAIL), "failures")
        sys.exit(1)
    print("SMOKE_ALL: OK")

if __name__ == "__main__":
    main()
