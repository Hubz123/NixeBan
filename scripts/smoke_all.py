import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

# --- fixed: import Path for template checks ---
from pathlib import Path
import importlib

FAILS = []

def fail(msg):
    print("[FAIL]", msg); FAILS.append(msg)

def ok(msg):
    print("[OK]", msg)

def check_import(mod):
    try:
        importlib.invalidate_caches()
        m = importlib.import_module(mod)
        ok(f"import {mod}")
        return m
    except Exception as e:
        fail(f"import {mod}: {e}")
        return None

def main():
    mods = [
        "nixe.config",
        "nixe.helpers.safeawait",
        "nixe.helpers.urltools",
        "nixe.cogs.image_phish_guard",
        "nixe.cogs.link_phish_guard",
    ]
    loaded = [check_import(m) for m in mods]

    try:
        from nixe.config import load
        cfg = load()
        assert cfg.image.phash_distance_strict <= cfg.image.phash_distance_lenient, "strict must be <= lenient"
        assert cfg.image.warmup_seconds >= 0
        assert cfg.image.ban_cooldown_seconds >= 0
        assert cfg.image.ban_ceiling_per_10min >= 0
        ok("config thresholds sane")
    except Exception as e:
        fail(f"config sanity: {e}")

    for p in ["templates/pinned_phash_db_template.txt", "templates/pinned_link_blacklist_template.txt"]:
        try:
            if Path(p).exists():
                ok(f"template: {p}")
            else:
                fail(f"missing template: {p}")
        except Exception as e:
            fail(f"missing template: {p}: {e}")

    try:
        img = importlib.import_module("nixe.cogs.image_phish_guard")
        assert hasattr(img, "ImagePhishGuard"), "ImagePhishGuard missing"
        ok("ImagePhishGuard present")
    except Exception as e:
        fail(f"ImagePhishGuard check: {e}")

    try:
        lnk = importlib.import_module("nixe.cogs.link_phish_guard")
        assert hasattr(lnk, "LinkPhishGuard"), "LinkPhishGuard missing"
        ok("LinkPhishGuard present")
    except Exception as e:
        fail(f"LinkPhishGuard check: {e}")

    if FAILS:
        print(f"SMOKE_ALL: {len(FAILS)} failures"); raise SystemExit(1)
    print("SMOKE_ALL: OK")

if __name__ == "__main__":
    main()
