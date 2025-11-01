# nixe/helpers/lpa_provider_bridge.py
"""
Lightweight provider bridge for Lucky Pull classification.

This module tries (in order) the providers specified by env LPA_PROVIDER_ORDER (e.g. "groq,gemini").
It looks for optional modules you may already have:
 - nixe.helpers.lpg_provider          -> expected function: classify_lucky_pull(text) -> (score[0..1], reason)
 - nixe.helpers.gemini_bridge         -> expected function: classify_lucky_pull(text) -> (score, reason)
 - nixe.helpers.groq_bridge           -> expected function: classify_lucky_pull(text) -> (score, reason)

If a provider module isn't present, it's skipped.
This module NEVER raises; it returns (None, "provider_unavailable") on failure.
"""
import os, time

def _getenv(k, d=""):
    return os.getenv(k, d)

def _try_import(path):
    try:
        mod = __import__(path, fromlist=["*"])
        return mod
    except Exception as e:
        return None

def _call(mod, text, timeout_ms):
    try:
        fn = getattr(mod, "classify_lucky_pull", None)
        if not callable(fn):
            return None, "no_fn"
        # naive timeout guard by start timestamp (actual network timeouts must be inside module)
        start = time.time()
        res = fn(text)
        if timeout_ms:
            elapsed = (time.time() - start) * 1000.0
            if elapsed > timeout_ms:
                return None, "timeout_soft"
        return res
    except Exception as e:
        return None, f"err:{type(e).__name__}"

def classify(text: str, provider_order: str = ""):
    order = [p.strip() for p in (provider_order or _getenv("LPA_PROVIDER_ORDER","groq,gemini")).split(",") if p.strip()]
    timeout_ms = int(_getenv("LPA_PROVIDER_TIMEOUT_MS", "9000") or 9000)

    modules = []
    for p in order:
        if p.lower() == "groq":
            m = _try_import("nixe.helpers.groq_bridge") or _try_import("nixe.helpers.lpg_provider")
        elif p.lower() == "gemini":
            m = _try_import("nixe.helpers.gemini_bridge") or _try_import("nixe.helpers.lpg_provider")
        else:
            m = _try_import(p)  # allow custom paths
        if m:
            modules.append((p.lower(), m))

    if not modules:
        return None, "provider_unavailable"

    last_reason = "provider_unavailable"
    for name, mod in modules:
        score_reason = _call(mod, text, timeout_ms)
        if not isinstance(score_reason, tuple) or len(score_reason) != 2:
            last_reason = "bad_tuple"
            continue
        score, reason = score_reason
        if isinstance(score, (int, float)):
            return float(score), f"{name}:{reason}"
        last_reason = f"{name}:{reason}"
    return None, last_reason
