#!/usr/bin/env python3
from pathlib import Path
import shutil, re
root = Path(__file__).resolve().parents[1]
cogs = root/'nixe'/'cogs'
helpers = root/'nixe'/'helpers'
helpers.mkdir(parents=True, exist_ok=True)
moved=0
if cogs.exists():
    for p in cogs.glob('*helper*.py'):
        txt = p.read_text(encoding='utf-8', errors='ignore')
        if "commands.Cog" in txt:
            continue
        shutil.move(str(p), str(helpers/p.name)); moved+=1
print(f'[OK] moved {moved} helper(s) to nixe/helpers')
