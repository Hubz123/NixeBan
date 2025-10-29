from __future__ import annotations
import os, json, asyncio
try:
    import aiohttp
except Exception:
    aiohttp=None
MEM_KEY="lpg:mem:ahash:lucky"; FILE_FALLBACK="data/lpg_memory.json"
class _S: loaded=False; dirty=False; items=[]
S=_S()
async def _upstash_get():
    url=os.getenv("UPSTASH_REDIS_REST_URL"); tok=os.getenv("UPSTASH_REDIS_REST_TOKEN")
    if not(url and tok and aiohttp): return None
    try:
        async with aiohttp.ClientSession() as sess:
            async with sess.get(f"{url}/get/{MEM_KEY}", headers={"Authorization":f"Bearer {tok}"}) as r:
                j=await r.json(); raw=j.get("result"); 
                if not raw: return []
                try: return json.loads(raw)
                except Exception: return []
    except Exception: return None
async def _upstash_set(items):
    url=os.getenv("UPSTASH_REDIS_REST_URL"); tok=os.getenv("UPSTASH_REDIS_REST_TOKEN")
    if not(url and tok and aiohttp): return False
    try:
        payload=json.dumps(items, ensure_ascii=False)
        async with aiohttp.ClientSession() as sess:
            async with sess.get(f"{url}/set/{MEM_KEY}/{payload}", headers={"Authorization":f"Bearer {tok}"}) as r:
                _=await r.json(); return True
    except Exception: return False
def _file_get():
    try:
        with open(FILE_FALLBACK,"r",encoding="utf-8") as f: return json.load(f)
    except Exception: return []
def _file_set(items):
    import os, json
    try:
        os.makedirs(os.path.dirname(FILE_FALLBACK) or ".", exist_ok=True)
        with open(FILE_FALLBACK,"w",encoding="utf-8") as f: json.dump(items,f,ensure_ascii=False,indent=2)
        return True
    except Exception: return False
async def load():
    if S.loaded: return
    items=await _upstash_get()
    if items is None: items=_file_get()
    S.items=list(dict.fromkeys(items)); S.loaded=True; S.dirty=False
async def save():
    if not S.loaded: return
    ok=await _upstash_set(S.items)
    if not ok: _file_set(S.items)
    S.dirty=False
def remember(hash_hex: str, cap: int = 500):
    if hash_hex in S.items: return
    S.items.append(hash_hex); 
    if len(S.items)>cap: S.items=S.items[-cap:]
    S.dirty=True
