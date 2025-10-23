from __future__ import annotations
# Backward-compat shim: if this file still exists alongside ban_commands, skip adding duplicate command.
import logging
from discord.ext import commands

class _SkipTB(commands.Cog): pass

async def setup(bot: commands.Bot):
    if bot.get_command("tb") or bot.get_command("testban"):
        logging.getLogger("nixe.cogs_loader").info("skip a01_leina_tb: 'tb' already provided by ban_commands")
        return
    # no command exists; we don't add anything here to avoid duplication.
    await bot.add_cog(_SkipTB(bot))
def setup_legacy(bot: commands.Bot):
    if bot.get_command("tb") or bot.get_command("testban"):
        return
    bot.add_cog(_SkipTB(bot))
