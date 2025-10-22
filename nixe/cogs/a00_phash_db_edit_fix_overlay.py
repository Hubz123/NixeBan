import os
from typing import Optional
import asyncio
from discord.ext import commands

class PhashDbEditFixOverlay(commands.Cog):
    """Overlay to prevent creating new pHash DB messages.
    Forces editing an existing pinned message if IDs are provided.
    """
    def __init__(self, bot):
        self.bot = bot
        self.strict = os.environ.get("PHASH_DB_STRICT_EDIT", "1") == "1"
        self.thread_id = int(os.environ.get("PHASH_DB_THREAD_ID", "0")) or int(os.environ.get("PHASH_IMAGEPHISH_THREAD_ID", "0")) if os.environ.get("PHASH_IMAGEPHISH_THREAD_ID") else 0
        self.msg_id = int(os.environ.get("PHASH_DB_MESSAGE_ID", "0"))
        self._ready_once = False

    @commands.Cog.listener()
    async def on_ready(self):
        if self._ready_once:
            return
        self._ready_once = True

        if self.strict and (self.thread_id == 0 or self.msg_id == 0):
            # Strict mode without IDs: do nothing (never create new message)
            return

        try:
            channel = self.bot.get_channel(self.thread_id) or await self.bot.fetch_channel(self.thread_id)
            msg = await channel.fetch_message(self.msg_id)
            # Attach a marker attribute for other cogs to find and reuse
            setattr(self.bot, "_phash_db_edit_message", msg)
        except Exception as e:
            # If strict, never create new
            if self.strict:
                # Log but do nothing; prevents accidental new posts.
                print(f"[phash-db-edit-fix] strict edit only; could not fetch existing message: {e}")
            else:
                print(f"[phash-db-edit-fix] non-strict; existing message not found: {e}")

async def setup(bot):
    await bot.add_cog(PhashDbEditFixOverlay(bot))
