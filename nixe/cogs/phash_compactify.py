# -*- coding: utf-8 -*-
from __future__ import annotations

import re, json, io, os
import discord
from discord.ext import commands
from discord import app_commands

PAGE_SIZE = 20

def _extract_json_blob(text: str):
    if not text: return None
    t = text.strip()
    if t.startswith("```") and t.endswith("```"):
        t = t.strip("`").strip()
    import re as _re
    m = _re.search(r"(\{.*\}|\[.*\])", t, flags=_re.S)
    return m.group(1) if m else None

def _parse(blob: str):
    try:
        data = json.loads(blob)
        if isinstance(data, dict) and "phash" in data: data = data["phash"]
        if isinstance(data, list): return [str(x) for x in data]
    except Exception: pass
    return []

class Pager(discord.ui.View):
    def __init__(self, items):
        super().__init__(timeout=None)
        self.items = items
        self.idx = 0
    def _pages(self):
        return [self.items[i:i+PAGE_SIZE] for i in range(0, len(self.items), PAGE_SIZE)] or [[]]
    def _embed(self):
        pages = self._pages()
        i = max(0, min(self.idx, len(pages)-1))
        body = "\n".join(f"`{h}`" for h in pages[i])
        e = discord.Embed(title="pHash (compact)", description=body or "*empty*", color=0x2e8b57)
        e.set_footer(text=f"Page {i+1}/{len(pages)}")
        return e
    async def _flip(self, interaction, to=None, delta=0):
        if to is not None: self.idx = to
        else: self.idx += delta
        await interaction.response.edit_message(embed=self._embed(), view=self)
    @discord.ui.button(label="≪ First", style=discord.ButtonStyle.secondary)
    async def first(self, i, _): await self._flip(i, to=0)
    @discord.ui.button(label="‹ Prev", style=discord.ButtonStyle.secondary)
    async def prev(self, i, _): await self._flip(i, delta=-1)
    @discord.ui.button(label="Next ›", style=discord.ButtonStyle.secondary)
    async def next(self, i, _): await self._flip(i, delta=1)
    @discord.ui.button(label="Last ≫", style=discord.ButtonStyle.secondary)
    async def last(self, i, _): await self._flip(i, to=10**6)

@app_commands.context_menu(name="Compact pHash")
async def compact_message_handler(interaction: discord.Interaction, message: discord.Message):
    blob = _extract_json_blob(message.content or "")
    items = _parse(blob) if blob else []
    if not items:
        return await interaction.response.send_message("Tidak menemukan JSON pHash di pesan itu.", ephemeral=True)
    view = Pager(items)
    await interaction.response.send_message(embed=view._embed(), view=view, ephemeral=False)

class PhashCompactify(commands.Cog):
    def __init__(self, bot): self.bot = bot

async def setup(bot: commands.Bot):
    await bot.add_cog(PhashCompactify(bot))
    gid = os.getenv("GUILD_METRICS_ID")
    guild_obj = discord.Object(id=int(gid)) if gid and gid.isdigit() else None
    if guild_obj:
        bot.tree.add_command(compact_message_handler, guild=guild_obj)
        await bot.tree.sync(guild=guild_obj)
    else:
        bot.tree.add_command(compact_message_handler)
        await bot.tree.sync()