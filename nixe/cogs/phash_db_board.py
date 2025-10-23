from __future__ import annotations

import logging
from typing import Optional, Set

import discord
from discord.ext import commands

from nixe.config_phash import (
    PHASH_DB_THREAD_ID as DB_THREAD_ID,
    PHASH_DB_MESSAGE_ID as DB_MESSAGE_ID,
    PHASH_DB_STRICT_EDIT as STRICT_EDIT,
)
from nixe.helpers.phash_board import (
    looks_like_phash_db,
    get_pinned_db_message,
    edit_pinned_db,
)

log = logging.getLogger("nixe.cogs.phash_db_board")

class PhashDbBoardCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._msg: Optional[discord.Message] = None

    @commands.Cog.listener()
    async def on_ready(self):
        if DB_THREAD_ID == 0:
            log.warning("DB thread id kosong; lewati deteksi.")
            return
        msg = await get_pinned_db_message(self.bot)
        if msg and looks_like_phash_db(getattr(msg, "content", "")):
            self._msg = msg
            log.info("pHash board ditemukan (msg_id=%s)", msg.id)
        else:
            if STRICT_EDIT:
                log.warning("STRICT_EDIT aktif dan board belum ditemukan -> tidak membuat pesan baru.")

    async def update_board(self, tokens: Set[str]) -> bool:
        return await edit_pinned_db(self.bot, set(tokens))

async def setup(bot: commands.Bot):
    await bot.add_cog(PhashDbBoardCog(bot))

def setup_legacy(bot: commands.Bot):
    bot.add_cog(PhashDbBoardCog(bot))
