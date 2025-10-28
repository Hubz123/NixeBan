from __future__ import annotations
import os, logging, asyncio
from typing import Dict, Optional, List

log = logging.getLogger(__name__)

async def classify_lucky_pull(image_bytes_list: List[bytes], *, api_key: Optional[str], model: str = "gemini-1.5-flash", timeout_ms: int = 1200) -> Dict:
    if not api_key or not image_bytes_list:
        return {"label": "other", "confidence": 0.0, "reason": "no_api_or_empty"}
    try:
        import google.generativeai as genai  # type: ignore
    except Exception as e:
        return {"label": "other", "confidence": 0.0, "reason": f"no_sdk:{e}"}
    try:
        genai.configure(api_key=api_key)
        model_obj = genai.GenerativeModel(model)
        img = image_bytes_list[0]

        async def _do():
            import concurrent.futures
            loop = asyncio.get_running_loop()
            def _call():
                # SDK may support dict with mime/data; otherwise adapt as needed
                prompt = "Classify strictly: lucky_pull or other. Reply JSON {\"label\":\"lucky_pull|other\",\"confidence\":0..1}."
                return model_obj.generate_content([prompt, {"mime_type": "image/png", "data": img}])
            return await loop.run_in_executor(None, _call)

        resp = await asyncio.wait_for(_do(), timeout=timeout_ms/1000.0)
        txt = ""
        try:
            txt = resp.text or ""
        except Exception:
            txt = str(resp)

        import json as _json
        try:
            data = _json.loads(txt)
            label = str(data.get("label","other")).strip()
            conf = float(data.get("confidence",0.0))
        except Exception:
            low = txt.lower()
            if "lucky" in low or "pull" in low or "wish" in low or "gacha" in low:
                label, conf = "lucky_pull", 0.65
            else:
                label, conf = "other", 0.0
        return {"label": label, "confidence": max(0.0, min(1.0, conf)), "reason": "gemini"}
    except asyncio.TimeoutError:
        return {"label": "other", "confidence": 0.0, "reason": "timeout"}
    except Exception as e:
        return {"label": "other", "confidence": 0.0, "reason": f"error:{e}"}
