from __future__ import annotations
from typing import Iterable, Tuple
try:
    from nixe.helpers.lp_gemini_helper import is_lucky_pull, is_gemini_enabled
except Exception:
    def is_lucky_pull(image_bytes: bytes, threshold: float = 0.65):
        return (False, 0.0, "helper_missing")
    def is_gemini_enabled() -> bool:
        return False

DEFAULT_GEMINI_MODEL = "gemini-1.5-flash"
GEMINI_MIN_CONF = 0.65

def gemini_judge_images(images: Iterable[bytes], min_conf: float = GEMINI_MIN_CONF) -> Tuple[bool, float]:
    if not is_gemini_enabled():
        return (False, 0.0)
    decided = False
    max_score = 0.0
    for b in images or []:
        dec, score, _ = is_lucky_pull(b, threshold=min_conf)
        decided = decided or bool(dec)
        max_score = max(max_score, float(score))
    return (decided, max_score)

# Make this module a valid Cog for smoke discovery
from discord.ext import commands

class LP_Gemini_Helper_Cog(commands.Cog):
    """No-op Cog to satisfy smoke validation; provides no runtime listeners."""
    def __init__(self, bot):
        self.bot = bot

async def setup(bot):
    try:
        await bot.add_cog(LP_Gemini_Helper_Cog(bot))
    except Exception:
        # In case running in stub/no-discord env
        pass
