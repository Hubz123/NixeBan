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

async def _adopt_pinned_if_missing(bot, thread_id: int):
    """Try to adopt an existing pinned message in the DB thread when STRICT_EDIT is on."""
    try:
        chan = bot.get_channel(thread_id) or await bot.fetch_channel(thread_id)
    except Exception as e:
        log.warning("phash-db: cannot resolve thread %s: %r", thread_id, e)
        return None
    try:
        pins = await chan.pins()
    except Exception as e:
        log.warning("phash-db: cannot read pins on %s: %r", thread_id, e)
        return None
    cand = None
    for m in pins:
        try:
            if m.author and bot.user and m.author.id == bot.user.id:
                cand = m; break
        except Exception:
            pass
    if cand is None and pins:
        cand = pins[0]
    if cand:
        log.warning("STRICT_EDIT aktif: mengadopsi pinned msg_id=%s", getattr(cand, "id", "<unknown>"))
        return cand
    return None

from nixe.state_runtime import set_phash_ids, get_phash_ids
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
                adopted = await _adopt_pinned_if_missing(self.bot, DB_THREAD_ID)
                if adopted:
                    self._msg = adopted
                    log.info("pHash board diikat ke pinned msg (msg_id=%s)", adopted.id)
                try:
                    set_phash_ids(DB_THREAD_ID, int(adopted.id))
                except Exception as _e:
                    log.warning("phash-db: failed to publish runtime ids: %r", _e)
                    # Propagate adopted IDs to config + env so other cogs see them immediately
                    try:
                        import os as _os
                        import nixe.config_phash as _cfg
                        _cfg.PHASH_DB_MESSAGE_ID = int(getattr(adopted, "id", 0) or 0)
                        if DB_THREAD_ID:
                            _cfg.PHASH_DB_THREAD_ID = int(DB_THREAD_ID)
                        # Also reflect to env for cogs that read os.environ
                        if getattr(adopted, "id", None):
                            _os.environ["PHASH_DB_MESSAGE_ID"] = str(adopted.id)
                        if DB_THREAD_ID:
                            _os.environ["PHASH_DB_THREAD_ID"] = str(DB_THREAD_ID)
                            _os.environ["NIXE_PHASH_DB_THREAD_ID"] = str(DB_THREAD_ID)
                    except Exception as _e:
                        log.warning("phash-db: failed to propagate adopted IDs: %r", _e)

                else:
                    log.warning("STRICT_EDIT aktif: tidak ada pin yang bisa diadopsi; tetap skip.")

    async def update_board(self, tokens: Set[str]) -> bool:
        return await edit_pinned_db(self.bot, set(tokens))

async def setup(bot: commands.Bot):
    await bot.add_cog(PhashDbBoardCog(bot))

def setup_legacy(bot: commands.Bot):
    bot.add_cog(PhashDbBoardCog(bot))
