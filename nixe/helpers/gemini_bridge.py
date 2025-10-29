# nixe/helpers/gemini_bridge.py
from __future__ import annotations
import asyncio, json, logging, os
from typing import Iterable, Tuple, Any
log = logging.getLogger("nixe.helpers.gemini_bridge")
try:
    from nixe.helpers.image_cleaner import clean_for_gemini_bytes  # type: ignore
except Exception:
    clean_for_gemini_bytes = None

def _load_runtime_env() -> dict:
    path = os.getenv("RUNTIME_ENV_PATH") or "nixe/config/runtime_env.json"
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _get_model_name() -> str:
    env = _load_runtime_env()
    return os.getenv("GEMINI_MODEL") or env.get("GEMINI_MODEL") or "gemini-2.5-flash"

def _get_api_key() -> str | None:
    return os.getenv("GEMINI_API_KEY")

def _mk_image_part(b: bytes) -> dict:
    return {"mime_type": "image/png", "data": b}

def _parse_json(s: str) -> dict | None:
    s = s.strip()
    if s.startswith("```"):
        s = s.strip("`")
        if s.startswith("json"):
            s = s[len("json"):].strip()
    try:
        return json.loads(s)
    except Exception:
        import re
        m = re.search(r'\{.*\}', s, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
        return None

def _build_prompt(hints: str = "") -> str:
    base = "Klasifikasikan apakah gambar ini merupakan 'lucky pull' (gacha result screenshot/art)."
    if hints:
        base += f" Konteks: {hints}."
    base += " Jawab dalam JSON murni: {\"label\": \"lucky\"|\"other\", \"conf\": 0..1}."
    return base

async def _gemini_generate(parts: list[Any], *, timeout_ms: int) -> dict | None:
    try:
        import google.generativeai as genai  # type: ignore
    except Exception as e:
        log.warning("[gemini] sdk import failed: %r", e)
        return None
    api_key = _get_api_key()
    if not api_key:
        log.warning("[gemini] missing GEMINI_API_KEY")
        return None
    model_name = _get_model_name()
    def _call_sync() -> dict | None:
        genai.configure(api_key=api_key)
        try:
            model = genai.GenerativeModel(model_name)
        except Exception as e:
            log.warning("[gemini] model init failed: %r", e)
            return None
        try:
            resp = model.generate_content(parts)
            txt = getattr(resp, "text", None)
            if isinstance(txt, str) and txt.strip():
                data = _parse_json(txt)
                return data
            try:
                return _parse_json(str(resp))
            except Exception:
                return None
        except Exception as e:
            log.warning("[gemini] call failed: %r", e)
            return None
    try:
        return await asyncio.wait_for(asyncio.get_running_loop().run_in_executor(None, _call_sync), timeout=timeout_ms/1000.0)
    except Exception as e:
        log.warning("[gemini] timeout/error: %r", e)
        return None

async def classify_lucky_pull(images: Iterable[bytes] | None, *, hints: str = "", timeout_ms: int = 20000) -> Tuple[str, float]:
    if not images:
        return ("other", 0.0)
    first: bytes | None = None
    for b in images:
        if isinstance(b, (bytes, bytearray)):
            first = bytes(b); break
    if first is None:
        return ("other", 0.0)
    if clean_for_gemini_bytes:
        try:
            first = clean_for_gemini_bytes(first)
        except Exception:
            pass
    parts: list[Any] = [_build_prompt(hints), _mk_image_part(first)]
    data = await _gemini_generate(parts, timeout_ms=timeout_ms)
    if not isinstance(data, dict):
        return ("other", 0.0)
    label = str(data.get("label", "other")).strip().lower()
    try: conf = float(data.get("conf", 0.0))
    except Exception: conf = 0.0
    if label not in ("lucky","other"): label = "other"
    conf = max(0.0, min(1.0, conf))
    return (label, conf)
