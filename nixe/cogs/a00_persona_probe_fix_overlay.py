# -*- coding: utf-8 -*-
import logging, os
from discord.ext import commands
log = logging.getLogger("nixe.cogs.a00_persona_probe_fix_overlay")
def _get(k, *alts, default=None):
    for n in (k,)+alts:
        v = os.getenv(n)
        if v: return v
    return default
class PersonaProbeFix(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    @commands.Cog.listener("on_ready")
    async def _on_ready(self):
        mode   = _get("PERSONA_MODE", "PERSONA_ACTIVE", "PERSONA", default="random")
        pool   = _get("PERSONA_POOL", default="yandere")
        name   = _get("PERSONA_DISPLAY_NAME", "PERSONA_NAME", default=f"Nixe ({mode.capitalize()} {pool})")
        log.warning("[persona-probe] Active persona: %s", name)
async def setup(bot):
    await bot.add_cog(PersonaProbeFix(bot))
