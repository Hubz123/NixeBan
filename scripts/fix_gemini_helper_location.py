#!/usr/bin/env python3
"""
Move any *_gemini_helper.py from nixe/cogs/ to nixe/helpers/ to avoid "invalid cog" FAIL.
Safe to re-run.
"""
import os, shutil, glob, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
cg = ROOT / "nixe" / "cogs"
hp = ROOT / "nixe" / "helpers"
hp.mkdir(parents=True, exist_ok=True)

moved = 0
for p in cg.glob("*gemini_helper.py"):
    dest = hp / p.name
    shutil.move(str(p), str(dest))
    moved += 1
print(f"[OK] moved {moved} file(s) to helpers")
