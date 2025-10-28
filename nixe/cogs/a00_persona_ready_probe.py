from __future__ import annotations
import logging
from discord.ext import commands
from nixe.helpers.persona_boot import persona_version

log = logging.getLogger(__name__)

class PersonaReadyProbe(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_ready")
    async def _on_ready(self):
        log.warning("[persona-probe] Active persona: %s", persona_version())

async def setup(bot: commands.Bot):
    await bot.add_cog(PersonaReadyProbe(bot))
