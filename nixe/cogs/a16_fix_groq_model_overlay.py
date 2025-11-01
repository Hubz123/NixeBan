# nixe/cogs/a16_fix_groq_model_overlay.py
import os, logging, inspect
from discord.ext import commands
PREFERRED = "llama-3.1-8b-instant"
class FixGroqModel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        po = (os.getenv("LPA_PROVIDER_ORDER") or "").replace(" ", "")
        if po:
            os.environ["LPA_PROVIDER_ORDER"] = po
        gm = (os.getenv("GROQ_MODEL") or os.getenv("LPG_GROQ_MODEL") or "").strip()
        if (not gm) or ("scout" in gm.lower()) or (gm.lower() in {"auto","default"}):
            os.environ["GROQ_MODEL"] = PREFERRED
        logging.getLogger(__name__).info(f"[lpg-model-fix] order={os.getenv('LPA_PROVIDER_ORDER')} groq={os.getenv('GROQ_MODEL')}")
async def setup(bot):
    add = getattr(bot, "add_cog")
    res = add(FixGroqModel(bot))
    if inspect.isawaitable(res):
        await res
