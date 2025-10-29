# nixe/helpers/image_cleaner.py
from __future__ import annotations
import io
from PIL import Image

def clean_for_gemini_bytes(b: bytes) -> bytes:
    im = Image.open(io.BytesIO(b)).convert("RGB")
    MAX = 2048
    w, h = im.size
    if max(w, h) > MAX:
        scale = MAX / float(max(w, h))
        im = im.resize((max(1,int(w*scale)), max(1,int(h*scale))), Image.LANCZOS)
    out = io.BytesIO()
    im.save(out, format="PNG", optimize=True)
    return out.getvalue()
