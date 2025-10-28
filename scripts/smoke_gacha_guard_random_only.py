import importlib, sys
from nixe.helpers.persona_loader import list_groups, pick_line

def main():
    ok = True
    try:
        mod = importlib.import_module("nixe.cogs.gacha_luck_guard_random_only")
        assert hasattr(mod, "setup"), "setup() missing in gacha_luck_guard_random_only"
        print("[PASS] cog import & setup present")
    except Exception as e:
        print("[FAIL] cog import:", e)
        ok = False
    try:
        groups = set(list_groups("yandere"))
        assert groups == {"soft","agro","sharp"}, f"groups mismatch: {groups}"
        s = pick_line("yandere", user="@u", channel="#c", reason="deteksi")
        assert s and "{user}" not in s, "persona formatting failed"
        print("[PASS] persona random-only OK")
    except Exception as e:
        print("[FAIL] persona:", e)
        ok = False
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
