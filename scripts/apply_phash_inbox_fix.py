#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
In-place fixer for NIXE's phash_inbox_watcher.py

- Fix SyntaxError on Python 3.10 due to `tuple[set[str], set[int]]` annotation by removing the PEP585 return annotation.
- Ensure `_get_inbox_thread` is async, because caller awaits it.

Usage:
    python scripts/apply_phash_inbox_fix.py
    (Run from the project root; it will edit nixe/cogs/phash_inbox_watcher.py)
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # project root (../.. from scripts/)
TARGET = ROOT / "nixe" / "cogs" / "phash_inbox_watcher.py"

def main():
    if not TARGET.exists():
        print(f"[ERR] Not found: {TARGET}")
        raise SystemExit(2)
    s = TARGET.read_text(encoding="utf-8", errors="ignore")

    before = s

    # 1) Remove PEP585 return annotation to be more version-tolerant
    s = re.sub(
        r"def\s+_parse_inbox_tokens\s*\(\s*raw\s*\)\s*->\s*tuple\[[^\]]+\]\s*:",
        "def _parse_inbox_tokens(raw):",
        s,
        flags=re.M
    )

    # 2) Ensure async def for _get_inbox_thread (caller does: await self._get_inbox_thread(...))
    #    Do not double-insert 'async' if already there
    s = re.sub(
        r"\n(def\s+_get_inbox_thread\s*\(\s*self\s*,\s*ch\s*\)\s*:\s*)",
        "\nasync \",
        s,
        count=1
    )

    if s == before:
        print("[INFO] No changes applied (file already patched).")
    else:
        TARGET.write_text(s, encoding="utf-8")
        print("[OK] Patched:", TARGET)

if __name__ == "__main__":
    main()
