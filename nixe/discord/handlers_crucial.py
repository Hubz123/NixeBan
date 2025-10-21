from __future__ import annotations
import os, logging, time, discord
from discord.ext import tasks

log = logging.getLogger(__name__)

# module config helper
def _cfg(key, default=None):
    try:
        from nixe.config import load as _load_cfg  # type: ignore
        cfg = _load_cfg() or {}
        return cfg.get(key, default)
    except Exception:
        return default

def _int(v, d=0):
    try:
        return int(v)
    except Exception:
        return d

def _bool(v, d=False):
    if isinstance(v, bool): return v
    if v is None: return d
    return str(v).lower() in ("1","true","yes","on")

HEARTBEAT_ENABLE = _bool(_cfg("HEARTBEAT_ENABLE", False), False)
STATUS_EMBED_ON_READY = _bool(_cfg("STATUS_EMBED_ON_READY", False), False)
LOG_CHANNEL_ID = _int(_cfg("BAN_LOG_CHANNEL_ID", _cfg("LOG_CHANNEL_ID", 0)), 0)
MODE = os.getenv("FLASK_ENV", _cfg("FLASK_ENV", "production"))

# BAN dedupe
_ban_seen = {}
async def _ban_once(self: discord.Guild, user, *args, **kwargs):
    ttl = _int(os.getenv("BAN_DEDUP_TTL", "10"), 10)
    uid = getattr(user, "id", user)
    key = f"{self.id}:{uid}"
    now = time.time()
    exp = _ban_seen.get(key, 0)
    if exp > now:
        return
    _ban_seen[key] = now + max(1, ttl)
    return await _orig_ban(self, user, *args, **kwargs)

if not hasattr(discord.Guild, "_nixe_ban_patched"):
    _orig_ban = discord.Guild.ban
    discord.Guild.ban = _ban_once
    discord.Guild._nixe_ban_patched = True

_last_hb_ts = 0
@tasks.loop(minutes=30)
async def status_heartbeat(bot, ch_id: int):
    global _last_hb_ts
    if not HEARTBEAT_ENABLE:
        return
    ch = bot.get_channel(ch_id) if ch_id else None
    if ch and isinstance(ch, discord.TextChannel):
        try:
            now = time.time()
            if now - _last_hb_ts < 600:
                return
            _last_hb_ts = now
            uptime = int(now - getattr(bot, "start_time", now))
            embed = discord.Embed(title="NIXE Status", description=f"✅ Online\n⏱️ Uptime: ~{uptime}s")
            await ch.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
        except Exception:
            pass

async def wire_handlers(bot: discord.Client):
    @bot.event
    async def setup_hook():
        try:
            from nixe.cogs_loader import load_cogs
            await load_cogs(bot)
            log.info("🧩 Cogs loaded (core + autodiscover).")
        except Exception as e:
            log.error("cogs_loader failed: %s", e, exc_info=True)
        # optional metrics
        if os.getenv("METRICS_DISABLE", "0") not in ("1", "true", "TRUE"):
            for ext in ("nixe.cogs.live_metrics_push", "nixe.metrics.live_metrics_push"):
                try:
                    if ext not in bot.extensions:
                        await bot.load_extension(ext)
                        log.info("✅ Loaded metrics cog: %s", ext)
                        break
                except Exception:
                    pass

    @bot.event
    async def on_ready():
        try:
            if not getattr(bot, "start_time", None):
                import time as _t; bot.start_time = _t.time()
            user = getattr(bot, "user", None)
            log.info("✅ Bot berhasil login sebagai %s (ID: %s)", getattr(user, "name", "?"), getattr(user, "id", "?"))
            log.info("🌐 Mode: %s", MODE)
        except Exception:
            log.info("✅ Bot login.")
        if HEARTBEAT_ENABLE and not status_heartbeat.is_running():
            status_heartbeat.start(bot, LOG_CHANNEL_ID)
        if STATUS_EMBED_ON_READY and LOG_CHANNEL_ID:
            try:
                ch = bot.get_channel(LOG_CHANNEL_ID)
                if ch and isinstance(ch, discord.TextChannel):
                    uptime = int(time.time() - getattr(bot, "start_time", time.time()))
                    embed = discord.Embed(title="NIXE Status", description=f"✅ Online\n⏱️ Uptime: ~{uptime}s")
                    await ch.send(embed=embed, allowed_mentions=discord.AllowedMentions.none())
            except Exception:
                pass

    @bot.event
    async def on_message(message: discord.Message):
        if getattr(message.author, "bot", False):
            return
        try:
            from .message_handlers import handle_on_message
            await handle_on_message(bot, message)
        except Exception as e:
            log.error("on_message pipeline error: %s", e)
        try:
            from discord.ext import commands as _commands
            if isinstance(bot, _commands.Bot):
                await bot.process_commands(message)
        except Exception as e:
            log.error("process_commands error: %s", e)