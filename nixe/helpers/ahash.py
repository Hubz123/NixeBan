from __future__ import annotations
from io import BytesIO
from PIL import Image
import numpy as np
def average_hash_bytes(b: bytes, size: int = 8) -> str:
    im = Image.open(BytesIO(b)).convert("L").resize((size,size), Image.BILINEAR)
    arr = np.asarray(im, dtype=np.float32)
    avg = float(arr.mean()); bits=(arr>=avg).astype(np.uint8).flatten()
    v=0; out=[]
    for i,bit in enumerate(bits):
        v=(v<<1)|int(bit)
        if i%4==3:
            out.append(format(v,'x')); v=0
    if len(bits)%4!=0: out.append(format(v,'x'))
    return ''.join(out)
