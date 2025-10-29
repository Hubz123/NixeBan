# -*- coding: utf-8 -*-
from __future__ import annotations
import asyncio, logging, json as _json
from typing import List, Tuple
from nixe.helpers.env_reader import get as _cfg_get
log = logging.getLogger(__name__)
_SYS = ("You are an image classifier that detects scam/phishing creatives: fake giveaways (MrBeast, Nitro), "
        "QR-code scams, crypto doubling, fake login/file previews, suspicious payment screenshots. "
        "Return JSON: {'label':'phish'|'ok','confidence':0..1} strictly.")
_USER = ("Task: Decide if this image is scam/phishing. Consider big words (FREE, CLAIM, GIVEAWAY), celebrity bait, "
         "QR codes, login prompts, weird URLs. Hints: {hints}. Return JSON.")
async def classify_image_phish(images: List[bytes], *, hints: str = "", timeout_ms: int = 6000) -> Tuple[str, float]:
    try:
        import google.generativeai as genai
    except Exception as e:
        log.warning("[gphish] google-generativeai missing: %r", e)
        return "ok", 0.0
    try:
        genai.configure(api_key=_cfg_get("GEMINI_API_KEY"))
        model=_cfg_get("GEMINI_MODEL","gemini-2.5-flash")
        obj = genai.GenerativeModel(model_name=model, system_instruction=_SYS, generation_config={'response_mime_type':'application/json'})
        parts=[_USER.format(hints=hints)]
        for b in images[:2]:
            parts.append({"mime_type":"image/png","data":b})
        resp = await asyncio.wait_for(obj.generate_content_async(parts), timeout=timeout_ms/1000.0)
        tx = getattr(resp,"text","") or ""
        data = _json.loads(tx) if tx.strip().startswith("{") else {}
        label = data.get("label","ok"); conf=float(data.get("confidence",0.0))
        if label not in ("phish","ok"): label="ok"
        return label, conf
    except Exception as e:
        log.warning("[gphish] call failed: %r", e)
        return "ok", 0.0
