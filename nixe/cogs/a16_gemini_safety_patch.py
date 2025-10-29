
from __future__ import annotations
import inspect
from typing import Any, Tuple
from discord.ext import commands

FALLBACK_MESSAGE = "Unable to process input image"

def _log(bot, level: str, msg: str):
    try:
        getattr(bot.logger, level)(msg)
    except Exception:
        print(f"[gemini-safety:{level}] {msg}")

def _normalize_result(res: Any) -> Tuple[str, float]:
    # Accept (label, conf) tuple or dict-like
    if isinstance(res, tuple) and len(res) == 2:
        return res[0], float(res[1])
    if isinstance(res, dict):
        label = res.get("label") or res.get("prediction") or res.get("class") or "other"
        conf = res.get("conf") or res.get("confidence") or res.get("score") or 0.0
        try:
            conf = float(conf)
        except Exception:
            conf = 0.0
        return str(label), conf
    # Fallback
    return "other", 0.0

async def _call_maybe_async(fn, *args, **kwargs):
    res = fn(*args, **kwargs)
    if inspect.isawaitable(res):
        res = await res
    return res

class GeminiSafetyPatch(commands.Cog):
    """Patch gemini_bridge.classify_lucky_pull to be robust against
    image processing errors and mixed async/sync implementations."""
    def __init__(self, bot):
        self.bot = bot
        self._apply_patch()

    def _apply_patch(self):
        try:
            import nixe.helpers.gemini_bridge as gb
        except Exception as e:
            _log(self.bot, "warning", f"gemini_bridge not found: {e!r}")
            return

        orig = getattr(gb, "classify_lucky_pull", None)
        if not callable(orig):
            _log(self.bot, "warning", "classify_lucky_pull not callable or missing")
            return

        async def safe_classify(*args, **kwargs):
            try:
                res = await _call_maybe_async(orig, *args, **kwargs)
                return _normalize_result(res)
            except Exception as e:
                msg = str(e)
                if FALLBACK_MESSAGE in msg:
                    # Retry without image inputs, force text only
                    kw = dict(kwargs)
                    for k in ("attachments", "images", "image", "file", "files"):
                        if k in kw:
                            kw[k] = None
                    kw["force_text_only"] = True
                    try:
                        res2 = await _call_maybe_async(orig, *args, **kw)
                        _log(self.bot, "warning", "[gemini-safety] image failed; fallback text-only succeeded")
                        return _normalize_result(res2)
                    except Exception as e2:
                        _log(self.bot, "warning", f"[gemini-safety] fallback also failed: {e2!r}")
                        raise
                raise

        setattr(gb, "classify_lucky_pull", safe_classify)
        _log(self.bot, "info", "classify_lucky_pull patched for image-fallback and async-safe")

async def setup(bot):
    await bot.add_cog(GeminiSafetyPatch(bot))
