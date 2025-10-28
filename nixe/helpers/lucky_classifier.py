from __future__ import annotations
import re
from typing import Dict, Optional

# simple conservative heuristics + optional LLM signal hook
FILE_HINT = re.compile(r"(gacha|pull|wish|warp|banner|rateup|hasil|result|roll)s?", re.I)

def classify_filename(filename: str) -> float:
    """Return confidence 0..1 from filename only (very conservative)."""
    if not filename:
        return 0.0
    return 0.7 if FILE_HINT.search(filename) else 0.0

def merge_confidences(*vals: float) -> float:
    """Conservative merge: take max of signals but cap unless multi-signal agreement."""
    vals = [v for v in vals if isinstance(v, (int, float))]
    if not vals: return 0.0
    mx = max(vals)
    # If multiple signals cross 0.6, boost a bit; else keep as-is
    agree = sum(1 for v in vals if v >= 0.6)
    if agree >= 2:
        return min(1.0, mx + 0.15)
    return mx

def classify_image_meta(*, filename: str = "", gemini_label: Optional[str] = None, gemini_conf: Optional[float] = None) -> Dict:
    """Return {'label','confidence','reason'} with NO network call here.
    - gemini_label/gemini_conf can be passed in by the caller if available.
    """
    c_file = classify_filename(filename)
    c_gem = float(gemini_conf) if (gemini_conf is not None and 0 <= float(gemini_conf) <= 1) else 0.0
    label = "lucky_pull" if (gemini_label == "lucky_pull" or c_file >= 0.7) else "other"
    conf = merge_confidences(c_file, c_gem)
    reason = []
    if c_file >= 0.7: reason.append("filename_hint")
    if gemini_label == "lucky_pull": reason.append("gemini_label")
    if c_gem > 0: reason.append(f"gemini_conf={c_gem:.2f}")
    return {"label": label, "confidence": conf, "reason": ",".join(reason) or "none"}
