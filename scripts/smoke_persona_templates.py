import sys
from nixe.helpers.persona_loader import list_groups, pick_line

def main():
    ok = True
    # Ensure groups exist
    groups = list_groups("yandere")
    expected = {"soft", "agro", "sharp"}
    if set(groups) != expected:
        print(f"[FAIL] groups mismatch: got={groups}, expected={sorted(expected)}")
        ok = False
    # Sample a few lines to ensure formatting works
    for tone in ("soft", "agro", "sharp", None):
        s = pick_line("yandere", tone=tone, user="@someone", channel="#general", reason="deteksi lucky pull")
        if not s or "{user}" in s:
            print(f"[FAIL] pick_line returned unformatted/empty for tone={tone!r}: {s!r}")
            ok = False
    if ok:
        print("[PASS] yandere persona templates OK")
        sys.exit(0)
    sys.exit(1)

if __name__ == "__main__":
    main()
