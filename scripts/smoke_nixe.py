# -*- coding: utf-8 -*-
import os, sys, json, time, inspect, importlib, urllib.request
from pathlib import Path

EXPECT_SOURCE_THREAD_ID   = 1431192568221270108  # PHASH DB / NIXE thread
EXPECT_IMAGEPHISH_THREAD_ID = 1409949797313679492

ROOT = Path(__file__).resolve().parents[1]
ENVF = ROOT / "nixe" / "config" / "runtime_env.json"
env = {}
if ENVF.exists():
    try: env = json.loads(ENVF.read_text(encoding="utf-8"))
    except Exception: env = {}

def env_get(k, d=""):
    v = os.getenv(k)
    if v is None: v = env.get(k, d)
    return "" if v is None else str(v)

PASS=WARN=FAIL=0
def ok(msg):  print("[PASS]", msg);  globals()["PASS"]+=1
def wrn(msg): print("[WARN]", msg);  globals()["WARN"]+=1
def bad(msg): print("[FAIL]", msg);  globals()["FAIL"]+=1

# 1) import resolver & read thread IDs
try:
    cp = importlib.import_module("nixe.config_phash")
    src = getattr(cp, "NIXE_PHASH_SOURCE_THREAD_ID", 0)
    img = getattr(cp, "PHASH_IMAGEPHISH_THREAD_ID", 0)
    print(f"[INFO] config_phash from: {inspect.getsourcefile(cp) or cp.__file__}")
    print(f"[INFO] NIXE_PHASH_SOURCE_THREAD_ID={src}  PHASH_IMAGEPHISH_THREAD_ID={img}")

    if src == 0:
        bad("THREAD NIXE = 0 (resolver runtime_env.json salah)")
    elif src != EXPECT_SOURCE_THREAD_ID:
        wrn(f"THREAD NIXE beda: {src} (ekspektasi {EXPECT_SOURCE_THREAD_ID})")
    else:
        ok("THREAD NIXE sesuai")

    if img == 0:
        bad("THREAD imagephising = 0 (resolver runtime_env.json salah)")
    elif img != EXPECT_IMAGEPHISH_THREAD_ID:
        wrn(f"THREAD imagephising beda: {img} (ekspektasi {EXPECT_IMAGEPHISH_THREAD_ID})")
    else:
        ok("THREAD imagephising sesuai")
except Exception as e:
    bad(f"import nixe.config_phash: {e}")

# 2) lucky_pull_guard: wajib ada alias class LuckyPullGuard & setup aman
try:
    lpg = importlib.import_module("nixe.cogs.lucky_pull_guard")
    has_alias = hasattr(lpg, "LuckyPullGuard")
    has_setup = "async def setup" in inspect.getsource(lpg)
    if has_alias: ok("LuckyPullGuard tersedia (compat loader)")
    else: bad("LuckyPullGuard tidak ditemukan (perlu alias di lucky_pull_guard)")
    if has_setup: ok("lucky_pull_guard.setup ada (no-dup safe)")
    else: wrn("lucky_pull_guard.setup tidak terdeteksi (loader harus handle)")
except Exception as e:
    bad(f"import lucky_pull_guard: {e}")

# 3) dupe guard untuk LuckyPullAuto
try:
    lpa = Path(importlib.import_module("nixe.cogs.lucky_pull_auto").__file__)
    txt = lpa.read_text(encoding="utf-8", errors="ignore")
    if "bot.get_cog(\"LuckyPullAuto\")" in txt or "bot.get_cog('LuckyPullAuto')" in txt:
        ok("LuckyPullAuto setup: ada anti-duplicate guard")
    else:
        wrn("LuckyPullAuto setup: TIDAK ada anti-duplicate guard (risiko double load)")
except Exception as e:
    wrn(f"cek LuckyPullAuto guard: {e}")

# 4) project loader load_all()
try:
    cl = importlib.import_module("nixe.cogs_loader")
    if hasattr(cl, "load_all"):
        ok("cogs_loader.load_all tersedia")
    else:
        wrn("cogs_loader.load_all tidak ada (akan fallback autodiscover)")
except Exception as e:
    wrn(f"import cogs_loader: {e}")

# 5) lucky pull policy (hapus & mention) + redirect + guard channels
lp_delete = env_get("LUCKYPULL_DELETE_ON_GUARD","0") in ("1","true","on","yes")
lp_mention= env_get("LUCKYPULL_MENTION","0")         in ("1","true","on","yes")
redirect  = env_get("LUCKYPULL_REDIRECT_CHANNEL_ID","0")
guards    = [s.strip() for s in env_get("LUCKYPULL_GUARD_CHANNELS","").split(",") if s.strip()]

if lp_delete and lp_mention: ok("LuckyPull policy: hapus + mention aktif")
else: wrn("LuckyPull policy: disarankan DELETE_ON_GUARD=1 dan MENTION=1")

if redirect.isdigit() and int(redirect)>0: ok(f"LuckyPull redirect channel OK: {redirect}")
else: bad("LuckyPull redirect channel ID tidak valid")

if guards: ok(f"LuckyPull guard channels OK: {','.join(guards)}")
else: bad("LuckyPull guard channels kosong")

# 6) Gemini setup cepat (tanpa internet = skip)
gem_enable = env_get("LUCKYPULL_GEMINI_ENABLE","0") in ("1","true","on","yes")
model      = (env_get("GEMINI_MODEL","") or "").lower()
if gem_enable:
    if "2.5" in model:
        ok(f"Gemini enable + model={model}")
    else:
        wrn(f"Gemini enable tapi model bukan 2.5: {model or '(kosong)'}")
else:
    wrn("Gemini nonaktif (LUCKYPULL_GEMINI_ENABLE=0)")

# 7) Optional live ping jika punya key
key = env_get("GEMINI_API_KEY","").strip()
if key:
    try:
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
        data = json.dumps({"contents":[{"parts":[{"text":"ping"}]}]}).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST",
            headers={"Content-Type":"application/json","x-goog-api-key":key})
        t0=time.perf_counter()
        with urllib.request.urlopen(req, timeout=10) as r:
            ms=int((time.perf_counter()-t0)*1000)
            if 200<=r.status<300:
                ok(f"Gemini ping OK {ms}ms (HTTP {r.status})")
            else:
                wrn(f"Gemini ping HTTP {r.status}")
    except Exception as e:
        wrn(f"Gemini ping error: {e}")
else:
    wrn("GEMINI_API_KEY kosong: skip ping")

print("\\n== SUMMARY ==  pass=%d warn=%d fail=%d" % (PASS,WARN,FAIL))
if FAIL>0: sys.exit(1)
