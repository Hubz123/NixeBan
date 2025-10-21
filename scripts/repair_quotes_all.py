#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TRIPLE_DQ = '"' * 3
TRIPLE_SQ = "'" * 3
RX_TRIPLE_DQ = re.compile(r'(?:\\")\s*(?:\\")\s*(?:\\")')
RX_TRIPLE_SQ = re.compile(r"(?:\\')\s*(?:\\')\s*(?:\\')")

def fix_text(s: str) -> str:
    s = RX_TRIPLE_DQ.sub(TRIPLE_DQ, s)
    s = RX_TRIPLE_SQ.sub(TRIPLE_SQ, s)
    return s

def main() -> int:
    changed = 0
    for p in ROOT.rglob('*.py'):
        txt = p.read_text(encoding='utf-8', errors='ignore')
        new = fix_text(txt)
        if new != txt:
            p.write_text(new, encoding='utf-8')
            changed += 1
            print('fixed:', p.relative_to(ROOT))
    print('done. files changed:', changed)
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())
