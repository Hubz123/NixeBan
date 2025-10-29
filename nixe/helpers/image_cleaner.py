from __future__ import annotations
from io import BytesIO
from PIL import Image
def clean_for_gemini_bytes(raw: bytes, max_side: int = 1600) -> bytes:
    try:
        im=Image.open(BytesIO(raw)).convert("RGB")
        w,h=im.size; m=max(w,h)
        if m>max_side:
            s=max_side/float(m); im=im.resize((int(w*s), int(h*s)), Image.BILINEAR)
        buf=BytesIO(); im.save(buf,"JPEG",quality=90, optimize=True); return buf.getvalue()
    except Exception: return raw
