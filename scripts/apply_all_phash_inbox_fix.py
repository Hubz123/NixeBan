#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Apply-all fixer for phash_inbox_watcher.py across the repo.

Fixes:
1) Removes PEP585 return annotation from:
     def _parse_inbox_tokens(raw) -> tuple[set[str], set[int]]:
   -> becomes:
     def _parse_inbox_tokens(raw):
2) Ensures _get_inbox_thread is async (since callers await it).

Usage:
  python scripts/apply_all_phash_inbox_fix.py
  (Run from repo root; this will recursively patch any matching files)
"""
import re
from pathlib import Path

def patch_file(path: Path) -> bool:
    s = path.read_text(encoding="utf-8", errors="ignore")
    orig = s

    # 1) Drop PEP585 return annotation (robust regex)
    s = re.sub(
        r"def\s+_parse_inbox_tokens\s*\(\s*raw\s*\)\s*->\s*tuple\[[^\]]+\]\s*:",
        "def _parse_inbox_tokens(raw):",
        s,
        flags=re.M
    )

    # 2) Ensure async def for _get_inbox_thread (avoid double async)
    # Replace the first 'def _get_inbox_thread(self, ch):' with 'async def ...'
    s = re.sub(
        r"(^|\n)(?!async\s+)def\s+_get_inbox_thread\s*\(\s*self\s*,\s*ch\s*\)\s*:",
        r"\1async def _get_inbox_thread(self, ch):",
        s,
        flags=re.M
    )

    if s != orig:
        # backup once
        bak = path.with_suffix(path.suffix + ".bak")
        try:
            if not bak.exists():
                bak.write_text(orig, encoding="utf-8")
        except Exception:
            pass
        path.write_text(s, encoding="utf-8")
        return True
    return False

def main():
    root = Path.cwd()
    targets = list(root.rglob("nixe/cogs/phash_inbox_watcher.py"))
    if not targets:
        print("[WARN] No targets found.")
        return
    patched = 0
    for p in targets:
        try:
            if patch_file(p):
                print(f"[OK] Patched: {p}")
                patched += 1
            else:
                print(f"[INFO] No changes needed: {p}")
        except Exception as e:
            print(f"[ERR] Failed to patch {p}: {e}")
    print(f"[DONE] Patched files: {patched}/{len(targets)}")

if __name__ == "__main__":
    main()
