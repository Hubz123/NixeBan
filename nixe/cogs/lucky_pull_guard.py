
# -*- coding: utf-8 -*-
from __future__ import annotations
import os, json, asyncio, logging
from pathlib import Path
import discord
from discord.ext import commands

LOGGER = logging.getLogger(__name__)

def _load_json_env():
    try:
        envp = Path(__file__).resolve().parents[1] / "config" / "runtime_env.json"
        return json.loads(envp.read_text(encoding="utf-8"))
    except Exception:
        return {}

_JSON = _load_json_env()

def _as_bool(v: str) -> bool:
    return str(v).strip().lower() in ("1","true","on","yes")

def _get_env(key: str, default: str = "0") -> str:
    override = _as_bool(_JSON.get("NIXE_ENV_OVERRIDE", os.getenv("NIXE_ENV_OVERRIDE","0")))
    if override:
        v = _JSON.get(key, None)
        if v is not None:
            return str(v)
        return os.getenv(key, default)
    else:
        v = os.getenv(key, None)
        if v is not None:
            return v
        return str(_JSON.get(key, default))

DELETE_ON_GUARD = _as_bool(_get_env("LUCKYPULL_DELETE_ON_GUARD","0"))
MENTION_ON_GUARD = _as_bool(_get_env("LUCKYPULL_MENTION","0"))
USE_HEUR = _as_bool(_get_env("LUCKYPULL_IMAGE_HEURISTICS","1"))
DEBUG = _as_bool(_get_env("LUCKYPULL_DEBUG","0"))
MAX_LAT_MS = int((_get_env("LUCKYPULL_MAX_LATENCY_MS","1000") or "1000").strip())

def _gemini_enabled() -> bool:
    return _as_bool(_get_env("LUCKYPULL_GEMINI_ENABLE","0"))

async def _gemini_judge(message, timeout_ms: int) -> bool:
    if not _gemini_enabled():
        return False
    try:
        from nixe.helpers.lp_gemini_helper import is_lucky_pull as _judge
    except Exception:
        return False
    async def _run():
        try:
            try:
                dec, conf, *_ = _judge(None, threshold=0.65)
                return bool(dec) and float(conf or 0.0) >= 0.65
            except TypeError:
                r = _judge(None)
                return bool(r)
        except Exception:
            return False
    try:
        import asyncio
        return await asyncio.wait_for(_run(), timeout=timeout_ms/1000.0)
    except Exception:
        return False

def _looks_like_image(att) -> bool:
    ct = (getattr(att, "content_type", "") or "").lower()
    if ct.startswith("image/"):
        return True
    name = (getattr(att, "filename","") or "").lower()
    return any(name.endswith(ext) for ext in (".png",".jpg",".jpeg",".webp",".gif",".bmp",".heic",".heif"))

def _heuristic_is_lucky_pull(msg) -> bool:
    atts = getattr(msg, "attachments", []) or []
    return any(_looks_like_image(a) for a in atts)

async def _delete_and_mention(bot, message, redirect_id: int):
    try:
        perms = message.channel.permissions_for(message.guild.me) if message.guild else None
        if perms and not perms.manage_messages:
            if DEBUG: LOGGER.warning("[lpg] missing Manage Messages in #%s", getattr(message.channel, "name", message.channel.id))
            if MENTION_ON_GUARD:
                try:
                    await message.channel.send(f"{message.author.mention} lucky pull pindah ke <#{redirect_id}> ya 🙏 (bot kurang izin hapus)", delete_after=15)
                except Exception:
                    pass
            return
    except Exception:
        pass
    try:
        await message.delete()
        if DEBUG: LOGGER.info("[lpg] deleted a message in %s", message.channel.id)
    except Exception as e:
        if DEBUG: LOGGER.warning("[lpg] delete failed: %s", e)
    if MENTION_ON_GUARD:
        try:
            await message.channel.send(f"{message.author.mention} lucky pull pindah ke <#{redirect_id}> ya 🙏", delete_after=15)
        except Exception:
            pass

class LuckyPullDeleteMentionEnforcer(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message or not getattr(message, "guild", None):
            return
        if DEBUG and not DELETE_ON_GUARD:
            LOGGER.info("[lpg] skip: DELETE_ON_GUARD=0")
        if not DELETE_ON_GUARD:
            return
        author = getattr(message, "author", None)
        if author and getattr(author, "bot", False):
            return
        try:
            guards = [s.strip() for s in (_get_env("LUCKYPULL_GUARD_CHANNELS","") or "").split(",") if s.strip().isdigit()]
            redirect_id = int((_get_env("LUCKYPULL_REDIRECT_CHANNEL_ID","0") or "0").strip())
            if not redirect_id:
                if DEBUG: LOGGER.info("[lpg] skip: redirect_id=0")
                return
            ch_id = int(message.channel.id)
            if str(ch_id) not in guards:
                if DEBUG: LOGGER.info("[lpg] skip: channel %s not in guards=%s", ch_id, guards)
                return
            if ch_id == redirect_id:
                if DEBUG: LOGGER.info("[lpg] skip: anti-loop (in redirect channel)")
                return

            is_lp = False
            if USE_HEUR:
                is_lp = _heuristic_is_lucky_pull(message)
                if DEBUG: LOGGER.info("[lpg] heur=%s (attachments=%d) in #%s", is_lp, len(message.attachments or []), ch_id)

            if not is_lp and _gemini_enabled():
                is_lp = await _gemini_judge(message, MAX_LAT_MS)
                if DEBUG: LOGGER.info("[lpg] gemini=%s (timeout=%dms) in #%s", is_lp, MAX_LAT_MS, ch_id)

            if is_lp:
                await _delete_and_mention(self.bot, message, redirect_id)
            else:
                if DEBUG: LOGGER.info("[lpg] skip: not lucky-pull in #%s", ch_id)
        except Exception as e:
            if DEBUG: LOGGER.exception("[lpg] error: %s", e)

class LuckyPullGuard(LuckyPullDeleteMentionEnforcer):
    pass

async def setup(bot):
    if DEBUG:
        try:
            LOGGER.setLevel(logging.INFO)
        except Exception:
            pass
        LOGGER.info("[lpg] setup: DELETE=%s MENTION=%s HEUR=%s GEM=%s MAXLAT=%sms GUARDS=%s REDIR=%s OVERRIDE_JSON=%s",
                    DELETE_ON_GUARD, MENTION_ON_GUARD, USE_HEUR, _gemini_enabled(),
                    MAX_LAT_MS, _get_env("LUCKYPULL_GUARD_CHANNELS",""), _get_env("LUCKYPULL_REDIRECT_CHANNEL_ID","0"),
                    _JSON.get("NIXE_ENV_OVERRIDE","0"))
    if bot.get_cog("LuckyPullGuard") or bot.get_cog("LuckyPullDeleteMentionEnforcer"):
        return
    try:
        await bot.add_cog(LuckyPullDeleteMentionEnforcer(bot))
    except Exception:
        pass
