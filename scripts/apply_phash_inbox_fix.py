
#!/usr/bin/env python3
from __future__ import annotations
import re, sys, pathlib

def main():
    if len(sys.argv) < 2:
        print("usage: apply_phash_inbox_fix.py <file.py>"); return 2
    target = pathlib.Path(sys.argv[1])
    s = target.read_text(encoding="utf-8")
    s = re.sub(r"\n(def\s+_get_inbox_thread\s*\(\s*self\s*,\s*ch\s*\)\s*:\s*)", r"\nasync \1", s, count=1)
    target.write_text(s, encoding="utf-8")
    print("[OK] patched:", target)
    return 0

if __name__ == "__main__":
    sys.exit(main() or 0)
