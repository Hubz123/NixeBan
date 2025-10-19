import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

# Minimal smoke: ensure cogs importable as extensions (no side-effects at import)
from importlib import util

mods = [
    "nixe.cogs.image_phish_guard",
    "nixe.cogs.link_phish_guard",
    "nixe.helpers.urltools",
]

def check():
    ok = True
    for m in mods:
        spec = util.find_spec(m)
        print("[OK]" if spec else "[FAIL]", m)
        ok = ok and (spec is not None)
    raise SystemExit(0 if ok else 1)

if __name__ == "__main__":
    check()
