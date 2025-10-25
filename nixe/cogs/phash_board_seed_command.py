
# -*- coding: utf-8 -*-
import os, discord
from discord.ext import commands

def _marker() -> str:
    return (os.getenv("PHASH_DB_MARKER") or "NIXE_PHASH_DB_V1").strip()

def _db_thread_id() -> int | None:
    v = os.getenv("NIXE_PHASH_DB_THREAD_ID") or os.getenv("PHASH_IMAGEPHISH_THREAD_ID")
    try: return int(str(v).strip()) if v else None
    except Exception: return None

def _board_message_id() -> int | None:
    v = os.getenv("PHASH_DB_MESSAGE_ID")
    try: return int(str(v).strip()) if v else None
    except Exception: return None

BOARD_TEMPLATE = "[pHash DB Board] {m}\nDo NOT delete this message. Bot will edit this message to maintain the pHash database board.\n\nMarker: {m}\nNotes : This message is pinned automatically. You can move it to the top of the thread."

class PhashBoardSeed(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="phash-seed")
    @commands.has_guild_permissions(manage_guild=True)
    async def phash_seed(self, ctx: commands.Context, arg: str | None = None):
        force = (arg == "force"); use_here = (arg == "here")
        existing = _board_message_id()
        if existing and not force:
            await ctx.reply(f"PHASH_DB_MESSAGE_ID already set: `{existing}`. Use `&phash-seed force` to create another.", mention_author=False)
            return
        dest = ctx.channel if use_here else None
        if dest is None:
            tid = _db_thread_id()
            if not tid:
                await ctx.reply("NIXE_PHASH_DB_THREAD_ID not set. Use `&phash-seed here` inside the target thread.", mention_author=False); return
            try:
                dest = self.bot.get_channel(tid) or await self.bot.fetch_channel(tid)
            except Exception:
                dest = None
        if not isinstance(dest, (discord.Thread, discord.TextChannel)):
            await ctx.reply("Destination must be a text channel/thread.", mention_author=False); return
        if isinstance(dest, discord.Thread) and getattr(dest, "archived", False):
            try: await dest.edit(archived=False, locked=False, reason="phash-seed")
            except Exception: pass
        content = BOARD_TEMPLATE.format(m=_marker())
        try: msg = await dest.send(content)
        except discord.Forbidden:
            await ctx.reply("Forbidden: missing permission to send to destination.", mention_author=False); return
        except Exception as e:
            await ctx.reply(f"Failed to send: {e!r}", mention_author=False); return
        try: await msg.pin(reason="pHash DB board")
        except Exception: pass
        await ctx.reply(f"✅ Board created in <#{dest.id}>. Message ID: `{msg.id}`\n→ Set `PHASH_DB_MESSAGE_ID={msg.id}` in your .env then restart.", mention_author=False)

async def setup(bot: commands.Bot):
    await bot.add_cog(PhashBoardSeed(bot))
