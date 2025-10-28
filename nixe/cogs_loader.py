from __future__ import annotations
from pathlib import Path
import re
def _is_valid_cog(txt:str)->bool:
    if 'commands.Cog' not in txt: return False
    if re.search(r'\b(async\s+)?def\s+setup\s*\(\s*bot\s*\)', txt) is None: return False
    return True
def discover()->list[str]:
    base=Path(__file__).resolve().parent/'cogs'; out:list[str]=[]
    if not base.exists(): return out
    for p in sorted(base.glob('*.py')):
        if p.name.startswith('_'): continue
        try: txt=p.read_text(encoding='utf-8', errors='ignore')
        except Exception: continue
        lname=p.name.lower()
        if any(k in lname for k in ('helper','gemini_helper')) and 'commands.Cog' not in txt: continue
        if _is_valid_cog(txt): out.append(str(p))
    return out
def discover_cogs(*a, **k): return discover()
def load_core(*a, **k): return True
