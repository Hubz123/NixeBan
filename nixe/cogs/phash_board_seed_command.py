
# -*- coding: utf-8 -*-
import os, discord
from discord.ext import commands

def _marker() -> str:
    return (os.getenv("PHASH_DB_MARKER") or "NIXE_PHASH_DB_V1").strip()

BOARD_TEMPLATE = "[pHash DB Board] {m}\nDo NOT delete this message. Bot will edit this message to maintain the pHash database board.\n\nMarker: {m}\nNotes : This message is pinned automatically. You can move it to the top of the thread.\n[phash-db-board]"

class PhashBoardSeed(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.guild_only()
    @commands.command(name="phash-seed")
    @commands.has_guild_permissions(manage_guild=True)
    async def phash_seed(self, ctx: commands.Context, arg: str | None = None):
        use_here = (arg == "here")
        dest = ctx.channel if use_here else None
        if not isinstance(dest, (discord.Thread, discord.TextChannel)):
            await ctx.reply("Jalankan `&phash-seed here` **di thread tujuan** (phash-db).", mention_author=False); return
        if isinstance(dest, discord.Thread) and getattr(dest, "archived", False):
            try: await dest.edit(archived=False, locked=False, reason="phash-seed")
            except Exception: pass
        content = BOARD_TEMPLATE.format(m=_marker())
        try: msg = await dest.send(content)
        except discord.Forbidden:
            await ctx.reply("Forbidden: izin kirim pesan kurang.", mention_author=False); return
        except Exception as e:
            await ctx.reply(f"Gagal buat board: {e!r}", mention_author=False); return
        try: await msg.pin(reason="pHash DB board")
        except Exception: pass
        await ctx.reply(f"✅ Board dibuat. Message ID: `{msg.id}` — langsung jalan tanpa set env (auto-discover).", mention_author=False)

async def setup(bot: commands.Bot):
    await bot.add_cog(PhashBoardSeed(bot))
