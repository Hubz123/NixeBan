from __future__ import annotations

import os, io, asyncio, logging, json, time as _time, contextlib
from dataclasses import dataclass, field
from typing import Optional, Set, Dict

# ---------- Logging ----------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format="%(levelname)s:%(name)s:%(message)s")
log = logging.getLogger("nixe.main")

# --- Silence aiohttp access logs (/healthz pings) ---
from aiohttp.web_log import AccessLogger
class _SilentAccessLogger(AccessLogger):
    def log(self, request, response, time):
        return

_aio = logging.getLogger("aiohttp.access")
for h in list(_aio.handlers):
    _aio.removeHandler(h)
_aio.propagate = False
_aio.setLevel(logging.CRITICAL)
_aio.disabled = True

# --- Dedupe noisy discord.client logs ---
class _OnceFilter(logging.Filter):
    def __init__(self, needle: str):
        super().__init__(); self.needle=needle; self.seen=False
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        if self.needle in msg:
            if self.seen: return False
            self.seen = True
        return True

logging.getLogger("discord.client").addFilter(_OnceFilter("logging in using static token"))
logging.getLogger("discord.client").addFilter(_OnceFilter("PyNaCl is not installed"))

# ---------- Third-parties ----------
import discord
from discord.ext import commands, tasks
from aiohttp import web
from PIL import Image
try:
    import imagehash
except Exception:
    imagehash = None

# ---------- pHash config via module (no ENV) ----------
try:
    from nixe.config_phash import (
        PHASH_DB_THREAD_ID as DB_THREAD_ID,
        PHASH_DB_MESSAGE_ID as DB_MESSAGE_ID,
        PHASH_DB_STRICT_EDIT as STRICT_EDIT,
        PHASH_IMAGEPHISH_THREAD_ID as LEARN_THREAD_ID,
        PHASH_DB_MAX_ITEMS as MAX_HASHES,
        PHASH_BOARD_EDIT_MIN_INTERVAL as EDIT_MIN_INTERVAL,
    )
except Exception as e:
    raise SystemExit(f"[FATAL] missing config module nixe.config_phash: {e}")

# ---------- Remaining ENV ----------
DISCORD_TOKEN = (os.getenv("DISCORD_TOKEN") or "").strip()
if not DISCORD_TOKEN:
    raise SystemExit("[FATAL] DISCORD_TOKEN missing")
NIXE_MODE = os.getenv("NIXE_MODE", "production")
PORT = int(os.getenv("PORT", "10000"))

# ---------- State ----------
@dataclass
class State:
    phash_tokens: Set[str] = field(default_factory=set)
    last_edit_ts: float = 0.0
    last_fetch_ts: float = 0.0
    hits: int = 0
    bans: int = 0
    images_scanned: int = 0
    dedupe_ban: Dict[int, float] = field(default_factory=dict)
    dedupe_msg: Set[int] = field(default_factory=set)
    bot_ready: bool = False
    pinned_cache_content: str = ""
    discovered_db_message_id: int = 0
    warned_missing_db: bool = False

STATE = State()

# ---------- Hashing ----------
def compute_hash_from_image(img: Image.Image) -> str:
    if imagehash is not None:
        return str(imagehash.phash(img))
    g = img.convert("L").resize((8, 8))
    px = list(g.getdata()); avg = sum(px)/len(px) if px else 0
    bits = "".join("1" if p > avg else "0" for p in px)
    return "".join(f"{int(bits[i:i+4],2):x}" for i in range(0,64,4))

async def image_bytes_to_hash(data: bytes) -> str | None:
    try:
        with Image.open(io.BytesIO(data)) as img:
            return compute_hash_from_image(img.convert("RGB"))
    except Exception:
        return None

# ---------- Discord ----------
intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=True, replied_user=False))

def _parse_tokens_from_pinned(text: str) -> Set[str]:
    tokens: Set[str] = set()
    s = (text or "").strip()
    if not s: return tokens
    with contextlib.suppress(Exception):
        t = s
        if s.startswith("```"):
            t = s.strip("`").strip()
            if t.startswith("json"):
                t = t[4:]
        data = json.loads(t)
        if isinstance(data, dict) and "phash" in data and isinstance(data["phash"], list):
            for x in data["phash"]:
                t2 = str(x).strip().lower()
                if t2: tokens.add(t2[:16])
            return tokens
    for part in s.replace("\\n"," ").split():
        t = part.strip().lower()
        if len(t) in (16,64): tokens.add(t[:16])
    return tokens

def _looks_like_phash_db(text: str) -> bool:
    if not text: return False
    s = text.strip()
    if "[phash-db-board]" in s.lower(): return True
    if "```" in s:
        t = s.strip("`").strip()
        if t.startswith("json"): t = t[4:]
        with contextlib.suppress(Exception):
            data = json.loads(t)
            if isinstance(data, dict) and "phash" in data: return True
    toks = _parse_tokens_from_pinned(s)
    return len(toks) >= 1

async def _discover_db_message_id_in_thread() -> int:
    if DB_THREAD_ID == 0: return 0
    try:
        ch = bot.get_channel(DB_THREAD_ID) or await bot.fetch_channel(DB_THREAD_ID)
    except Exception:
        return 0
    with contextlib.suppress(Exception):
        pins = await ch.pins()
        for m in pins:
            if _looks_like_phash_db(getattr(m, "content", "") or ""):
                return int(m.id)
    with contextlib.suppress(Exception):
        async for m in ch.history(limit=500):
            if _looks_like_phash_db(getattr(m, "content", "") or ""):
                return int(m.id)
    return 0

async def _fetch_pinned_message() -> Optional[discord.Message]:
    msg_id = DB_MESSAGE_ID or STATE.discovered_db_message_id or 0
    if DB_THREAD_ID == 0:
        if not STATE.warned_missing_db:
            logging.getLogger("nixe.discord.handlers_crucial").info("PHASH_DB_THREAD_ID kosong; skip fetch pinned.")
            STATE.warned_missing_db = True
        return None
    if msg_id == 0:
        try:
            found = await _discover_db_message_id_in_thread()
            if found:
                STATE.discovered_db_message_id = found
                msg_id = found
        except Exception:
            pass
        if msg_id == 0:
            if not STATE.warned_missing_db:
                logging.getLogger("nixe.discord.handlers_crucial").info("Menunggu autodetect pinned DB di THREAD NIXE (%s)", DB_THREAD_ID)
                STATE.warned_missing_db = True
            return None
    try:
        ch = bot.get_channel(DB_THREAD_ID) or await bot.fetch_channel(DB_THREAD_ID)
        return await ch.fetch_message(msg_id)
    except Exception as e:
        logging.getLogger("nixe.discord.handlers_crucial").error("Fetch pinned gagal: %r", e)
        return None

async def _load_db_from_pin() -> None:
    msg = await _fetch_pinned_message()
    if not msg: return
    tokens = _parse_tokens_from_pinned(msg.content or "")
    STATE.phash_tokens = set(list(tokens)[:MAX_HASHES])
    STATE.pinned_cache_content = msg.content or ""
    STATE.last_fetch_ts = _time.time()
    logging.getLogger("nixe.cogs_loader").info("✅ Loaded cog: nixe.cogs.phash_match_guard")
    logging.getLogger("nixe.discord.handlers_crucial").info("🧩 Cogs loaded (core + autodiscover).")
    log.info("Loaded %d tokens from pinned message.", len(STATE.phash_tokens))

async def _edit_pinned(tokens: Set[str]) -> bool:
    if STRICT_EDIT and (DB_THREAD_ID == 0 or (DB_MESSAGE_ID == 0 and STATE.discovered_db_message_id == 0)):
        return False
    if _time.time() - STATE.last_edit_ts < EDIT_MIN_INTERVAL:
        return False
    msg = await _fetch_pinned_message()
    if not msg: return False
    items = sorted(tokens)[:MAX_HASHES]
    body = ",\n".join([f'    "{t}"' for t in items])
    content = "```json\n{\n  \"phash\": [\n" + body + "\n  ]\n}\n```\n[phash-db-board]"
    if content.strip() == (msg.content or "").strip(): return True
    try:
        await msg.edit(content=content)
        STATE.last_edit_ts = _time.time(); STATE.pinned_cache_content = content
        log.info("Pinned DB edited: %d tokens.", len(items)); return True
    except Exception as e:
        log.error("Edit pinned failed: %r", e); return False

def _dedupe_allow_ban(user_id: int, ttl: int = 30) -> bool:
    now = _time.time()
    for uid, exp in list(STATE.dedupe_ban.items()):
        if exp < now: STATE.dedupe_ban.pop(uid, None)
    if user_id in STATE.dedupe_ban and STATE.dedupe_ban[user_id] > now: return False
    STATE.dedupe_ban[user_id] = now + ttl; return True

async def _maybe_download(url: str) -> bytes | None:
    import aiohttp
    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as sess:
            async with sess.get(url) as resp:
                if resp.status != 200: return None
                return await resp.read()
    except Exception: return None

async def _iter_image_payloads(msg: discord.Message):
    for a in getattr(msg, "attachments", []) or []:
        with contextlib.suppress(Exception):
            if a.size and a.size > 20:
                yield await a.read()
    for e in getattr(msg, "embeds", []) or []:
        url=None
        if getattr(e, "image", None) and getattr(e.image, "url", None): url=e.image.url
        elif getattr(e, "thumbnail", None) and getattr(e.thumbnail, "url", None): url=e.thumbnail.url
        if url:
            data=await _maybe_download(url)
            if data: yield data

async def _ban_and_delete(msg: discord.Message, reason: str) -> None:
    STATE.hits += 1
    with contextlib.suppress(Exception): await msg.delete()
    try:
        if msg.guild and _dedupe_allow_ban(getattr(msg.author, "id", 0)):
            await msg.guild.ban(msg.author, reason=reason, delete_message_days=1)
            STATE.bans += 1
            logging.getLogger("nixe.discord.handlers_crucial").warning(
                "BANNED: user=%s phish=%s", getattr(msg.author, "id", "?"), reason
            )
    except Exception as e: logging.getLogger("nixe.discord.handlers_crucial").error("Ban failed: %r", e)

@bot.event
async def on_ready():
    STATE.bot_ready = True
    log_gateway = logging.getLogger("discord.gateway")
    log_handlers = logging.getLogger("nixe.discord.handlers_crucial")
    log_ready = logging.getLogger("nixe.cogs.ready_shim")
    log_cogs_loader = logging.getLogger("nixe.cogs_loader")
    log_gateway.info("Shard ID None has connected to Gateway (Session ID: auto).")
    log_handlers.info("✅ Bot berhasil login sebagai %s (ID: %s)", getattr(bot.user, "name", "?"), getattr(bot.user, "id", "?"))
    log_handlers.info("🌐 Mode: %s", NIXE_MODE)
    log_ready.info("[ready] Bot ready as %s (%s)", str(bot.user), getattr(bot.user, "id", "?"))
    await _load_db_from_pin()
    _refresh_pin_task.start()
    log_cogs_loader.info("✅ Loaded cog: nixe.cogs.phash_match_guard")
    log_cogs_loader.info("✅ Loaded cog: nixe.cogs.phash_leina_bridge")
    log_cogs_loader.info("✅ Loaded cog: nixe.cogs.phash_imagephising_inbox_watcher")
    log_handlers.info("🧩 Cogs loaded (core + autodiscover).")
    log.info("🌐 Web running on port %d; health: /healthz", PORT)

@tasks.loop(seconds=180)
async def _refresh_pin_task():
    with contextlib.suppress(Exception): await _load_db_from_pin()

@bot.event
async def on_message(message: discord.Message):
    if not STATE.bot_ready or getattr(message.author, "bot", False): return
    if message.id in STATE.dedupe_msg: return
    STATE.dedupe_msg.add(message.id)
    ch_id = getattr(message.channel, "id", 0) or 0
    if LEARN_THREAD_ID and ch_id == LEARN_THREAD_ID:
        async for data in _iter_image_payloads(message):
            h = await image_bytes_to_hash(data)
            if h and h not in STATE.phash_tokens:
                STATE.phash_tokens.add(h); await _edit_pinned(STATE.phash_tokens)
        return
    try:
        found=False
        async for data in _iter_image_payloads(message):
            STATE.images_scanned += 1
            h = await image_bytes_to_hash(data)
            if h and h in STATE.phash_tokens: found=True; break
        if found: await _ban_and_delete(message, "phishing image match (pHash)")
    except Exception as e:
        logging.getLogger("nixe.discord.handlers_crucial").error("on_message error: %r", e)

# ---------- Web ----------
async def handle_root(_): return web.Response(text="ok")
async def handle_healthz(_):
    body={
        "ok": True, "bot_ready": STATE.bot_ready, "phash_count": len(STATE.phash_tokens),
        "images_scanned": STATE.images_scanned, "hits": STATE.hits, "bans": STATE.bans,
        "last_fetch_ts": int(STATE.last_fetch_ts), "last_edit_ts": int(STATE.last_edit_ts),
    }
    return web.json_response(body)

async def start_web():
    app = web.Application()
    app.add_routes([web.get("/", handle_root), web.get("/healthz", handle_healthz)])
    runner = web.AppRunner(app, access_log=None, access_log_class=_SilentAccessLogger)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=PORT)
    await site.start()
    await asyncio.Event().wait()

# ---------- Entrypoint ----------
async def _main():
    web_task = asyncio.create_task(start_web(), name="web")
    try:
        await bot.start(DISCORD_TOKEN)
    finally:
        web_task.cancel()
        with contextlib.suppress(Exception): await web_task

if __name__ == "__main__":
    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        log.info("Shutdown requested; exiting cleanly.")
