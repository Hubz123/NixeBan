import sys
from nixe.helpers.persona_loader import list_groups, pick_line

def assert_ok(cond, msg):
    if not cond:
        print("[FAIL]", msg)
        return False
    return True

def main():
    ok = True
    groups = set(list_groups("yandere"))
    ok &= assert_ok(groups == {"soft","agro","sharp","possessive"}, f"groups mismatch: {groups}")
    # explicit tones
    for tone in ("soft","agro","sharp","possessive","killer","yandere_killer","poss"):
        s = pick_line("yandere", tone=tone, user="@u", channel="#c", reason="deteksi")
        ok &= assert_ok(bool(s and "{user}" not in s), f"explicit tone failed: {tone}: {s!r}")
    # weighted & random
    for mode in ("weighted","random"):
        s = pick_line("yandere", mode=mode, user="@u", channel="#c", reason="deteksi")
        ok &= assert_ok(bool(s and "{user}" not in s), f"mode failed: {mode}: {s!r}")
    # by_score buckets
    tests = [(5,"soft"), (35,"possessive"), (70,"agro"), (95,"sharp")]
    for score, label in tests:
        s = pick_line("yandere", mode="by_score", score=score, user="@u", channel="#c", reason="deteksi")
        ok &= assert_ok(bool(s and "{user}" not in s), f"by_score {score} failed: {s!r}")
    if ok:
        print("[PASS] yandere persona v2 OK")
        sys.exit(0)
    sys.exit(1)

if __name__ == "__main__":
    main()
