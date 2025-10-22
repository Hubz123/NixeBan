
from __future__ import annotations
import os, io, asyncio, logging

import discord
from discord.ext import commands

log = logging.getLogger("nixe.cogs.phash_relay_inbox")

INBOX_ID = int(os.getenv("PHASH_INBOX_CHANNEL_ID", "0"))
IMAGEPHISH_THREAD_ID = int(os.getenv("PHASH_IMAGEPHISH_THREAD_ID", "1409949797313679492"))  # user's imagephish thread

def _is_image(att: discord.Attachment) -> bool:
    ct = (att.content_type or "").lower()
    fn = (att.filename or "").lower()
    return ct.startswith("image/") or fn.endswith((".jpg",".jpeg",".png",".gif",".webp",".bmp",".tiff",".tif",".jfif",".pjpeg",".pjp",".avif",".heic",".heif"))

class PhashRelayInbox(commands.Cog):
    """Watch the Nixe image-phishing thread and forward new images to INBOX to trigger hashing."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._seen = set()  # process-lifetime dedupe

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        try:
            if not INBOX_ID or not IMAGEPHISH_THREAD_ID:
                return
            if message.channel.id != IMAGEPHISH_THREAD_ID:
                return
            if not message.attachments:
                return
            if message.id in self._seen:
                return
            self._seen.add(message.id)
            inbox = message.guild.get_channel(INBOX_ID) or await self.bot.fetch_channel(INBOX_ID)
            for att in message.attachments:
                if _is_image(att):
                    data = await att.read()
                    file = discord.File(io.BytesIO(data), filename=att.filename)
                    meta = f"[relay from imgphish {IMAGEPHISH_THREAD_ID} msg {message.id}] {att.url}"
                    await inbox.send(content=meta, file=file)
                    await asyncio.sleep(0.3)
        except Exception as e:
            log.warning("relay failed: %r", e)

async def setup(bot: commands.Bot):
    await bot.add_cog(PhashRelayInbox(bot))
