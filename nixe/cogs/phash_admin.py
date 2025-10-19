from __future__ import annotations

import json
import os
import re
from io import BytesIO
from typing import List, Optional

import discord
from discord import app_commands
from discord.ext import commands

# Optional deps
try:
    from PIL import Image as _PIL_Image
except Exception:
    _PIL_Image = None

try:
    import imagehash as _imagehash
except Exception:
    _imagehash = None

# Read same env/marker as runtime (no imports to avoid circular deps)
MARKER = os.getenv("PHASH_DB_MARKER", "SATPAMBOT_PHASH_DB_V1")
_DEFAULT_INBOX = "imagephising,imagelogphising,image-phising,image_phising,image-phishing,image_phishing"
INBOX_NAMES = [n.strip() for n in os.getenv("PHASH_INBOX_THREAD", _DEFAULT_INBOX).split(",") if n.strip()]

HEX16 = re.compile(r"^[0-9a-f]{16}$", re.I)
BLOCK_RE = re.compile(
    r"(?:^|\n)\s*%s\s*```(?:json)?\s*(\{.*?\})\s*```" % re.escape(MARKER),
    re.I | re.S,
)
INBOX_FUZZY = re.compile(r"(image.*phis?h|phish.*image|image.*phish|imagelog.*phis?h)", re.I)

def _norm_hashes(obj):
    out = []
    def push(x):
        if isinstance(x, str) and HEX16.match(x.strip()):
            out.append(x.strip())
    if isinstance(obj, dict):
        if isinstance(obj.get("phash"), list):
            for h in obj["phash"]: push(h)
        if isinstance(obj.get("items"), list):
            for it in obj["items"]:
                if isinstance(it, dict): push(it.get("hash"))
        if isinstance(obj.get("hashes"), list):
            for h in obj["hashes"]: push(h)
    elif isinstance(obj, list):
        for it in obj:
            if isinstance(it, dict): push(it.get("hash"))
            else: push(it)
    seen=set(); uniq=[]
    for h in out:
        if h not in seen:
            seen.add(h); uniq.append(h)
    return uniq

def _compute_phash(raw: bytes) -> Optional[str]:
    if _PIL_Image is None or _imagehash is None:
        return None
    try:
        im = _PIL_Image.open(BytesIO(raw)).convert("RGB")
        return str(_imagehash.phash(im))
    except Exception:
        return None

class PhashAdmin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    group = app_commands.Group(name="phash", description="pHash DB tools")

    async def _candidate_threads(self, guild: discord.Guild) -> List[discord.Thread]:
        names_l = {n.lower() for n in INBOX_NAMES}
        hits: List[discord.Thread] = []
        # active threads cache
        for t in guild.threads:
            if not isinstance(t, discord.Thread):
                continue
            n=(t.name or '').lower()
            if n in names_l or INBOX_FUZZY.search(n or ""):
                hits.append(t)
        # walk channels
        for ch in guild.text_channels:
            try:
                async for th in ch.threads():
                    n=(th.name or '').lower()
                    if n in names_l or INBOX_FUZZY.search(n or ""):
                        hits.append(th)
            except Exception:
                continue
        # dedup
        seen=set(); ded=[]
        for t in hits:
            if t.id not in seen:
                seen.add(t.id); ded.append(t)
        return ded

    async def _get_or_create_db_message(self, thread: discord.Thread) -> Optional[discord.Message]:
        for src in [thread, thread.parent]:
            if not isinstance(src, (discord.TextChannel, discord.Thread)):
                continue
            try:
                async for msg in src.history(limit=100):
                    if isinstance(msg.content, str) and MARKER in msg.content:
                        m = BLOCK_RE.search(msg.content)
                        if m:
                            return msg
            except Exception:
                continue
        parent = thread.parent if isinstance(thread.parent, discord.TextChannel) else thread
        try:
            payload = {"phash": []}
            content = f"{MARKER}\n```json\n{json.dumps(payload, ensure_ascii=False)}\n```"
            return await parent.send(content)
        except Exception:
            return None

    @group.command(name="status", description="Show pHash runtime status and DB summary")
    async def status(self, interaction: discord.Interaction):
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("Use this in a server.", ephemeral=True)
            return
        threads = await self._candidate_threads(guild)
        hit_names = ", ".join(f"#{t.name}" for t in threads[:6]) or "(none)"
        msg = None
        if threads:
            msg = await self._get_or_create_db_message(threads[0])
        count = 0
        if msg and isinstance(msg.content, str):
            m = BLOCK_RE.search(msg.content)
            if m:
                try:
                    obj = json.loads(m.group(1))
                    count = len(_norm_hashes(obj))
                except Exception:
                    pass
        libs = [
            f"Pillow={'OK' if _PIL_Image else 'MISSING'}",
            f"ImageHash={'OK' if _imagehash else 'MISSING'}",
        ]
        await interaction.response.send_message(
            f"**pHash status**\n- INBOX names: {', '.join(INBOX_NAMES)}\n- Fuzzy: `{INBOX_FUZZY.pattern}`\n- Candidate threads: {hit_names}\n- DB count: **{count}**\n- Libs: {', '.join(libs)}",
            ephemeral=True
        )

    @group.command(name="reseed", description="Backfill recent images from inbox threads into the pHash DB")
    @app_commands.describe(limit_msgs="Messages to scan per inbox thread (default 120)", limit_imgs="Max images to hash (default 80)")
    async def reseed(self, interaction: discord.Interaction, limit_msgs: int = 120, limit_imgs: int = 80):
        await interaction.response.defer(ephemeral=True, thinking=True)
        guild = interaction.guild
        if guild is None:
            await interaction.followup.send("Use this in a server.", ephemeral=True)
            return
        threads = await self._candidate_threads(guild)
        if not threads:
            await interaction.followup.send("No inbox thread detected.", ephemeral=True); return
        total_imgs = 0
        total_new = 0
        for t in threads:
            phs: List[str] = []
            async for msg in t.history(limit=limit_msgs):
                if not msg.attachments:
                    continue
                imgs = [a for a in msg.attachments if isinstance(a.filename, str) and a.filename.lower().endswith((".png",".jpg",".jpeg",".webp",".gif",".bmp",".tif",".tiff",".heic",".heif"))]
                for att in imgs:
                    if total_imgs >= limit_imgs:
                        break
                    try:
                        raw = await att.read()
                        ph = _compute_phash(raw)
                        if ph and HEX16.match(ph):
                            phs.append(ph); total_imgs += 1
                    except Exception:
                        continue
                if total_imgs >= limit_imgs:
                    break
            if phs:
                # merge into db message
                msg = await self._get_or_create_db_message(t)
                if msg and isinstance(msg.content, str):
                    try:
                        m = BLOCK_RE.search(msg.content)
                        obj = json.loads(m.group(1)) if m else {"phash": []}
                    except Exception:
                        obj = {"phash": []}
                    current = _norm_hashes(obj)
                    seen=set(current)
                    merged = current + [h for h in phs if h not in seen]
                    if merged != current:
                        content = f"{MARKER}\n```json\n{json.dumps({'phash': merged}, ensure_ascii=False)}\n```"
                        try:
                            await msg.edit(content=content); total_new += (len(merged)-len(current))
                        except Exception:
                            pass
        await interaction.followup.send(f"Reseed done. Hashed images: {total_imgs}, new pHash appended: ~{total_new}.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(PhashAdmin(bot))
    try:
        bot.tree.add_command(PhashAdmin.group)
    except Exception:
        pass