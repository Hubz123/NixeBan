from __future__ import annotations
from typing import Optional, Dict, Any, Set, Iterable
from pathlib import Path
def ensure_phash_board(*args, **kwargs) -> Dict[str, Any]:
    mid = int(str(kwargs.get('message_id', 0)) or 0); return {'ok': True, 'message_id': mid}
def update_phash_board(*args, **kwargs) -> Dict[str, Any]: return {'ok': True}
def find_phash_db_message(*args, **kwargs) -> Optional[int]: return int(str(kwargs.get('message_id', 0)) or 0)
def get_blacklist_hashes() -> Set[int]:
    out:set[int]=set(); p=Path(__file__).resolve().parents[1]/'data'/'phash_blacklist.txt'
    try:
        for line in p.read_text(encoding='utf-8').splitlines():
            s=line.strip().lower()
            if not s: continue
            try: out.add(int(s,16) if s.startswith('0x') else int(s))
            except: pass
    except Exception: pass
    return out
async def discover_db_message_id(bot)->int:
    try:
        from nixe import config_phash as _cfg
        return int(getattr(_cfg, 'PHASH_DB_MESSAGE_ID', 0) or 0)
    except Exception: return 0
def looks_like_phash_db(content:str)->bool:
    if not content: return False
    s=str(content).lower(); return ('phash' in s and 'db' in s) or ('token' in s and 'hash' in s) or ('blacklist' in s)
async def get_pinned_db_message(bot): return None
async def edit_pinned_db(bot, tokens: Iterable[str])->bool: return True
