
# -*- coding: utf-8 -*-
from __future__ import annotations
import os, json, asyncio, logging
from pathlib import Path
import discord
from discord.ext import commands

LOGGER = logging.getLogger(__name__)

def _get_env(key: str, default: str = "0") -> str:
    v = os.getenv(key)
    if v is not None:
        return v
    try:
        envp = Path(__file__).resolve().parents[1] / "config" / "runtime_env.json"
        data = json.loads(envp.read_text(encoding="utf-8"))
        v = data.get(key, default)
        return "" if v is None else str(v)
    except Exception:
        return default

DELETE_ON_GUARD = _get_env("LUCKYPULL_DELETE_ON_GUARD","0").strip() == "1"
MENTION_ON_GUARD = _get_env("LUCKYPULL_MENTION","0").strip() == "1"
USE_HEUR = _get_env("LUCKYPULL_IMAGE_HEURISTICS","1").strip() in ("1","true","on","yes")
DEBUG = _get_env("LUCKYPULL_DEBUG","0").strip() in ("1","true","on","yes")
MAX_LAT_MS = int((_get_env("LUCKYPULL_MAX_LATENCY_MS","1000") or "1000").strip())

# Gemini bridge (optional)
def _gemini_enabled() -> bool:
    return _get_env("LUCKYPULL_GEMINI_ENABLE","0").strip() in ("1","true","on","yes")

async def _gemini_judge(message: discord.Message, timeout_ms: int) -> bool:
    if not _gemini_enabled():
        return False
    try:
        # Import helper lazily to avoid hard dep if not present
        from nixe.helpers.lp_gemini_helper import is_lucky_pull as _judge
    except Exception:
        return False

    # Collect lightweight image bytes (Discord gives us URLs; avoid heavy I/O here)
    # We will only use existing attachment metadata; if gemini helper needs bytes,
    # it should use a fast head/thumbnail path or short timeout network fetch.
    async def _run():
        # Try pass None to let helper do its own fetch, or bail if it can't
        # Contract: helper returns (bool_decision, confidence, reason)
        try:
            # Allow helper decide based on message object if supported
            if hasattr(_judge, "__call__"):
                res = False
                conf = 0.0
                try:
                    # Some helpers accept (message) only
                    dec, conf, _ = _judge(None, threshold=0.65)
                    res = bool(dec) and conf >= 0.65
                except TypeError:
                    # Fallback path (no-bytes support) -> skip
                    res = False
                return res
            return False
        except Exception:
            return False

    try:
        return await asyncio.wait_for(_run(), timeout=timeout_ms/1000.0)
    except asyncio.TimeoutError:
        return False
    except Exception:
        return False

def _looks_like_image(att: discord.Attachment) -> bool:
    ct = (att.content_type or "").lower() if hasattr(att, "content_type") else ""
    if ct.startswith("image/"):
        return True
    name = (att.filename or "").lower()
    return any(name.endswith(ext) for ext in (".png",".jpg",".jpeg",".webp",".gif",".bmp",".heic",".heif"))

def _heuristic_is_lucky_pull(msg: discord.Message) -> bool:
    # Fast heuristic: has >=1 image attachment
    return any(_looks_like_image(a) for a in getattr(msg, "attachments", []) or [])

async def _delete_and_mention(bot, message: discord.Message, redirect_id: int):
    # Check permission before trying delete
    try:
        perms = message.channel.permissions_for(message.guild.me) if message.guild else None
        if perms and not perms.manage_messages:
            if DEBUG: LOGGER.warning("[lpg] missing Manage Messages in #%s", getattr(message.channel, "name", message.channel.id))
            # still drop a friendly notice if allowed
            if MENTION_ON_GUARD:
                try:
                    await message.channel.send(f"{message.author.mention} lucky pull pindah ke <#{redirect_id}> ya 🙏 (bot kurang izin hapus)", delete_after=15)
                except Exception:
                    pass
            return
    except Exception:
        pass

    # Try delete
    try:
        await message.delete()
        if DEBUG: LOGGER.info("[lpg] deleted a message in %s", message.channel.id)
    except Exception as e:
        if DEBUG: LOGGER.warning("[lpg] delete failed: %s", e)

    # Mention after delete (non-blocking)
    if MENTION_ON_GUARD:
        try:
            await message.channel.send(f"{message.author.mention} lucky pull pindah ke <#{redirect_id}> ya 🙏", delete_after=15)
        except Exception:
            pass

class LuckyPullDeleteMentionEnforcer(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Basic rejects
        if not (DELETE_ON_GUARD and message and getattr(message, "guild", None)):
            return
        author = getattr(message, "author", None)
        if author and getattr(author, "bot", False):
            return

        try:
            guards = [s.strip() for s in (_get_env("LUCKYPULL_GUARD_CHANNELS","") or "").split(",") if s.strip().isdigit()]
            redirect_id = int((_get_env("LUCKYPULL_REDIRECT_CHANNEL_ID","0") or "0").strip())
            if not redirect_id: return
            ch_id = int(message.channel.id)

            if str(ch_id) not in guards:
                return
            if ch_id == redirect_id:
                return  # anti-loop

            # Decide lucky-pull quickly
            is_lp = False
            if USE_HEUR:
                is_lp = _heuristic_is_lucky_pull(message)
                if DEBUG: LOGGER.info("[lpg] heur=%s (attachments=%d) in #%s", is_lp, len(message.attachments or []), ch_id)

            if not is_lp and _gemini_enabled():
                # Try a very short Gemini decision
                is_lp = await _gemini_judge(message, MAX_LAT_MS)
                if DEBUG: LOGGER.info("[lpg] gemini=%s (timeout=%dms) in #%s", is_lp, MAX_LAT_MS, ch_id)

            if is_lp:
                await _delete_and_mention(self.bot, message, redirect_id)

        except Exception as e:
            if DEBUG: LOGGER.exception("[lpg] error: %s", e)

# Back-compat alias
class LuckyPullGuard(LuckyPullDeleteMentionEnforcer):
    pass

async def setup(bot):
    if bot.get_cog("LuckyPullGuard") or bot.get_cog("LuckyPullDeleteMentionEnforcer"):
        return
    try:
        await bot.add_cog(LuckyPullDeleteMentionEnforcer(bot))
    except Exception:
        pass
