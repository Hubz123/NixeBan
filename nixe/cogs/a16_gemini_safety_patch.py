from __future__ import annotations
import asyncio, os, inspect
from typing import Any, Tuple, List
from discord.ext import commands

class GeminiSafetyPatch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Lazy import so the project structure is respected
        try:
            import nixe.helpers.gemini_bridge as gb  # type: ignore
        except Exception as e:
            # Don't crash import: keep Cog loadable; log via bot logger if available
            if getattr(bot, "logger", None):
                bot.logger.warning("[gemini-safety] import gemini_bridge failed: %r", e)
            self._gb = None
            return
        self._gb = gb
        self._orig = getattr(gb, "classify_lucky_pull", None)
        if not callable(self._orig):
            if getattr(bot, "logger", None):
                bot.logger.warning("[gemini-safety] classify_lucky_pull not found; skip patch")
            return
        # expose LAST_META
        try:
            if not hasattr(gb, "LAST_META"):
                gb.LAST_META = {}
        except Exception:
            pass
        # install patch
        async def safe_classify(*args, **kwargs):
            tout_ms = _read_int_env("LUCKYPULL_GEM_TIMEOUT_MS", 20000)
            # propagate/override timeout_ms param
            if "timeout_ms" not in kwargs or not kwargs.get("timeout_ms"):
                kwargs["timeout_ms"] = tout_ms
            try:
                res = await asyncio.wait_for(_call(self._orig, *args, **kwargs), timeout=max(1, tout_ms)//1000)
                _set_last_meta(self._gb, fallback=False)
                return _normalize(res)
            except Exception as e1:
                # Known image processing errors -> mark fallback and return neutral
                _set_last_meta(self._gb, fallback=True)
                if getattr(self.bot, "logger", None):
                    self.bot.logger.warning("[gemini-safety] classify error, fallback: %r", e1)
                # best-effort second try with shorter timeout if possible
                try:
                    res2 = await asyncio.wait_for(_call(self._orig, *args, **kwargs), timeout=3)
                    _set_last_meta(self._gb, fallback=True)
                    return _normalize(res2)
                except Exception:
                    # final neutral
                    return ("other", 0.0)

        setattr(gb, "classify_lucky_pull", safe_classify)

    def cog_unload(self):
        if self._gb and getattr(self, "_orig", None):
            try:
                setattr(self._gb, "classify_lucky_pull", self._orig)
            except Exception:
                pass

async def _call(fn, *args, **kwargs):
    res = fn(*args, **kwargs)
    if inspect.isawaitable(res):
        return await res
    return res

def _read_int_env(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except Exception:
        return default

def _set_last_meta(gb: Any, fallback: bool):
    try:
        gb.LAST_META = {"fallback": bool(fallback)}
    except Exception:
        pass

def _normalize(res: Any) -> Tuple[str, float]:
    # Accept ('label', conf) or dict-like {'label':..., 'conf':...}
    try:
        if isinstance(res, (list, tuple)) and len(res) >= 2:
            return (str(res[0]), float(res[1]))
        if isinstance(res, dict):
            return (str(res.get("label", "other")), float(res.get("conf", 0.0)))
    except Exception:
        pass
    return ("other", 0.0)

async def setup(bot):
    await bot.add_cog(GeminiSafetyPatch(bot))
