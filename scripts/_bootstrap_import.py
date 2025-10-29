import sys, os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = [ROOT, ROOT / "src"]
for cand in CANDIDATES:
    if cand.exists():
        s = str(cand)
        if s not in sys.path:
            sys.path.insert(0, s)
# Optional: show where we import from when debugging
def whereis(mod_name: str) -> str:
    try:
        mod = __import__(mod_name)
        p = getattr(mod, "__file__", None)
        return f"{mod_name} -> {p}"
    except Exception as e:
        return f"{mod_name} -> <not found> ({e})"
