# tools/hash_whitelist_helper.py
# Usage:
#   python tools/hash_whitelist_helper.py path/to/image.png
# Prints ahash, dhash and sha256 for the image.
import sys, hashlib, io
from PIL import Image
import numpy as np

def ahash_hex_from_bytes(b: bytes, size: int = 8) -> str:
    im = Image.open(io.BytesIO(b)).convert("L").resize((size, size))
    arr = np.asarray(im, dtype=np.float32)
    avg = float(arr.mean())
    bits = (arr >= avg).astype(np.uint8).flatten()
    v = 0; out = []
    for i, bit in enumerate(bits):
        v = (v << 1) | int(bit)
        if i % 4 == 3:
            out.append(format(v, "x")); v = 0
    if len(bits) % 4 != 0:
        out.append(format(v, "x"))
    return "".join(out)

def dhash_hex_from_bytes(b: bytes) -> str:
    im = Image.open(io.BytesIO(b)).convert("L").resize((9, 8))
    px = list(im.getdata())
    w, h = im.size
    bits = []
    for y in range(h):
        row = [px[y * w + x] for x in range(w)]
        for x in range(w - 1):
            bits.append(1 if row[x] < row[x + 1] else 0)
    v = 0; out = []
    for i, bit in enumerate(bits):
        v = (v << 1) | int(bit)
        if i % 4 == 3:
            out.append(format(v, "x")); v = 0
    if len(bits) % 4 != 0:
        out.append(format(v, "x"))
    return "".join(out)

def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/hash_whitelist_helper.py <image>")
        sys.exit(1)
    p = sys.argv[1]
    b = open(p, "rb").read()
    print("ahash:", ahash_hex_from_bytes(b, 8))
    print("dhash:", dhash_hex_from_bytes(b))
    print("sha256:", hashlib.sha256(b).hexdigest())

if __name__ == "__main__":
    main()
