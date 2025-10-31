# -*- coding: utf-8 -*-
"""
a00_mirror_before_delete_overlay
- Mirrors image attachments to a protected thread ASAP on_message,
  so log links won't 404 after guards delete the original message.
- Loaded early (a00_) to race ahead of fast-delete paths.
"""
from __future__ import annotations
import os, logging
import discord
from discord.ext import commands

from nixe.helpers.attachment_mirror import mirror_attachments_for_log

log = logging.getLogger("nixe.cogs.a00_mirror_before_delete_overlay")

def _ids(csv: str | None) -> set[int]:
    s = set()
    if not csv: 
        return s
    for part in csv.split(","):
        part = part.strip()
        if part.isdigit():
            s.add(int(part))
    return s

class MirrorBeforeDeleteOverlay(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.enable = os.getenv("MIRROR_BEFORE_DELETE", "1") != "0"
        self.dest_id = int(os.getenv("MIRROR_DEST_ID", "0") or "0")
        scope = set()
        for key in ("MIRROR_CHANNELS", "LPA_GUARD_CHANNELS", "LPG_GUARD_CHANNELS"):
            scope |= _ids(os.getenv(key, ""))
        self.scope = scope
        if self.enable:
            log.warning("[mirror-overlay] enabled; scope=%s dest=%s", 
                        ",".join(map(str, sorted(self.scope))) or "<any guarded>", 
                        self.dest_id or "<auto>")

    @commands.Cog.listener("on_message")
    async def _on_message(self, message: discord.Message):
        if not self.enable: 
            return
        try:
            if message.author.bot or not message.attachments:
                return
            if self.scope and message.channel.id not in self.scope:
                return
            mirror = await mirror_attachments_for_log(
                self.bot, message, reason="pre-delete", dest_id=self.dest_id, include_phash=True
            )
            if mirror:
                log.info("[mirror-overlay] mirrored -> %s", mirror.jump_url)
        except Exception as e:
            log.debug("[mirror-overlay] err: %r", e)

async def setup(bot: commands.Bot):
    await bot.add_cog(MirrorBeforeDeleteOverlay(bot))