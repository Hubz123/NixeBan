# scripts/smoke_lpg_whitelist.py
import os, sys, pathlib

# Ensure project root is on sys.path so "nixe" package is importable when running directly.
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

NEG = os.environ.get("LPG_NEG_FILE", "data/lpg_negative_hashes.txt")

def main():
    print("[SMOKE] project root:", ROOT)
    ok = os.path.exists(NEG)
    print("[SMOKE] NEG file exists:", ok, "->", NEG)
    if ok:
        try:
            n = sum(1 for _ in open(NEG, "r", encoding="utf-8"))
            print("[SMOKE] NEG lines:", n)
        except Exception as e:
            print("[SMOKE] WARN: failed to count lines:", e)
    print("OK")

if __name__ == "__main__":
    main()
