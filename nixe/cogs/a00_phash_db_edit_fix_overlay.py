
import os
import asyncio
import logging
import discord
from discord.ext import commands
from nixe.helpers.phash_board import discover_db_message_id

log = logging.getLogger(__name__)

PHASH_DB_MARKER = os.getenv("PHASH_DB_MARKER", "NIXE_PHASH_DB_V1").strip()
STRICT = bool(int(os.getenv("PHASH_DB_STRICT_EDIT", "1")))
DB_MSG_ID = int(os.getenv("PHASH_DB_MESSAGE_ID", "0") or 0)
LOG_CH_ID = int(os.getenv("LOG_CHANNEL_ID", "0") or 0)
DB_THREAD_ID = int(os.getenv("NIXE_PHASH_DB_THREAD_ID", "0") or 0)

class PhashDbEditFixOverlay(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._task = self.bot.loop.create_task(self._run())

    def cog_unload(self):
        try:
            self._task.cancel()
        except Exception:
            pass

    async def _try_fetch(self) -> discord.Message | None:
        if DB_MSG_ID <= 0:
            return None
        # 1) Try thread first (common case)
        if DB_THREAD_ID:
            try:
                th = self.bot.get_channel(DB_THREAD_ID) or await self.bot.fetch_channel(DB_THREAD_ID)
                if isinstance(th, (discord.Thread, discord.TextChannel)):
                    return await th.fetch_message(DB_MSG_ID)
            except Exception:
                pass
        # 2) Fallback: main log channel
        if LOG_CH_ID:
            try:
                ch = self.bot.get_channel(LOG_CH_ID) or await self.bot.fetch_channel(LOG_CH_ID)
                if isinstance(ch, (discord.Thread, discord.TextChannel)):
                    return await ch.fetch_message(DB_MSG_ID)
            except Exception:
                pass
        # 3) Last resort: scan recent messages in log channel for marker
        if LOG_CH_ID:
            try:
                ch = self.bot.get_channel(LOG_CH_ID) or await self.bot.fetch_channel(LOG_CH_ID)
                async for m in ch.history(limit=50):
                    if m.author.id == self.bot.user.id and PHASH_DB_MARKER in (m.content or ""):
                        return m
            except Exception:
                pass
        return None

    async def _run(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(2)
        msg = await self._try_fetch()
        if not msg:
            try:
                did = await discover_db_message_id(self.bot)
                if did:
                    try:
                        ch = self.bot.get_channel(DB_THREAD_ID) or await self.bot.fetch_channel(DB_THREAD_ID)
                        msg = await ch.fetch_message(did)
                    except Exception:
                        msg = None
            except Exception:
                msg = None
        if not msg:
            if STRICT:
                log.warning("[phash-db-edit-fix] strict edit only; DB message not found in thread/log channel; skipping.")
            else:
                log.info("[phash-db-edit-fix] non-strict; DB message not found; skipping.")
            return
        log.info("[phash-db-edit-fix] DB message located (id=%s) — OK", msg.id)

async def setup(bot: commands.Bot):
    await bot.add_cog(PhashDbEditFixOverlay(bot))
def legacy_setup(bot: commands.Bot):
    bot.add_cog(PhashDbEditFixOverlay(bot))
