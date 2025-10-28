
from __future__ import annotations
from PIL import Image
import io
def dhash_bytes(image_bytes: bytes) -> int:
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("L").resize((9,8), Image.LANCZOS)
    except Exception:
        return 0
    bits = 0
    for y in range(8):
        for x in range(8):
            a = img.getpixel((x, y)); b = img.getpixel((x+1, y))
            bits = (bits << 1) | (1 if a > b else 0)
    return bits
def hamming(a: int, b: int) -> int:
    return ((a ^ b) & ((1<<64)-1)).bit_count()
