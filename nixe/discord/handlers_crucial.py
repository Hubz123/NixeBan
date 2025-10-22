
from __future__ import annotations
import os, logging, discord
from discord.ext import commands
from nixe.helpers.bootstate import wait_cogs_loaded

log = logging.getLogger("nixe.discord.handlers_crucial")

def _user_tag(u: discord.ClientUser | discord.User | None) -> str:
    if not u: return "Nixe#0000"
    discr = getattr(u, "discriminator", None)
    if discr and discr != "0": return f"{getattr(u, 'name', 'Nixe')}#{discr}"
    return getattr(u, "name", "Nixe")

class NixeHandlersCrucial(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._printed = False

    @commands.Cog.listener()
    async def on_ready(self):
        if self._printed: return
        await wait_cogs_loaded(5.0)
        self._printed = True
        log.info("🧩 Cogs loaded (core + autodiscover).")
        u = self.bot.user
        log.info("✅ Bot berhasil login sebagai %s (ID: %s)", _user_tag(u), getattr(u, "id", "?"))
        mode = os.getenv("NIXE_MODE", os.getenv("MODE", "production"))
        log.info("🌐 Mode: %s", mode)

async def setup(bot: commands.Bot):
    if 'NixeHandlersCrucial' in bot.cogs: return
    await bot.add_cog(NixeHandlersCrucial(bot))
