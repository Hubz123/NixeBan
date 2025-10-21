from __future__ import annotations

import os
import logging
import discord
from discord.ext import commands

log = logging.getLogger("nixe.discord.handlers_crucial")

class NixeHandlersCrucial(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # Print the exact lines users expect
        log.info("🧩 Cogs loaded (core + autodiscover).")
        user = self.bot.user
        uid = getattr(user, "id", "?")
        # Discord.py v2 removed discriminator for new users; handle both
        tag = f"{getattr(user, 'name', 'Nixe')}#{getattr(user, 'discriminator', '8056')}" if getattr(user, 'discriminator', None) else getattr(user, 'name', 'Nixe')
        log.info("✅ Bot berhasil login sebagai %s (ID: %s)", tag if tag else user, uid)
        mode = os.getenv("NIXE_MODE", "production")
        log.info("🌐 Mode: %s", mode)

async def setup(bot: commands.Bot):
    # Avoid duplicate add
    if 'NixeHandlersCrucial' in bot.cogs:
        return
    await bot.add_cog(NixeHandlersCrucial(bot))
