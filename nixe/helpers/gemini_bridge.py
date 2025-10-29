
# -*- coding: utf-8 -*-
from __future__ import annotations
import asyncio, logging, json as _json
from typing import List, Tuple

# Read API key / model via env_reader (runtime_env.json / secrets.json / ENV)
try:
    from nixe.helpers.env_reader import get as _cfg_get
except Exception:
    import os
    def _cfg_get(key: str, default: str = "") -> str:
        return str(os.environ.get(key, default)).strip()

log = logging.getLogger(__name__)

_JSON_SYS = """You are an image classifier specialized in detecting
GACHA / LUCKY-PULL RESULT screens across many games.
Typical cues:
- multiple vertical card/panel strips
- rarity frames/colors (SSR / SR / R / UR / N), sometimes 'UP'
- star icons (e.g., 3★..6★), rainbow/aurora glow
- labels like NEW / NEW!!
- pity shards counters (×60 / ×150 / ×200 / ×440 / ×1000)
- buttons like Confirm / Recruit Again / Continue Herald
Return STRICT JSON ONLY: {"label": "lucky_pull"|"other", "confidence": 0..1}.
"""

_JSON_USER_TEMPLATE = """Task: Decide if this image is a gacha multi-pull RESULT screen.
Look for cues listed above (vertical cards; SSR/SR/R/UR/N; stars; NEW; shards ×60/×150/×200/×440/×1000;
buttons Confirm/Recruit Again/Continue Herald; headers like RESCUE RESULTS).
Hints: {hints}
Return strictly a JSON object like {{"label":"lucky_pull","confidence":0.92}}.
"""

def _detect_mime(b: bytes) -> str:
    # Simple header sniffing; default to JPEG for compression-friendly payloads
    if not b:
        return "image/jpeg"
    sig = b[:16]
    if sig.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if sig[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if sig[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    return "image/jpeg"

async def _gemini_call(images: List[bytes], *, hints: str = "", timeout_ms: int = 10000) -> Tuple[str, float]:
    """Call Gemini in JSON mode. Returns (label, confidence)."""
    try:
        import google.generativeai as genai  # type: ignore
    except Exception as e:
        log.warning("[gemini] google-generativeai not installed: %r", e)
        return "other", 0.0

    api_key = _cfg_get("GEMINI_API_KEY", "")
    if not api_key:
        log.warning("[gemini] GEMINI_API_KEY is empty")
        return "other", 0.0

    model_name = _cfg_get("GEMINI_MODEL", "gemini-2.5-flash")
    try:
        genai.configure(api_key=api_key)
        model_obj = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=_JSON_SYS,
            generation_config={"response_mime_type": "application/json"},
        )

        parts: List[object] = [_JSON_USER_TEMPLATE.format(hints=hints or "").strip()]
        for b in images[: max(1, int(_cfg_get("LUCKYPULL_GEMINI_MAX_IMAGES", "1") or "1"))]:
            parts.append({"mime_type": _detect_mime(b), "data": b})

        resp = await asyncio.wait_for(
            model_obj.generate_content_async(parts),
            timeout=max(1.0, (timeout_ms or 10000) / 1000.0),
        )
        tx = getattr(resp, "text", "") or ""
        if not tx:
            return "other", 0.0

        # Parse strict JSON; be forgiving if model wrapped in code fences.
        tx = tx.strip()
        if tx.startswith("```"):
            # remove fences if any
            tx = tx.strip("`").strip()
            if tx.startswith("json"):
                tx = tx[4:].strip()
        try:
            data = _json.loads(tx)
        except Exception:
            # attempt to extract first JSON object
            import re
            m = re.search(r"\{[\s\S]*\}", tx)
            data = _json.loads(m.group(0)) if m else {}

        label = str(data.get("label", "other")).strip().lower()
        conf = float(data.get("confidence", 0.0))
        if label not in ("lucky_pull", "other"):
            label = "other"
        # Clamp confidence
        if conf < 0.0: conf = 0.0
        if conf > 1.0: conf = 1.0
        return label, conf
    except asyncio.TimeoutError:
        log.warning("[gemini] timeout after %d ms", timeout_ms)
        return "other", 0.0
    except Exception as e:
        log.warning("[gemini] call failed: %r", e)
        return "other", 0.0

# Public API expected by guards/warmup
async def classify_lucky_pull(images: List[bytes], *, hints: str = "", timeout_ms: int = 10000) -> Tuple[str, float]:
    """
    Return ("lucky_pull" | "other", confidence 0..1).
    """
    return await _gemini_call(images, hints=hints, timeout_ms=timeout_ms)
