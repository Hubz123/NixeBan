
# -*- coding: utf-8 -*-
from __future__ import annotations

import os, re, json, logging, asyncio
from typing import Optional, List, Tuple

import discord
from discord.ext import commands

log = logging.getLogger(__name__)

# ---------------- Utilities ----------------
IMAGE_EXTS = (".png",".jpg",".jpeg",".webp",".gif",".bmp",".tif",".tiff",".heic",".heif")

def _csv_ids(v: str) -> List[int]:
    out: List[int] = []
    for p in (v or "").split(","):
        p = p.strip()
        if not p:
            continue
        try:
            out.append(int(p))
        except Exception:
            pass
    return out

def _parse_phash_json(text: str) -> Tuple[int, Optional[dict]]:
    # Try to locate a JSON object (often inside ```json ... ```)
    try:
        # prefer fenced block
        s = text.find("```json")
        if s >= 0:
            s = text.find("{", s)
            e = text.find("```", s)
            blob = text[s:e]
            obj = json.loads(blob)
            arr = obj.get("phash") or []
            return (len(arr) if isinstance(arr, list) else 0, obj)
        # fallback: first {...} anywhere
        m = re.search(r"\{[\s\S]*\}", text or "", re.M)
        if m:
            obj = json.loads(m.group(0))
            arr = obj.get("phash") or []
            return (len(arr) if isinstance(arr, list) else 0, obj)
    except Exception:
        pass
    return (0, None)

def _fmt_ts(iso: Optional[str]) -> str:
    return iso or "—"

# ---------------- Cog ----------------
class StatusCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ----------- pHash status -----------
    @commands.guild_only()
    @commands.command(name="phash-status")
    async def phash_status(self, ctx: commands.Context):
        """Tampilkan status pHash DB board + ringkasan jumlah token."""
        try:
            from nixe.helpers.phash_board import get_pinned_db_message
        except Exception as e:
            await ctx.reply(f"phash-status: helper tidak ditemukan: {e!r}", mention_author=False)
            return

        src_id = int(os.getenv("NIXE_PHASH_SOURCE_THREAD_ID", "0") or 0)
        db_id  = int(os.getenv("NIXE_PHASH_DB_THREAD_ID", "0") or 0)

        msg = await get_pinned_db_message(self.bot)
        if not msg:
            await ctx.reply("phash-status: board belum ditemukan. Jalankan `&phash-seed here` di thread DB atau set PHASH_DB_MESSAGE_ID=0 untuk autoseed.", mention_author=False)
            return

        count, obj = _parse_phash_json(msg.content or "")

        embed = discord.Embed(title="pHash DB Status", color=0x4caf50)
        embed.add_field(name="Board Msg ID", value=str(msg.id), inline=True)
        embed.add_field(name="DB Thread ID", value=str(db_id or getattr(msg.channel, "id", "—")), inline=True)
        embed.add_field(name="Source Thread ID", value=str(src_id or "—"), inline=True)
        embed.add_field(name="Tokens", value=str(count), inline=True)
        embed.add_field(name="Last Edited", value=_fmt_ts(getattr(msg, "edited_at", None).isoformat() if getattr(msg, "edited_at", None) else "—"), inline=True)
        await ctx.reply(embed=embed, mention_author=False)

    # ----------- Lucky Pull status -----------
    @commands.guild_only()
    @commands.command(name="luckypull-status")
    async def luckypull_status(self, ctx: commands.Context):
        """Tampilkan status konfigurasi Lucky Pull dan (opsional) uji 1 gambar via reply."""
        lpa = ctx.bot.get_cog("LuckyPullAuto")
        # Read config either from cog or env
        def env_bool(k, d="0"):
            return (os.getenv(k, d) == "1")
        allow = _csv_ids(os.getenv("LUCKYPULL_ALLOW_CHANNELS",""))
        guard = _csv_ids(os.getenv("LUCKYPULL_GUARD_CHANNELS",""))
        redir = int(os.getenv("LUCKYPULL_REDIRECT_CHANNEL_ID","0") or 0)
        mention = env_bool("LUCKYPULL_MENTION","1")
        heur = env_bool("LUCKYPULL_IMAGE_HEURISTICS","1")
        gem_en = env_bool("LUCKYPULL_GEMINI_ENABLE","0")
        gem_model = os.getenv("LUCKYPULL_GEMINI_MODEL","gemini-1.5-flash")
        pat = os.getenv("LUCKYPULL_PATTERN", r"\b(wish|warp|pull|tenpull|gacha|roll|multi|banner|rate up|pity|constellation|character event|weapon event)\b")

        if lpa:
            # prefer live values from cog
            try:
                allow = getattr(lpa, "allow_channels", allow)
                guard = getattr(lpa, "guard_channels", guard)
                redir = getattr(lpa, "redirect_channel_id", redir)
                mention = getattr(lpa, "mention", mention)
                heur = getattr(lpa, "image_heur", heur)
                gem_en = getattr(lpa, "gemini_enable", gem_en)
                gem_model = getattr(lpa, "gemini_model", gem_model)
                pat_obj = getattr(lpa, "_pat", None)
                if pat_obj:
                    pat = getattr(pat_obj, "pattern", pat)
            except Exception:
                pass

        # Build embed
        embed = discord.Embed(title="Lucky Pull Status", color=0x03a9f4)
        embed.add_field(name="Allow Channels", value=", ".join(map(str, allow)) or "—", inline=False)
        embed.add_field(name="Guard Channels", value=(("GLOBAL" if not guard else ", ".join(map(str, guard)))), inline=False)
        embed.add_field(name="Redirect To", value=(f"<#{redir}>" if redir else "—"), inline=True)
        embed.add_field(name="Mention", value=str(mention), inline=True)
        embed.add_field(name="Image Heuristic", value=str(heur), inline=True)
        embed.add_field(name="Gemini", value=(f"ON ({gem_model})" if gem_en else "OFF"), inline=True)
        embed.add_field(name="Text Pattern", value=f"`{pat}`", inline=False)

        # If the command replies to a message with image, run a dry-run test
        ref = getattr(ctx.message, "reference", None)
        if ref and getattr(ref, "message_id", None):
            try:
                m = await ctx.channel.fetch_message(ref.message_id)
            except Exception as e:
                await ctx.reply(f"Dry-run gagal ambil pesan: {e!r}", mention_author=False)
                await ctx.reply(embed=embed, mention_author=False)
                return

            text_ok = False
            img_ok = False
            gem_ok = None

            # text
            if lpa and hasattr(lpa, "_looks_text"):
                try:
                    text_ok = bool(lpa._looks_text(m.content or ""))
                except Exception:
                    text_ok = False
            else:
                try:
                    text_ok = bool(re.search(pat, m.content or "", re.I))
                except Exception:
                    text_ok = False

            # image heur
            if lpa and hasattr(lpa, "_looks_image") and m.attachments:
                for a in m.attachments:
                    fn = (a.filename or "").lower()
                    if not any(fn.endswith(ext) for ext in IMAGE_EXTS):
                        continue
                    try:
                        raw = await a.read()
                    except Exception:
                        raw = None
                    if raw:
                        try:
                            img_ok = bool(lpa._looks_image(raw))
                        except Exception:
                            img_ok = False
                        break

            # gemini
            if gem_en and m.attachments:
                if lpa and hasattr(lpa, "_gemini_judge"):
                    try:
                        gem_ok = await lpa._gemini_judge(m.attachments)
                    except Exception:
                        gem_ok = None
                else:
                    gem_ok = None

            embed.add_field(name="Dry-run (reply target)", value=f"text={text_ok}, image={img_ok}, gemini={gem_ok}", inline=False)

        await ctx.reply(embed=embed, mention_author=False)

async def setup(bot: commands.Bot):
    await bot.add_cog(StatusCommands(bot))
