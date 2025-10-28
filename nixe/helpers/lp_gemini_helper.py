
from __future__ import annotations
import base64, json, re
from typing import Optional, Tuple
from .env_reader import get
try:
    import urllib.request as _urlreq
except Exception:
    _urlreq=None
def _endpoint(model: str) -> str:
    return f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
def is_gemini_enabled() -> bool:
    return get("LUCKYPULL_GEMINI_ENABLE","1")=="1" and bool(get("GEMINI_API_KEY",""))
def score_lucky_pull_image(image_bytes: bytes, timeout: float = 7.0) -> Optional[Tuple[bool,float,str]]:
    if not is_gemini_enabled() or _urlreq is None: return None
    api_key=get("GEMINI_API_KEY",""); model=get("GEMINI_MODEL","gemini-1.5-flash")
    url=_endpoint(model)+f"?key={api_key}"
    b64=base64.b64encode(image_bytes).decode("ascii")
    body={"contents":[{"parts":[{"text":"Return JSON {\"is_lucky\": bool, \"score\": float, \"reason\": str} for whether this is a gacha lucky pull result screen. Be conservative."},{"inline_data":{"mime_type":"image/png","data":b64}}]}]}
    try:
        req=_urlreq.Request(url, data=json.dumps(body).encode("utf-8"), headers={"Content-Type":"application/json"})
        with _urlreq.urlopen(req, timeout=timeout) as resp:
            raw=resp.read().decode("utf-8", errors="ignore")
    except Exception: return None
    try:
        data=json.loads(raw); txt=""
        for c in data.get("candidates") or []:
            for p in (c.get("content") or {}).get("parts") or []:
                if "text" in p: txt+=p["text"]
        m=re.search(r"\{[^\}]*\}", txt, re.S)
        if not m: return None
        obj=json.loads(m.group(0))
        return (bool(obj.get("is_lucky",False)), float(obj.get("score",0.0)), str(obj.get("reason",""))[:200])
    except Exception: return None
def is_lucky_pull(image_bytes: bytes, threshold: float = 0.65):
    res=score_lucky_pull_image(image_bytes)
    if not res: return (False,0.0,"gemini_unavailable_or_low_confidence")
    ok,score,reason=res
    return (bool(ok and score>=float(threshold)), float(score), reason)
