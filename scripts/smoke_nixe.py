#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NIXE Smoketest v2.3 — strict & no self-false-positive
"""
import sys, os, ast, json, compileall, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THIS = Path(__file__).resolve()
sys.path.insert(0, str(ROOT))

EXPECTED_IDS = {"THREAD_DB": 1431192568221270108, "THREAD_IMAGEPHISH": 1409949797313679492, "LOG_BOTPHISHING": 1431178130155896882}

def PASS(msg): print(f"[PASS] {msg}")
def WARN(msg): print(f"[WARN] {msg}")
def FAIL(msg): print(f"[FAIL] {msg}")

def _load_text(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

def _parse_ast(p: Path):
    try:
        return ast.parse(_load_text(p), filename=str(p))
    except Exception:
        return None

def check_pyver(res):
    if sys.version_info >= (3,10):
        PASS(f"Python {sys.version.split()[0]}"); res["pass"] += 1
    else:
        FAIL(f"Python >=3.10 required, found {sys.version}"); res["fail"] += 1

def check_compile(res):
    ok = compileall.compile_dir(str(ROOT), force=True, quiet=1)
    if ok: PASS("Syntax compile OK untuk semua .py"); res["pass"] += 1
    else:  FAIL("Syntax compile gagal (lihat traceback di atas)"); res["fail"] += 1

def _choose_main():
    mains = list(ROOT.rglob("main.py"))
    if not mains: return None
    for mp in mains:
        if mp.parent == ROOT: return mp
    return mains[0]

def check_main_web(res):
    mp = _choose_main()
    if not mp:
        FAIL("main.py tidak ditemukan"); res["fail"] += 1; return None, ""
    text = _load_text(mp)
    ok_health = "/healthz" in text
    ok_port = "PORT" in text
    if ok_health and ok_port:
        PASS(f"{mp} expose /healthz dan memakai PORT"); res["pass"] += 1
    else:
        FAIL(f"{mp} TIDAK memenuhi healthz/PORT"); res["fail"] += 1
    if ("access_log=None" in text or
        "SilentAccessLogger" in text or
        "AccessLogger" in text or
        'logging.getLogger("aiohttp.access")' in text):
        PASS("Anti-spam aiohttp.access terpasang"); res["pass"] += 1
    else:
        WARN("Anti-spam aiohttp.access TIDAK terdeteksi (akses /healthz bisa spam)"); res["warn"] += 1
    return mp, text

def check_config_phash(res, main_text: str):
    mod = ROOT / "nixe" / "config_phash.py"
    if "nixe.config_phash" in main_text and mod.exists():
        src = _load_text(mod); vals = {}
        for k in ["PHASH_DB_THREAD_ID","PHASH_DB_MESSAGE_ID","PHASH_DB_STRICT_EDIT","PHASH_IMAGEPHISH_THREAD_ID","PHASH_DB_MAX_ITEMS","PHASH_BOARD_EDIT_MIN_INTERVAL"]:
            mm = re.search(rf"{k}\s*=\s*([^\n#]+)", src)
            if mm: vals[k] = mm.group(1).strip()
        try:
            thread_db = int(eval(vals.get("PHASH_DB_THREAD_ID","0"), {}))
            msg_id    = int(eval(vals.get("PHASH_DB_MESSAGE_ID","0"), {}))
            strict    = bool(eval(vals.get("PHASH_DB_STRICT_EDIT","True"), {}))
            learn_id  = int(eval(vals.get("PHASH_IMAGEPHISH_THREAD_ID","0"), {}))
        except Exception:
            FAIL("nixe/config_phash.py: tipe nilai tidak valid"); res["fail"] += 1; return
        if thread_db == EXPECTED_IDS["THREAD_DB"]:
            PASS("THREAD NIXE (pHash DB) sesuai"); res["pass"] += 1
        else:
            WARN(f"THREAD NIXE berbeda: {thread_db} (ekspektasi {EXPECTED_IDS['THREAD_DB']})"); res["warn"] += 1
        if learn_id == EXPECTED_IDS["THREAD_IMAGEPHISH"]:
            PASS("THREAD imagephising sesuai"); res["pass"] += 1
        else:
            WARN(f"THREAD imagephising berbeda: {learn_id} (ekspektasi {EXPECTED_IDS['THREAD_IMAGEPHISH']})"); res["warn"] += 1
        if strict:
            PASS("Policy DB: EDIT-ONLY"); res["pass"] += 1
        else:
            FAIL("Policy DB bukan EDIT-ONLY (resiko membuat message baru)"); res["fail"] += 1
    else:
        if "PHASH_DB_THREAD_ID" in main_text or "PHASH_DB_MESSAGE_ID" in main_text:
            WARN("Konfigurasi pHash via ENV; disarankan pindah ke nixe/config_phash.py"); res["warn"] += 1
        else:
            FAIL("Tidak menemukan konfigurasi pHash (module/ENV)"); res["fail"] += 1

    offenders = []
    for py in ROOT.rglob("*.py"):
        if py.resolve() == THIS:
            continue  # skip smoketest sendiri
        lowname = py.name.lower()
        txt = _load_text(py)
        if ".send(" not in txt:
            continue
        strong = ("db_board" in lowname)
        if not strong:
            for m in re.finditer(r"\.send\s*\(", txt):
                start = max(0, m.start()-200); end = min(len(txt), m.end()+200)
                ctx = txt[start:end].lower()
                if "[phash-db-board]" in ctx or '"phash"' in ctx or "```json" in ctx:
                    strong = True; break
        if strong:
            offenders.append(str(py.relative_to(ROOT)))

    if offenders:
        WARN("Kemungkinan membuat message DB baru untuk BOARD pada: " + ", ".join(offenders)); res["warn"] += 1
    else:
        PASS("Tidak ada pattern pembuatan message DB baru untuk BOARD (aman)"); res["pass"] += 1

def check_cogs(res):
    cogs_dir = ROOT / "nixe" / "cogs"
    if not cogs_dir.exists():
        WARN("Folder nixe/cogs tidak ada"); res["warn"] += 1; return
    total = 0; missing = []; dup = {}
    def is_cog_class(node: ast.ClassDef) -> bool:
        for b in node.bases:
            if isinstance(b, ast.Attribute) and b.attr == "Cog": return True
            if isinstance(b, ast.Name) and b.id == "Cog": return True
        return node.name.endswith("Cog")
    for py in sorted(cogs_dir.rglob("*.py")):
        if py.name == "__init__.py": continue
        total += 1; tree = _parse_ast(py)
        if not tree:
            missing.append((py, False, False)); continue
        has_cog = any(isinstance(n, ast.ClassDef) and is_cog_class(n) for n in tree.body)
        has_setup = any((isinstance(n, ast.FunctionDef) or isinstance(n, ast.AsyncFunctionDef)) and n.name == "setup" for n in tree.body)
        if not (has_cog or has_setup):
            missing.append((py, has_cog, has_setup))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                        for kw in dec.keywords or []:
                            if kw.arg == "name":
                                v = kw.value; s = None
                                if isinstance(v, ast.Constant) and isinstance(v.value, str): s = v.value
                                elif isinstance(v, ast.Str): s = v.s
                                if s: dup.setdefault(s, []).append(f"{py.relative_to(ROOT)}::{node.name}")
    if total > 0:
        PASS(f"COGS ditemukan: {total} file"); res["pass"] += 1
    if missing:
        for p, hc, hs in missing:
            FAIL(f"Cog tidak valid: {p} -> class Cog? {hc}, setup()? {hs}"); res["fail"] += 1
    else:
        PASS("Semua cogs valid (class Cog ATAU setup(bot))"); res["pass"] += 1
    dups = {k: v for k, v in dup.items() if len(v) > 1}
    if dups:
        for k, locs in dups.items():
            WARN(f"Duplicate command name '{k}' di: {', '.join(locs)}"); res["warn"] += 1
    else:
        PASS("Tidak ada duplicate decorator command name"); res["pass"] += 1

def check_practices(res, main_text: str):
    offenders = {"aiohttp.ClientSession": [], "requests.http": []}
    for py in ROOT.rglob("*.py"):
        if py.resolve() == THIS:  # skip this smoketest file
            continue
        tree = _parse_ast(py)
        if not tree: continue
        for node in tree.body:
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
                f = node.value.func
                if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
                    if f.value.id == "aiohttp" and f.attr == "ClientSession":
                        offenders["aiohttp.ClientSession"].append(str(py.relative_to(ROOT)))
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                f = node.value.func
                if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id == "requests":
                    if f.attr in {"get","post","put","delete","head","patch"}:
                        offenders["requests.http"].append(str(py.relative_to(ROOT)))
    if offenders["aiohttp.ClientSession"] or offenders["requests.http"]:
        if offenders["aiohttp.ClientSession"]:
            WARN("Top-level aiohttp.ClientSession terdeteksi pada: " + ", ".join(sorted(set(offenders["aiohttp.ClientSession"])))); res["warn"] += 1
        if offenders["requests.http"]:
            WARN("Top-level requests.(http) terdeteksi pada: " + ", ".join(sorted(set(offenders["requests.http"])))); res["warn"] += 1
    else:
        PASS("Tidak ada top-level networking saat import"); res["pass"] += 1

    # Auto-restart patterns (skip this file + proximity)
    auto = []
    for py in ROOT.rglob("*.py"):
        if py.resolve() == THIS:
            continue
        t = _load_text(py)
        if "os.execv(" in t or "os._exit(" in t:
            auto.append(str(py.relative_to(ROOT))); continue
        if "while True" in t and "bot.start(" in t:
            auto.append(str(py.relative_to(ROOT))); continue
        for m in re.finditer(r"sys\\.exit\\([^)]*\\)", t, flags=re.I):
            start = max(0, m.start()-120); end = min(len(t), m.end()+120)
            if "restart" in t[start:end].lower():
                auto.append(str(py.relative_to(ROOT))); break
    if auto:
        FAIL("Pattern auto-restart terdeteksi: " + ", ".join(sorted(set(auto)))); res["fail"] += 1
    else:
        PASS("Tidak ada pattern auto-restart berbahaya"); res["pass"] += 1

    if "PyNaCl is not installed" in main_text and "OnceFilter" in main_text:
        PASS("Filter log discord.client (login/PyNaCl) aktif"); res["pass"] += 1
    else:
        WARN("Filter log discord.client (login/PyNaCl) tidak terdeteksi"); res["warn"] += 1

def check_render_yaml(res):
    ry = ROOT / "render.yaml"
    if not ry.exists():
        WARN("render.yaml tidak ada (OK jika deploy manual)"); res["warn"] += 1; return
    t = _load_text(ry)
    ok = ("type: web" in t) and (("python main.py" in t) or ("python3 main.py" in t))
    if ok:
        PASS("render.yaml: type web + start command valid"); res["pass"] += 1
    else:
        WARN("render.yaml: pastikan service type=web dan start 'python main.py'"); res["warn"] += 1
    if "worker" in t:
        FAIL("render.yaml: terdeteksi worker/background (Free Plan tidak mendukung)"); res["fail"] += 1

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--json-output", default=None)
    args = ap.parse_args()

    res = {"pass":0, "warn":0, "fail":0}
    check_pyver(res); check_compile(res)
    mp, mtxt = check_main_web(res)
    if mp is not None:
        check_config_phash(res, mtxt)
        check_practices(res, mtxt)
    check_cogs(res); check_render_yaml(res)
    print(f"\\n== SUMMARY ==  pass={res['pass']} warn={res['warn']} fail={res['fail']}")
    if args.json_output:
        with open(args.json_output, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2, ensure_ascii=False)
        print(f"JSON saved -> {args.json_output}")
    sys.exit(0 if res["fail"]==0 else 2)

if __name__ == "__main__":
    main()
