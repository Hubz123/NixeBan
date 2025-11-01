
# -*- coding: utf-8 -*-
from typing import Tuple
import os, json, base64, urllib.request, urllib.error

def _detect_mime(b: bytes) -> str:
    """Detect basic image mime from header bytes."""
    if b.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if b.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if b.startswith(b"RIFF") and b[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"

def _image_provider_order():
    order = os.environ.get("LPG_IMAGE_PROVIDER_ORDER") or os.environ.get("LPG_PROVIDER_ORDER") or "gemini,groq"
    items = [x.strip().lower() for x in order.split(",") if x.strip()]
    return items or ["gemini"]

def _extract_json_like(txt: str) -> dict:
    try:
        return json.loads(txt)
    except Exception:
        pass
    s = txt
    start = s.find("{")
    if start == -1:
        return {}
    depth = 0
    for i in range(start, len(s)):
        ch = s[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                block = s[start:i+1]
                try:
                    return json.loads(block)
                except Exception:
                    break
    return {}

def _gemini_call(img_bytes: bytes, model: str, timeout: float):
    api = os.environ.get("GEMINI_API_KEY")
    if not api:
        return (False, 0.0, "gemini:"+model, "GEMINI_API_KEY missing")
    url = "https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={k}".format(
        m=model, k=api
    )

    prompt = (
        "Return ONLY a JSON object with EXACT keys: "
        "{"
        "\"is_lucky\": true or false, "
        "\"confidence\": number between 0 and 1, "
        "\"reason\": string"
        "}. "
        "Classify whether the image is a gacha 'lucky pull' reveal (celebration/obtained screen)."
    )

    mime = _detect_mime(img_bytes)
    payload = {
        "generationConfig": {"response_mime_type": "application/json"},
        "contents":[{
            "role":"user",
            "parts":[
                {"inlineData": {"mimeType": mime, "data": base64.b64encode(bytes(img_bytes)).decode("ascii")}},
                {"text": prompt}
            ]
        }]
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type":"application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=float(timeout)) as resp:
            code = resp.getcode()
            text = resp.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "ignore")
        return False, 0.0, "gemini:"+model, "gemini_http_{c}: {b}".format(c=e.code, b=body[:200])
    except Exception as e:
        return False, 0.0, "gemini:"+model, str(e)

    if code != 200:
        return False, 0.0, "gemini:"+model, "gemini_http_{c}: {b}".format(c=code, b=text[:200])

    # Prefer JSON-only; fallback to text extraction
    try:
        data = json.loads(text)
    except Exception:
        data = {"text": text}

    if isinstance(data, dict) and "candidates" in data:
        parts = (data.get("candidates") or [{}])[0].get("content", {}).get("parts", [])
        txt = ""
        for p in parts:
            if "text" in p:
                txt = p["text"]
                break
        obj = _extract_json_like(txt)
    else:
        obj = data if isinstance(data, dict) else {}

    conf_raw = obj.get("confidence", 0.0)
    conf = float(conf_raw) if isinstance(conf_raw, (int, float)) else 0.0
    ok = bool(obj.get("is_lucky", False))
    reason = obj.get("reason", "ok" if ok else "not_lucky")
    return ok, conf, "gemini:"+model, reason

def classify_lucky_pull_bytes(img_bytes: bytes, threshold: float = 0.75, timeout: float = 20000.0, *args, **kwargs):
    last_provider, last_score, last_reason = "none", 0.0, ""
    order = _image_provider_order()
    model_gem = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")

    for p in order:
        try:
            if p == "gemini":
                ok, score, prov, reason = _gemini_call(img_bytes, model_gem, timeout)
                last_provider, last_score, last_reason = prov, float(score), reason
                if ok and score >= float(threshold):
                    return True, float(score), prov, reason
            elif p == "groq":
                # groq vision path intentionally not implemented in this bridge
                last_provider, last_reason = "groq", "groq_vision_path_not_implemented"
        except Exception as e:
            last_reason = str(e)
            continue

    return False, float(last_score), last_provider, last_reason
