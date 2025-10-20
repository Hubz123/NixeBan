# scripts/smoke_gacha_guard.py (robust)
import sys
from pathlib import Path

# Ensure repo root on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def main():
    import importlib
    mod = importlib.import_module("nixe.cogs.gacha_luck_guard")
    assert hasattr(mod, "CONFIG"), "CONFIG missing"
    assert hasattr(mod, "GachaLuckGuard"), "GachaLuckGuard missing"
    print("[SMOKE] import OK; no side-effects on import")
    print(f"[SMOKE] guard channels: {getattr(mod.CONFIG, 'guard_channel_ids', None)}")
    print(f"[SMOKE] redirect: {getattr(mod.CONFIG, 'redirect_channel_id', None)}")

if __name__ == "__main__":
    main()
