from __future__ import annotations
import logging, discord
from discord import app_commands
from discord.ext import commands
log = logging.getLogger(__name__)
class PhashAdmin(commands.Cog):
    group = app_commands.Group(name="phash", description="pHash admin tools")
    def __init__(self, bot: commands.Bot): self.bot=bot
    @group.command(name="ping", description="Check that pHash admin is online.")
    async def ping(self, interaction: discord.Interaction):
        await interaction.response.send_message("pHash admin OK", ephemeral=True)
async def setup(bot: commands.Bot):
    await bot.add_cog(PhashAdmin(bot))
    try:
        if not any(c.name=="phash" for c in bot.tree.get_commands()):
            bot.tree.add_command(PhashAdmin.group)
    except Exception: log.debug("[phash_admin] group registration skipped", exc_info=True)
