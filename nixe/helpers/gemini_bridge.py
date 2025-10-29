# -*- coding: utf-8 -*-
from __future__ import annotations
import logging, asyncio, os, json as _json
from nixe.helpers.env_reader import get as _cfg_get
from typing import Dict, List, Optional

log = logging.getLogger(__name__)

_JSON_SYS = (
    "You are an image classifier for GACHA/LUCKY-PULL result screens across many games. "
    "Typical cues: multiple vertical cards/panels, rarity frames/colors (SSR/SR/R/UR/N), "
    "star icons (3★..6★), rainbow/aurora glows, NEW/NEW!! tags, pity shards (×60/×150/×200/×440/×1000), "
    "and action buttons like 'Confirm', 'Recruit Again', 'Continue Herald', or headers like 'RESCUE RESULTS'. "
    "Return STRICT JSON ONLY: {'label': 'lucky_pull'|'other', 'confidence': 0..1}."
)

_JSON_USER_TEMPLATE = (
    "Task: Decide if this image is a gacha multi-pull RESULT screen.
"
    "Look for cues: vertical card strips; rarity text or frames (SSR/SR/R/UR/N, sometimes 'UP'); "
    "star icons; duplicate units; shards like ×60/×150/×200/×440/×1000; "
    "labels NEW/NEW!!; headers 'RESCUE RESULTS'; buttons 'Confirm'/'Recruit Again'/'Continue Herald'.
"
    "Hints: {hints}
"
    "Return strictly JSON like {\"label\":\"lucky_pull\",\"confidence\":0.92}."
)

async def _gemini_call(imgs: List[bytes], *, api_key: str, model: str, timeout_ms: int, hints: str="") -> Dict:
    try:
        import google.generativeai as genai  # type: ignore
    except Exception as e:
        return {"label":"other","confidence":0.0,"reason":f"no_sdk:{e}"}
    try:
        genai.configure(api_key=api_key)
        model_obj = genai.GenerativeModel(model_name=model, system_instruction=_JSON_SYS, generation_config={'response_mime_type':'application/json'})
        prompt = _JSON_USER_TEMPLATE.format(hints=hints or "(none)")
        parts = [prompt] + [{"mime_type":"image/png","data":b} for b in imgs]
        resp = await asyncio.wait_for(model_obj.generate_content_async(parts), timeout=timeout_ms/1000.0)
        txt = (getattr(resp, "text", None) or "").strip()
        if not txt:
            return {"label":"other","confidence":0.0,"reason":"empty"}
        try:
            data = _json.loads(txt)
            label = str(data.get("label","other")).strip()
            conf = float(data.get("confidence",0.0))
            return {"label":label, "confidence":max(0.0,min(1.0,conf)), "reason":"gemini"}
        except Exception:
            low = txt.lower()
            if any(k in low for k in ("lucky","pull","wish","gacha","10x","draw","pity","ssr","ur","banner")):
                return {"label":"lucky_pull","confidence":0.75,"reason":"parse_heur"}
            return {"label":"other","confidence":0.0,"reason":"parse_fail"}
    except asyncio.TimeoutError:
        return {"label":"other","confidence":0.0,"reason":"timeout"}
    except Exception as e:
        return {"label":"other","confidence":0.0,"reason":f"error:{e}"}

async def classify_lucky_pull(image_bytes_list: List[bytes], *, api_key: Optional[str]=None, model: str="gemini-2.5-flash", timeout_ms: int=1200, hints: str="") -> Dict:
    # Enforce latest only: NO FALLBACK to older models.
    if not api_key or not image_bytes_list:
        return {"label":"other","confidence":0.0,"reason":"no_api_or_empty"}
    imgs = image_bytes_list[:3]
    return await _gemini_call(imgs, api_key=api_key, model=model, timeout_ms=timeout_ms, hints=hints)
