# -*- coding: utf-8 -*-
from __future__ import annotations
import logging, asyncio, os, json as _json
from typing import Dict, List, Optional

log = logging.getLogger(__name__)

_JSON_SYS = (
    "You are an image classifier that decides if an image shows a GACHA/LUCKY PULL result "
    "(e.g., wish/pull results, 10x draw, star ratings, reward reveal, SSR/UR, pity, rate-up banner) "
    "from any game (HSR, Genshin, WuWa, etc.). "
    "Return STRICT JSON ONLY with keys: label (\"lucky_pull\" or \"other\") and confidence (0..1). "
    "Do NOT include any extra text."
)

_JSON_USER_TEMPLATE = (
    "Task: Classify the given image(s) as 'lucky_pull' or 'other'.\n"
    "Guidance: Look for results screen, multi-draw (10x), reveal cards, rarity stars, banner name/portrait, "
    "terms like wish/pull/gacha/pity/SSR/UR, or typical reward layouts. "
    "If strongly consistent with such UI, output confidence >= 0.80.\n"
    "Context hints (may be empty): {hints}\n"
    "Respond with JSON only."
)

async def _gemini_call(imgs: List[bytes], *, api_key: str, model: str, timeout_ms: int, hints: str="") -> Dict:
    try:
        import google.generativeai as genai  # type: ignore
    except Exception as e:
        return {"label":"other","confidence":0.0,"reason":f"no_sdk:{e}"}
    try:
        genai.configure(api_key=api_key)
        model_obj = genai.GenerativeModel(model_name=model, system_instruction=_JSON_SYS)
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
