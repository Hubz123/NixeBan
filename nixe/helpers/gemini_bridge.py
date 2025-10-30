# -*- coding: utf-8 -*-
from __future__ import annotations
import os, base64, logging, json, asyncio
from typing import Iterable, Tuple, List

try:
    import requests
except Exception:
    requests = None

log = logging.getLogger(__name__)

API_BASES: List[str] = [
    "https://generativelanguage.googleapis.com/v1beta",
    "https://generativelanguage.googleapis.com/v1",
]

def _models() -> List[str]:
    pref = (os.getenv("GEMINI_MODEL") or "").strip()
    fallbacks = [
        "gemini-2.5-flash",
        "gemini-2.5-flash-latest",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
        "gemini-1.5-flash-8b",
    ]
    out: List[str] = []
    if pref:
        out.append(pref)
    for m in fallbacks:
        if m not in out:
            out.append(m)
    return out

def _get_key() -> str:
    return (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()

def _guess_mime(data: bytes) -> str:
    if data.startswith(b"\x89PNG"): return "image/png"
    if data.startswith(b"\xff\xd8"): return "image/jpeg"
    if data[:6] in (b"GIF87a", b"GIF89a"): return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP": return "image/webp"
    return "image/png"

def _post(url: str, payload: dict, timeout: float, key: str, header_key: bool):
    headers = {"Content-Type": "application/json"}
    if header_key:
        headers["x-goog-api-key"] = key
        return requests.post(url, json=payload, headers=headers, timeout=timeout)
    else:
        return requests.post(f"{url}?key={key}", json=payload, headers=headers, timeout=timeout)

def _extract_text(resp_json: dict) -> str:
    try:
        cands = resp_json.get("candidates") or []
        if cands:
            return cands[0].get("content", {}).get("parts", [{}])[0].get("text", "") or ""
    except Exception:
        pass
    return ""

# ---------- Lucky Pull (existing) ----------
def _lp_prompt(hints: str = "") -> str:
    base = (
        "Task: Determine if an image is a gacha/lucky-pull RESULT screen.\n"
        "Return ONLY compact JSON: {\"label\":\"lucky|other\",\"confidence\":0..1}\n"
        "Guidelines:\n"
        "- 'lucky' if it shows the pull RESULT grid (10/11 cards), rarity stars (3-5★), NEW!! tag, rainbow/gold beams, or character/item tiles with stars.\n"
        "- Include games like Genshin, Honkai, Blue Archive, HSR, Umamusume, Wuthering Waves, Nikke, etc.\n"
        "- 'other' for chat images, memes, gameplay without result grid, banners, or loading/animation without final results.\n"
        "Scoring:\n"
        "- Clear result grid with stars or NEW!! -> confidence 0.85–0.98\n"
        "- Likely result grid but small/cropped -> 0.65–0.84\n"
        "- Unsure -> 0.30–0.64 (label 'other')\n"
    )
    if hints:
        base += f"Hints: {hints}\n"
    base += (
        "Examples:\n"
        "1) Image: 11 tiles in a row, gold/purple beams, some tiles say NEW!! -> {\"label\":\"lucky\",\"confidence\":0.92}\n"
        "2) Image: banner art with Start/Recruit buttons, no result tiles -> {\"label\":\"other\",\"confidence\":0.15}\n"
        "3) Image: one character splash with rainbow background (no grid) -> {\"label\":\"other\",\"confidence\":0.35}\n"
    )
    return base

def _lp_payload(img: bytes, hints: str = "") -> dict:
    return {
        "contents": [{
            "parts":[
                {"inline_data": {"mime_type": _guess_mime(img), "data": base64.b64encode(img).decode("ascii")}},
                {"text": _lp_prompt(hints)},
            ]
        }],
        "generationConfig": {"responseMimeType": "application/json"}
    }

async def classify_lucky_pull(images: Iterable[bytes], hints: str = "", timeout_ms: int = 10000) -> Tuple[str, float]:
    key = _get_key()
    imgs = list(images or [])
    if not imgs or not key or requests is None:
        return "other", 0.0
    timeout = max(3.0, timeout_ms / 1000.0)
    img = imgs[0]

    # Try v1beta first
    for model in _models():
        url = f"{API_BASES[0]}/models/{model}:generateContent"
        try:
            resp = await asyncio.to_thread(_post, url, _lp_payload(img, hints), timeout, key, True)
            if resp.status_code in (400,404):
                continue
            resp.raise_for_status()
            data = resp.json()
            text = _extract_text(data) or json.dumps(data)[:400]
            obj = json.loads(text)
            return (str(obj.get("label","other")), float(obj.get("confidence", 0.0)))
        except Exception:
            pass

    # Fallback v1
    for model in _models():
        url = f"{API_BASES[1]}/models/{model}:generateContent"
        try:
            resp = await asyncio.to_thread(_post, url, _lp_payload(img, hints), timeout, key, False)
            if resp.status_code in (400,404):
                continue
            resp.raise_for_status()
            data = resp.json()
            text = _extract_text(data) or json.dumps(data)[:400]
            obj = json.loads(text)
            return (str(obj.get("label","other")), float(obj.get("confidence", 0.0)))
        except Exception:
            pass

    return "other", 0.0

# ---------- Phish Image (new) ----------
def _phish_prompt(hints: str = "") -> str:
    base = (
        "Task: Detect whether an image is a screenshot/picture of a PHISHING page.\n"
        "Return ONLY compact JSON: {\"label\":\"phish|benign\",\"confidence\":0..1}\n"
        "Consider typical phish cues: fake login pages, wallet-connect prompts, 'claim reward' / giveaway pages,\n"
        "QR login scams, requests for OTP/seed phrases, brand impersonation with suspicious URLs,\n"
        "security alerts urging immediate action, password reset popups not from original site, etc.\n"
        "If the image is just a normal chat, meme, game screenshot or benign UI, return 'benign'.\n"
        "Scoring guideline: clear phishing UX -> 0.85–0.98; likely -> 0.65–0.84; unsure -> 0.30–0.64.\n"
    )
    if hints:
        base += f"Hints: {hints}\n"
    return base

def _phish_payload(img: bytes, hints: str = "") -> dict:
    return {
        "contents": [{
            "parts":[
                {"inline_data": {"mime_type": _guess_mime(img), "data": base64.b64encode(img).decode("ascii")}},
                {"text": _phish_prompt(hints)},
            ]
        }],
        "generationConfig": {"responseMimeType": "application/json"}
    }

async def classify_phish_image(images: Iterable[bytes], hints: str = "", timeout_ms: int = 12000) -> Tuple[str, float]:
    key = _get_key()
    imgs = list(images or [])
    if not imgs or not key or requests is None:
        return "benign", 0.0
    timeout = max(3.0, timeout_ms / 1000.0)
    img = imgs[0]

    # Try v1beta first
    for model in _models():
        url = f"{API_BASES[0]}/models/{model}:generateContent"
        try:
            resp = await asyncio.to_thread(_post, url, _phish_payload(img, hints), timeout, key, True)
            if resp.status_code in (400,404):
                continue
            resp.raise_for_status()
            data = resp.json()
            text = _extract_text(data) or json.dumps(data)[:400]
            obj = json.loads(text)
            lab = str(obj.get("label","benign")).lower()
            conf = float(obj.get("confidence", 0.0))
            return ("phish" if lab=="phish" else "benign", conf)
        except Exception:
            pass

    # Fallback v1
    for model in _models():
        url = f"{API_BASES[1]}/models/{model}:generateContent"
        try:
            resp = await asyncio.to_thread(_post, url, _phish_payload(img, hints), timeout, key, False)
            if resp.status_code in (400,404):
                continue
            resp.raise_for_status()
            data = resp.json()
            text = _extract_text(data) or json.dumps(data)[:400]
            obj = json.loads(text)
            lab = str(obj.get("label","benign")).lower()
            conf = float(obj.get("confidence", 0.0))
            return ("phish" if lab=="phish" else "benign", conf)
        except Exception:
            pass

    return "benign", 0.0
