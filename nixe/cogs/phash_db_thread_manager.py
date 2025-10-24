# Auto-created by ChatGPT patch: Ensure pHash-DB thread exists under log channel
# Safe for smoke: no side-effects on import; executes once on READY.
import asyncio
import logging
from discord.ext import commands
import discord

from nixe import config

log = logging.getLogger(__name__)

class PhashDbThreadManager(commands.Cog):
    """
    Ensure pHash-DB thread exists under PHISH_LOG_CHAN_ID and pin a board message.
    It also exposes runtime thread id to other cogs via:
        - bot.phash_db_thread_id
        - nixe.config.PHASH_DB_THREAD_ID (overridden at runtime)
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._ran = False  # guard to avoid double work on reconnects

    @commands.Cog.listener()
    async def on_ready(self):
        if self._ran:
            return
        self._ran = True
        try:
            await self.ensure_thread_and_board()
        except Exception as e:
            log.exception("phash-db ensure failed: %s", e)

    async def ensure_thread_and_board(self):
        chan_id = getattr(config, "PHISH_LOG_CHAN_ID", None) or getattr(config, "LOG_CHANNEL_ID", None)
        if not chan_id:
            log.warning("PHISH_LOG_CHAN_ID/LOG_CHANNEL_ID not set; skip phash-db ensure")
            return

        chan = self.bot.get_channel(chan_id)
        if chan is None:
            try:
                chan = await self.bot.fetch_channel(chan_id)
            except Exception:
                log.warning("Cannot fetch channel id=%s", chan_id)
                return

        if not isinstance(chan, (discord.TextChannel, discord.ForumChannel)):
            log.warning("Channel %s is not a Text/Forum channel", chan_id)
            return

        # Determine desired thread name
        thread_name = getattr(config, "PHASH_DB_THREAD_NAME", None) or "phash-db"

        # Try use configured thread id if provided
        desired_thread_id = getattr(config, "PHASH_DB_THREAD_ID", None)
        thread = None
        if desired_thread_id:
            thread = self.bot.get_channel(desired_thread_id) or await self._maybe_fetch_channel(desired_thread_id)

        # Discover by name in active threads
        if thread is None and hasattr(chan, "threads"):
            for t in chan.threads:
                if (t.name or "").lower() == thread_name.lower():
                    thread = t
                    break

        # Look in archived threads (best-effort)
        if thread is None and isinstance(chan, discord.TextChannel):
            try:
                async for t in chan.archived_threads(limit=50):
                    if (t.name or "").lower() == thread_name.lower():
                        thread = t
                        break
            except Exception:
                pass

        # Create if missing
        if thread is None:
            try:
                # Prefer public thread under the log channel
                thread = await chan.create_thread(
                    name=thread_name,
                    type=discord.ChannelType.public_thread,
                    auto_archive_duration=10080  # 7 days
                )
                log.info("Created pHash-DB thread id=%s under chan=%s", thread.id, chan.id)
            except Exception as e:
                log.exception("Failed creating pHash-DB thread: %s", e)
                return

        # Expose runtime overrides for other cogs
        try:
            self.bot.phash_db_thread_id = thread.id
            import nixe.config as _cfg
            _cfg.PHASH_DB_THREAD_ID = thread.id  # dynamic override
        except Exception:
            pass

        # Ensure pinned "board" message exists
        await self._ensure_board_message(thread)

        log.info("pHash DB thread ensured: %s (log channel %s)", thread.id, chan.id)

    async def _maybe_fetch_channel(self, cid):
        try:
            return await self.bot.fetch_channel(cid)
        except Exception:
            return None

    async def _ensure_board_message(self, thread: discord.abc.GuildChannel):
        try:
            pins = await thread.pins()
        except Exception:
            pins = []
        board = None
        for m in pins:
            if m.author.bot and any((emb.title or "").lower().startswith("phash db board") for emb in m.embeds):
                board = m
                break

        if board is None:
            # Build board embed
            source_thread_id = getattr(config, "PHASH_SOURCE_THREAD_ID", None) or getattr(config, "PHASH_IMAGEPHISH_THREAD_ID", None)
            desc_lines = []
            desc_lines.append("Thread ini menyimpan **pHash DB**.")
            if source_thread_id:
                desc_lines.append(f"Sumber gambar tetap: <#{source_thread_id}>.")
            desc_lines.append("Gunakan template/format yang sudah ditentukan untuk update.")
            emb = discord.Embed(
                title="pHash DB Board",
                description="\n".join(desc_lines),
            )
            msg = await thread.send(embed=emb)
            try:
                await msg.pin()
            except Exception:
                pass
        else:
            # nothing — already present
            pass

async def setup(bot):
    await bot.add_cog(PhashDbThreadManager(bot))
