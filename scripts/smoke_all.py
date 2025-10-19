
"""
Comprehensive local "smoke" for Nixe.
- Validates config/env defaults
- Imports cogs & helpers
- Static checks for thresholds & guards
- Ensures templates exist
Exit 0 on success, 1 on failure.
"""
import sys, os, importlib, inspect

FAILS = []

def fail(msg):
    print("[FAIL]", msg)
    FAILS.append(msg)

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
    # Basic imports
    mods = [
        "nixe.config",
        "nixe.helpers.safeawait",
        "nixe.helpers.urltools",
        "nixe.cogs.image_phish_guard",
        "nixe.cogs.link_phish_guard",
    ]
    loaded = [check_import(m) for m in mods]

    # Config sanity
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

    # Template existence
    for p in ["templates/pinned_phash_db_template.txt", "templates/pinned_link_blacklist_template.txt"]:
        if not os.path.exists(p):
            fail(f"missing template: {p}")
        else:
            ok(f"template: {p}")

    # Module attributes quick peek
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
        print(f"SMOKE_ALL: {len(FAILS)} failures")
        sys.exit(1)
    print("SMOKE_ALL: OK")
    return 0

if __name__ == "__main__":
    main()
