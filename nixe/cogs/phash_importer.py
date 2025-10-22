
from __future__ import annotations
import os, io, asyncio, logging

import discord
from discord.ext import commands

log = logging.getLogger("nixe.cogs.phash_importer")

INBOX_ID = int(os.getenv("PHASH_INBOX_CHANNEL_ID", "0"))
SOURCE_THREAD_ID = int(os.getenv("PHASH_SOURCE_THREAD_ID", os.getenv("PHASH_IMPORT_SOURCE_THREAD_ID", "1409949797313679492")))

def _is_image(att: discord.Attachment) -> bool:
    ct = (att.content_type or "").lower()
    fn = (att.filename or "").lower()
    return ct.startswith("image/") or fn.endswith((".jpg",".jpeg",".png",".gif",".webp",".bmp",".tiff",".tif",".jfif",".pjpeg",".pjp",".avif",".heic",".heif"))

class PhashImporter(commands.Cog):
    """Copy images from a source thread -> inbox channel so existing pHash watcher will index them."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="phash_import_now")
    @commands.has_permissions(administrator=True)
    async def phash_import_now(self, ctx: commands.Context, source_thread_id: int = 0):
        src_id = source_thread_id or SOURCE_THREAD_ID
        if not INBOX_ID:
            return await ctx.reply("PHASH_INBOX_CHANNEL_ID belum di-set.")
        if not src_id:
            return await ctx.reply("Berikan thread id sumber atau set PHASH_SOURCE_THREAD_ID.")

        inbox = ctx.guild.get_channel(INBOX_ID) or await self.bot.fetch_channel(INBOX_ID)
        src = await self.bot.fetch_channel(src_id)
        if not isinstance(src, discord.Thread):
            return await ctx.reply(f"{src_id} bukan thread.")

        sent = 0
        async for msg in src.history(limit=None, oldest_first=True):
            for att in msg.attachments:
                if _is_image(att):
                    try:
                        data = await att.read()
                        file = discord.File(io.BytesIO(data), filename=att.filename)
                        meta = f"[imported from thread {src_id} msg {msg.id}] {att.url}"
                        await inbox.send(content=meta, file=file)
                        sent += 1
                        await asyncio.sleep(0.4)
                    except Exception as e:
                        log.warning("skip one attachment: %r", e)
                        await asyncio.sleep(0.5)
        await ctx.reply(f"Imported {sent} images from thread {src_id} into inbox <#{INBOX_ID}>.")

async def setup(bot: commands.Bot):
    await bot.add_cog(PhashImporter(bot))
