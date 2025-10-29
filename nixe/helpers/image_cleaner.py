# nixe/helpers/image_cleaner.py
from __future__ import annotations
import io
from PIL import Image

def clean_for_gemini_bytes(b: bytes) -> bytes:
    """
    Normalize various image bytes (webp, heic, etc.) to PNG bytes for Gemini.
    Drops alpha if necessary; resizes if absurdly large.
    """
    im = Image.open(io.BytesIO(b)).convert("RGB")
    # Optional: clamp max side to 2048 to avoid excessive payload
    MAX = 2048
    w, h = im.size
    if max(w, h) > MAX:
        scale = MAX / float(max(w, h))
        im = im.resize((max(1,int(w*scale)), max(1,int(h*scale))), Image.LANCZOS)
    out = io.BytesIO()
    im.save(out, format="PNG", optimize=True)
    return out.getvalue()
