
# Ensure pHash-DB thread exists under log channel and pin board message
import asyncio, logging, os
from discord.ext import commands
import discord
from nixe import config
log = logging.getLogger(__name__)
NO_FALLBACK = (os.getenv('NIXE_PHASH_DISABLE_LOG_FALLBACK','1') == '1')

class PhashDbThreadManager(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._ran = False

    @commands.Cog.listener()
    async def on_ready(self):
        if self._ran: return
        self._ran = True
        try:
            await self.ensure_thread_and_board()
        except Exception as e:
            log.exception("phash-db ensure failed: %s", e)

    async def ensure_thread_and_board(self):
        chan_id = (getattr(config, 'PHISH_LOG_CHAN_ID', None) or
                   getattr(config, 'LOG_CHANNEL_ID', None))
        if not chan_id:
            for k in ('NIXE_PHISH_LOG_CHAN_ID','LOG_CHANNEL_ID'):
                v = os.getenv(k, '')
                if v.isdigit():
                    chan_id = int(v); break
        log.info("[phash-db-manager] resolved chan=%r (cfg.PHISH_LOG_CHAN_ID=%r cfg.LOG_CHANNEL_ID=%r env.NIXE_PHISH_LOG_CHAN_ID=%r env.LOG_CHANNEL_ID=%r)",
                 chan_id, getattr(config,'PHISH_LOG_CHAN_ID',None), getattr(config,'LOG_CHANNEL_ID',None),
                 os.getenv('NIXE_PHISH_LOG_CHAN_ID'), os.getenv('LOG_CHANNEL_ID'))
        if not chan_id:
            log.warning("PHISH_LOG_CHAN_ID/LOG_CHANNEL_ID not set; skip phash-db ensure"); return

        chan = self.bot.get_channel(chan_id) or await self.bot.fetch_channel(chan_id)
        if not isinstance(chan, (discord.TextChannel, discord.ForumChannel)):
            log.warning("Channel %s is not Text/Forum", chan_id); return

        thread_name = getattr(config, 'PHASH_DB_THREAD_NAME', None) or os.getenv('NIXE_PHASH_DB_THREAD_NAME','phash-db')
        thread_id = (getattr(config, 'PHASH_DB_THREAD_ID', None) or
                     (int(os.getenv('NIXE_PHASH_DB_THREAD_ID')) if (os.getenv('NIXE_PHASH_DB_THREAD_ID') or '').isdigit() else None))
        thread = None
        if thread_id:
            thread = self.bot.get_channel(thread_id) or await self.bot.fetch_channel(thread_id)

        if thread is None and getattr(chan, "threads", None):
            for t in chan.threads:
                if (t.name or "").lower() == (thread_name or "phash-db").lower():
                    thread = t; break

        if thread is None and isinstance(chan, discord.TextChannel):
            try:
                async for t in chan.archived_threads(limit=50):
                    if (t.name or "").lower() == (thread_name or "phash-db").lower():
                        thread = t; break
            except Exception: pass

        if thread is None:
            thread = await chan.create_thread(
                name=thread_name or "phash-db",
                type=discord.ChannelType.public_thread,
                auto_archive_duration=10080
            )
            log.info("Created pHash-DB thread id=%s under chan=%s", thread.id, chan.id)

        try:
            self.bot.phash_db_thread_id = thread.id
            import nixe.config as _cfg
            _cfg.PHASH_DB_THREAD_ID = thread.id
        except Exception: pass

        try:
            pins = await thread.pins()
        except Exception:
            pins = []
        has_board = False
        for m in pins:
            if m.author.id == self.bot.user.id and any((e.title or '').lower().startswith('phash db board') for e in m.embeds):
                has_board = True; break
        if not has_board:
            src_id = (getattr(config,'PHASH_SOURCE_THREAD_ID', None) or
                      (int(os.getenv('NIXE_PHASH_SOURCE_THREAD_ID')) if (os.getenv('NIXE_PHASH_SOURCE_THREAD_ID') or '').isdigit() else None) or
                      getattr(config,'PHASH_IMAGEPHISH_THREAD_ID', None))
            desc = ["Thread ini menyimpan **pHash DB**."]
            if src_id: desc.append(f"Sumber gambar tetap: <#{src_id}>.")
            desc.append("Gunakan template/format yang sudah ditentukan untuk update.")
            emb = discord.Embed(title="pHash DB Board", description="\n".join(desc))
            if src_id: emb.add_field(name="Source thread ID", value=str(src_id), inline=True)
            emb.add_field(name="DB thread ID", value=str(thread.id), inline=True)
            msg = await thread.send(embed=emb)
            try: await msg.pin()
            except Exception: pass

        log.info("pHash DB thread ensured: %s (log channel %s)", thread.id, chan.id)

async def setup(bot):
    await bot.add_cog(PhashDbThreadManager(bot))
