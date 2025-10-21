# -*- coding: utf-8 -*-
# Compatibility wrapper: alias to NixePhashInboxWatcher (safe, no duplicate loops)
from __future__ import annotations
from discord.ext import commands
from .phash_inbox_watcher import NixePhashInboxWatcher

async def setup(bot: commands.Bot):
    await bot.add_cog(NixePhashInboxWatcher(bot))
