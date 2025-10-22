#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
In-place fixer for NIXE's phash_inbox_watcher.py

- Fix Python 3.10 annotation error by removing PEP 585 return annotation (-> tuple[set[str], set[int]] -> -> tuple).
- Ensure `_get_inbox_thread` is async.

Usage:
    python scripts/apply_phash_inbox_fix.py
    (Run from project root; edits nixe/cogs/phash_inbox_watcher.py)
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "nixe" / "cogs" / "phash_inbox_watcher.py"

def main():
    if not TARGET.exists():
        print("[WARN] target not found:", TARGET)
        return
    s = TARGET.read_text(encoding="utf-8", errors="ignore")
    before = s

    # 1) Relax return annotation
    s = re.sub(
        r"(def\s+[_a-zA-Z0-9]+\s*\([^)]*\)\s*->\s*)tuple\s*\[[^\]]*\]",
        r"\1tuple",
        s
    )

    # 2) Ensure async def for _get_inbox_thread
    s = re.sub(
        r"(?m)^\s*def\s+_get_inbox_thread\s*\(",
        "async def _get_inbox_thread(",
        s
    )

    if s != before:
        TARGET.write_text(s, encoding="utf-8")
        print("[OK] Patched:", TARGET)
    else:
        print("[INFO] No changes applied (file already patched).")

if __name__ == "__main__":
    main()
