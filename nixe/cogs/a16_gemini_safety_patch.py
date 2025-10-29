# nixe/cogs/a16_gemini_safety_patch.py
# Patch Gemini calls to be async-safe, use image cleaning, and avoid warning spam on timeouts.
from __future__ import annotations
import asyncio, inspect, os, types

try:
    from nixe.helpers.image_cleaner import clean_for_gemini_bytes
except Exception:
    clean_for_gemini_bytes = None

def _with_timeout_and_clean(fn, *, timeout_ms: int):
    async def _wrap(*args, **kwargs):
        # Clean image-like payloads in *args/**kwargs
        def _clean_obj(x):
            if clean_for_gemini_bytes and isinstance(x, (bytes, bytearray)):
                try:
                    return clean_for_gemini_bytes(x)
                except Exception:
                    return x
            if isinstance(x, (list, tuple)):
                return type(x)(_clean_obj(xx) for xx in x)
            if isinstance(x, dict):
                return {k: _clean_obj(v) for k, v in x.items()}
            return x

        cargs = _clean_obj(list(args))
        ckwargs = _clean_obj(dict(kwargs))
        try:
            return await asyncio.wait_for(fn(*cargs, **ckwargs), timeout=timeout_ms/1000.0)
        except Exception:
            # On any error/timeout, return neutral result rather than warning-spam
            # Lucky-pull style: ("other", 0.0)
            # Phish style: {"label":"other","conf":0.0}
            return ("other", 0.0)
    return _wrap

async def setup(bot):
    # LUCKY PULL bridge
    try:
        import nixe.helpers.gemini_bridge as gbridge  # classify_lucky_pull([...], ...)
        tout_ms = int(os.getenv("LUCKYPULL_GEM_TIMEOUT_MS", "20000"))
        if hasattr(gbridge, "classify_lucky_pull") and asyncio.iscoroutinefunction(gbridge.classify_lucky_pull):
            gbridge.classify_lucky_pull = _with_timeout_and_clean(gbridge.classify_lucky_pull, timeout_ms=tout_ms)
    except Exception:
        pass

    # PHISH bridge — wrap any coroutine with "classify" & "phish" in its name
    try:
        import nixe.helpers.gemini_phish as gphish
        ptout_ms = int(os.getenv("PHISH_GEMINI_MAX_LATENCY_MS", "12000"))
        for name in dir(gphish):
            if "classify" in name and "phish" in name:
                fn = getattr(gphish, name, None)
                if asyncio.iscoroutinefunction(fn):
                    setattr(gphish, name, _with_timeout_and_clean(fn, timeout_ms=ptout_ms))
    except Exception:
        pass
