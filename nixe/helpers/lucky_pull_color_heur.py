from __future__ import annotations
from io import BytesIO
from typing import Tuple
from PIL import Image
import numpy as np

def _to_hsv(img: Image.Image) -> np.ndarray:
    if img.mode not in ("RGB","RGBA"):
        img = img.convert("RGB")
    if img.mode == "RGBA":
        # remove transparent areas from stats
        a = np.array(img.split()[-1], dtype=np.uint8)
        img = img.convert("RGB")
    hsv = np.array(img.convert("HSV"), dtype=np.uint8)  # H:0-255 ~ 0-360deg
    return hsv

def _ratio_mask(hsv: np.ndarray, h_lo: float, h_hi: float, s_lo: float=0.4, v_lo: float=0.4) -> float:
    H,S,V = hsv[:,:,0]/255.0, hsv[:,:,1]/255.0, hsv[:,:,2]/255.0
    # Convert normalized hue [0..1] to degrees
    deg = H*360.0
    # handle wrap-around if needed
    if h_lo <= h_hi:
        hmask = (deg>=h_lo) & (deg<=h_hi)
    else:
        hmask = (deg>=h_lo) | (deg<=h_hi)
    smask = (S>=s_lo)
    vmask = (V>=v_lo)
    m = hmask & smask & vmask
    return float(m.mean())

def analyze_color_signature(image_bytes: bytes, downscale_px: int=768) -> Tuple[float,float,float]:
    """Return (purple_ratio, yellow_ratio, bright_ratio) approx signatures.
    - purple ~ 260..300 deg
    - yellow ~ 45..65 deg
    - bright ~ V>=0.7
    """
    img = Image.open(BytesIO(image_bytes))
    # speed up
    w,h = img.size
    if max(w,h) > downscale_px:
        scale = downscale_px / float(max(w,h))
        img = img.resize((int(w*scale), int(h*scale)), Image.BILINEAR)
    hsv = _to_hsv(img)
    purple = _ratio_mask(hsv, 260, 300, 0.35, 0.35)
    yellow = _ratio_mask(hsv, 45, 65, 0.35, 0.35)
    V = hsv[:,:,2]/255.0
    bright = float((V>=0.70).mean())
    return purple, yellow, bright

def is_lucky_pull_colorlike(image_bytes: bytes) -> Tuple[bool, dict]:
    p,y,b = analyze_color_signature(image_bytes)
    # Heuristic tuned: gacha UI sering ungu/magenta dominan + highlight kuning bintang/SSR
    ok = (p >= 0.06 and y >= 0.02 and b >= 0.35)
    return ok, {"purple": round(p,4), "yellow": round(y,4), "bright": round(b,4)}
