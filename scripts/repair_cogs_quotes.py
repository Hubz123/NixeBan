#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COGS = ROOT / "nixe" / "cogs"

# Fix the common escaped triple-quote patterns that break Python parsing
PATTERNS = [
    (re.compile(r'\\"\\"\\"'), '"""'),
    (re.compile(r'"""'), '"""'),
    (re.compile(r'\"""'), '"""'),
    (re.compile(r'"""\"'), '"""'),
]

def fix_text(s: str) -> str:
    out = s
    for rx, rep in PATTERNS:
        out = rx.sub(rep, out)
    return out

def main() -> int:
    changed = 0
    if not COGS.exists():
        print("no cogs dir:", COGS)
        return 1
    for p in COGS.rglob("*.py"):
        t = p.read_text(encoding="utf-8", errors="ignore")
        ft = fix_text(t)
        if ft != t:
            p.write_text(ft, encoding="utf-8")
            changed += 1
            print("fixed:", p.relative_to(ROOT))
    print("done. files changed:", changed)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
