from __future__ import annotations
from io import BytesIO
from typing import Tuple, Dict
from PIL import Image
import numpy as np

def _to_hsv_np(img: Image.Image) -> np.ndarray:
    if img.mode not in ("RGB","RGBA"):
        img = img.convert("RGB")
    if img.mode == "RGBA":
        img = img.convert("RGB")
    hsv = np.array(img.convert("HSV"), dtype=np.uint8)
    return hsv

def _grayscale_v(hsv: np.ndarray) -> np.ndarray:
    return hsv[:,:,2].astype(np.float32) / 255.0

def _count_vertical_edges(vmat: np.ndarray) -> Tuple[int,float]:
    # simple vertical gradient (x-derivative)
    gx = np.abs(np.diff(vmat, axis=1))
    # smooth a bit
    k = 7
    if gx.shape[1] > k:
        kernel = np.ones((1,k), dtype=np.float32) / float(k)
        gx = np.convolve(gx.mean(axis=0), kernel.ravel(), mode="same")
    else:
        gx = gx.mean(axis=0)
    # threshold by percentile
    thr = float(np.percentile(gx, 92))
    peaks = np.where(gx >= thr)[0]
    if peaks.size == 0:
        return 0, 1.0
    # group close peaks into columns
    groups = []
    cur = [int(peaks[0])]
    for p in peaks[1:]:
        if p - cur[-1] <= 10:  # within 10px considered same column
            cur.append(int(p))
        else:
            groups.append(cur)
            cur = [int(p)]
    groups.append(cur)
    centers = [int(np.mean(g)) for g in groups]
    if len(centers) < 2:
        return len(centers), 1.0
    d = np.diff(sorted(centers))
    reg = float(np.std(d) / max(np.mean(d), 1e-5))
    return len(centers), reg

def _ratio_hsv(hsv: np.ndarray, h_lo: float, h_hi: float, s_lo: float=0.4, v_lo: float=0.4) -> float:
    H,S,V = hsv[:,:,0]/255.0, hsv[:,:,1]/255.0, hsv[:,:,2]/255.0
    deg = H*360.0
    if h_lo <= h_hi:
        hmask = (deg>=h_lo) & (deg<=h_hi)
    else:
        hmask = (deg>=h_lo) | (deg<=h_hi)
    m = hmask & (S>=s_lo) & (V>=v_lo)
    return float(m.mean())

def _ratio_in_border(hsv: np.ndarray, h_lo: float, h_hi: float, border_frac: float=0.12, s_lo: float=0.4, v_lo: float=0.4) -> float:
    H,S,V = hsv[:,:,0]/255.0, hsv[:,:,1]/255.0, hsv[:,:,2]/255.0
    Hdeg = H*360.0
    hmask = (Hdeg>=h_lo)&(Hdeg<=h_hi) if h_lo<=h_hi else ((Hdeg>=h_lo)|(Hdeg<=h_hi))
    m = hmask & (S>=s_lo) & (V>=v_lo)
    h, w = V.shape
    b = int(max(1, w*border_frac))
    # left & right border areas
    border = np.zeros_like(V, dtype=bool)
    border[:, :b] = True
    border[:, -b:] = True
    return float((m & border).mean())

def analyze_layout_signature(image_bytes: bytes, max_px: int=1536) -> Dict[str, float]:
    img = Image.open(BytesIO(image_bytes))
    w, h = img.size
    if max(w,h) > max_px:
        scale = max_px / float(max(w,h))
        img = img.resize((int(w*scale), int(h*scale)), Image.BILINEAR)
    hsv = _to_hsv_np(img)
    v = _grayscale_v(hsv)
    ncols, reg = _count_vertical_edges(v)
    gold = _ratio_hsv(hsv, 25, 55, 0.35, 0.45)     # golden flame/bursts
    purple = _ratio_hsv(hsv, 260, 320, 0.30, 0.35) # magenta/purple UIs
    cyan_border = _ratio_in_border(hsv, 185, 205, 0.12, 0.35, 0.45)  # bluish borders on left/right
    blue = _ratio_hsv(hsv, 200, 240, 0.25, 0.35)   # deep blue rails
    bright = float((hsv[:,:,2] >= int(0.70*255)).mean())
    return {
        "ncols": float(ncols),
        "reg": round(reg,4),
        "gold": round(gold,4),
        "purple": round(purple,4),
        "cyan_border": round(cyan_border,4),
        "blue": round(blue,4),
        "bright": round(bright,4),
        "w": float(w),
        "h": float(h),
    }

def is_lucky_pull_layoutlike(image_bytes: bytes) -> Tuple[bool, Dict[str,float]]:
    m = analyze_layout_signature(image_bytes)
    ncols = m["ncols"]; reg = m["reg"]
    # Rules tuned for mixed styles:
    r1 = (ncols >= 7 and reg <= 0.42)                       # many evenly spaced vertical panels
    r2 = (m["gold"] >= 0.06 and ncols >= 4)                 # strong gold bar + multi-panels
    r3 = (m["cyan_border"] >= 0.03 and ncols >= 4)          # cyan/blue borders + multi-panels
    r4 = (m["purple"] >= 0.05 and m["bright"] >= 0.33)      # purple & bright
    r5 = (m["blue"] >= 0.06 and ncols >= 6)                 # deep blue rail + many panels
    ok = bool(r1 or r2 or r3 or r4 or r5)
    m["rule_hits"] = int(r1) + int(r2) + int(r3) + int(r4) + int(r5)
    return ok, m
