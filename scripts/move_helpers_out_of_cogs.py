
#!/usr/bin/env python3
from pathlib import Path; import shutil
root=Path(__file__).resolve().parents[1]
cogs=root/'nixe'/'cogs'; helpers=root/'nixe'/'helpers'
helpers.mkdir(parents=True, exist_ok=True)
moved=0
if cogs.exists():
    for p in cogs.glob('*.py'):
        txt=p.read_text(encoding='utf-8', errors='ignore')
        if "commands.Cog" in txt: continue
        lname=p.name.lower()
        if ('helper' in lname) or ('gemini' in lname) or ('phash' in lname):
            shutil.move(str(p), str(helpers/p.name)); moved+=1
print(f"[OK] moved {moved} helper-like file(s)")
