from __future__ import annotations

import logging
import discord
from discord.ext import commands

log = logging.getLogger("nixe.cogs.ready_shim")

class ReadyShim(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        user = self.bot.user
        uid = getattr(user, "id", "?")
        tag = f"{getattr(user, 'name', 'Nixe')}#{getattr(user, 'discriminator', '8056')}" if getattr(user, 'discriminator', None) else getattr(user, 'name', 'Nixe')
        log.info("[ready] Bot ready as %s (%s)", tag if tag else user, uid)

async def setup(bot: commands.Bot):
    if 'ReadyShim' in bot.cogs:
        return
    await bot.add_cog(ReadyShim(bot))
