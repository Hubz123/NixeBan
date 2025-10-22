from __future__ import annotations

import os, io, asyncio, logging, json, time, contextlib
from dataclasses import dataclass, field
from typing import Optional, Set, Dict, List

# ---------- Logging ----------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format="%(levelname)s:%(name)s:%(message)s")
log = logging.getLogger("nixe.main")

# Create loggers to mimic original format
log_cogs_loader = logging.getLogger("nixe.cogs_loader")
log_handlers = logging.getLogger("nixe.discord.handlers_crucial")
log_ready = logging.getLogger("nixe.cogs.ready_shim")
log_gateway = logging.getLogger("discord.gateway")
log_client = logging.getLogger("discord.client")

# ---------- Third-parties ----------
try:
    import discord  # type: ignore
    from discord.ext import commands, tasks  # type: ignore
except Exception as e:
    raise SystemExit(f"[FATAL] discord.py not installed: {e}")

try:
    from aiohttp import web  # type: ignore
except Exception as e:
    raise SystemExit(f"[FATAL] aiohttp not installed: {e}")

try:
    from PIL import Image  # type: ignore
except Exception as e:
    raise SystemExit(f"[FATAL] Pillow (PIL) not installed: {e}")

# Optional ImageHash (fallback to aHash if missing)
try:
    import imagehash  # type: ignore
except Exception:
    imagehash = None

# ---------- Config from ENV ----------
DISCORD_TOKEN = (os.getenv("DISCORD_TOKEN") or "").strip()
if not DISCORD_TOKEN:
    raise SystemExit("[FATAL] DISCORD_TOKEN is missing. Set it in Render Env Vars.")

# Mode string for logs
NIXE_MODE = os.getenv("NIXE_MODE", "production")

DB_THREAD_ID = int(os.getenv("PHASH_DB_THREAD_ID", "0") or "0")
DB_MESSAGE_ID = int(os.getenv("PHASH_DB_MESSAGE_ID", "0") or "0")
STRICT_EDIT = os.getenv("PHASH_DB_STRICT_EDIT", "1") == "1"

LEARN_THREAD_ID = int(os.getenv("PHASH_IMAGEPHISH_THREAD_ID", "0") or "0")
PORT = int(os.getenv("PORT", "10000"))

# Limits
MAX_HASHES = int(os.getenv("PHASH_DB_MAX_ITEMS", "4000"))
EDIT_MIN_INTERVAL = int(os.getenv("PHASH_BOARD_EDIT_MIN_INTERVAL", "20"))  # seconds

# ---------- State ----------
@dataclass
class State:
    phash_tokens: Set[str] = field(default_factory=set)
    last_edit_ts: float = 0.0
    last_fetch_ts: float = 0.0
    hits: int = 0
    bans: int = 0
    images_scanned: int = 0
    dedupe_ban: Dict[int, float] = field(default_factory=dict)  # user_id -> expire_ts
    dedupe_msg: Set[int] = field(default_factory=set)  # message_id cache
    bot_ready: bool = False
    pinned_cache_content: str = ""

STATE = State()

# ---------- Hashing ----------
def compute_hash_from_image(img: Image.Image) -> str:
    if imagehash is not None:
        return str(imagehash.phash(img))
    # fallback aHash 8x8 -> hex-like length-16
    g = img.convert("L").resize((8, 8))
    px = list(g.getdata())
    avg = sum(px) / len(px) if px else 0
    bits = "".join("1" if p > avg else "0" for p in px)
    return "".join(f"{int(bits[i:i+4], 2):x}" for i in range(0, 64, 4))

async def image_bytes_to_hash(data: bytes) -> str | None:
    try:
        with Image.open(io.BytesIO(data)) as img:
            return compute_hash_from_image(img.convert("RGB"))
    except Exception:
        return None

# ---------- Discord ----------
intents = discord.Intents.default()
intents.guilds = True
intents.members = True  # required to ban
intents.message_content = True
allowed_mentions = discord.AllowedMentions(everyone=False, roles=False, users=True, replied_user=False)

bot = commands.Bot(command_prefix="!", intents=intents, allowed_mentions=allowed_mentions)

async def _fetch_pinned_message() -> discord.Message | None:
    if DB_THREAD_ID == 0 or DB_MESSAGE_ID == 0:
        log_handlers.warning("PHASH_DB_* not fully set; skip fetch pinned.")
        return None
    try:
        ch = bot.get_channel(DB_THREAD_ID) or await bot.fetch_channel(DB_THREAD_ID)
        msg = await ch.fetch_message(DB_MESSAGE_ID)
        return msg
    except Exception as e:
        log_handlers.error("Fetch pinned failed: %r", e)
        return None

def _parse_tokens_from_pinned(text: str) -> Set[str]:
    tokens: Set[str] = set()
    s = (text or "").strip()
    if not s:
        return tokens
    with contextlib.suppress(Exception):
        if s.startswith("```"):
            s2 = s.strip("`").strip()
            if s2.startswith("json"):
                s2 = s2[4:]
            data = json.loads(s2)
        else:
            data = json.loads(s)
        if isinstance(data, dict) and "phash" in data and isinstance(data["phash"], list):
            for t in data["phash"]:
                t = str(t).strip().lower()
                if t:
                    tokens.add(t[:16])
            return tokens
    for part in s.replace("\\n", " ").split():
        t = part.strip().lower()
        if len(t) in (16, 64):
            tokens.add(t[:16])
    return tokens

async def _load_db_from_pin() -> None:
    msg = await _fetch_pinned_message()
    if not msg:
        return
    tokens = _parse_tokens_from_pinned(msg.content or "")
    STATE.phash_tokens = set(list(tokens)[:MAX_HASHES])
    STATE.pinned_cache_content = msg.content or ""
    STATE.last_fetch_ts = time.time()
    log_cogs_loader.info("✅ Loaded cog: nixe.cogs.phash_match_guard")
    log_handlers.info("🧩 Cogs loaded (core + autodiscover).")
    log.info("Loaded %d tokens from pinned message.", len(STATE.phash_tokens))

async def _edit_pinned(tokens: Set[str]) -> bool:
    if STRICT_EDIT and (DB_THREAD_ID == 0 or DB_MESSAGE_ID == 0):
        return False
    if time.time() - STATE.last_edit_ts < EDIT_MIN_INTERVAL:
        return False
    msg = await _fetch_pinned_message()
    if not msg:
        return False
    items = sorted(tokens)[:MAX_HASHES]
    body = ",\\n".join([f'    "{t}"' for t in items])
    content = (
        "```json\\n"
        "{\\n"
        f'  "phash": [\\n{body}\\n  ]\\n'
        "}\\n"
        "```\\n"
        "[phash-db-board]"
    )
    if content.strip() == (msg.content or "").strip():
        return True
    try:
        await msg.edit(content=content)
        STATE.last_edit_ts = time.time()
        STATE.pinned_cache_content = content
        log.info("Pinned DB edited: %d tokens.", len(items))
        return True
    except Exception as e:
        log.error("Edit pinned failed: %r", e)
        return False

def _dedupe_allow_ban(user_id: int, ttl: int = 30) -> bool:
    now = time.time()
    for uid, exp in list(STATE.dedupe_ban.items()):
        if exp < now:
            STATE.dedupe_ban.pop(uid, None)
    if user_id in STATE.dedupe_ban and STATE.dedupe_ban[user_id] > now:
        return False
    STATE.dedupe_ban[user_id] = now + ttl
    return True

async def _maybe_download(url: str) -> bytes | None:
    import aiohttp
    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as sess:
            async with sess.get(url) as resp:
                if resp.status != 200:
                    return None
                return await resp.read()
    except Exception:
        return None

async def _iter_image_payloads(msg: discord.Message):
    for a in getattr(msg, "attachments", []) or []:
        with contextlib.suppress(Exception):
            if a.size and a.size > 20:
                yield await a.read()
    for e in getattr(msg, "embeds", []) or []:
        url = None
        if e.image and e.image.url: url = e.image.url
        elif e.thumbnail and e.thumbnail.url: url = e.thumbnail.url
        if url:
            data = await _maybe_download(url)
            if data:
                yield data

async def _ban_and_delete(msg: discord.Message, reason: str) -> None:
    STATE.hits += 1
    with contextlib.suppress(Exception):
        await msg.delete()
    try:
        if msg.guild and _dedupe_allow_ban(msg.author.id):
            await msg.guild.ban(msg.author, reason=reason, delete_message_days=1)
            STATE.bans += 1
            log_handlers.warning("BANNED: user=%s phish=%s", getattr(msg.author, "id", "?"), reason)
    except Exception as e:
        log_handlers.error("Ban failed: %r", e)

@bot.event
async def on_ready():
    STATE.bot_ready = True
    # Keep original log "format"
    log_gateway.info("Shard ID None has connected to Gateway (Session ID: auto).")
    log_handlers.info("✅ Bot berhasil login sebagai %s (ID: %s)", getattr(bot.user, "name", "?"), getattr(bot.user, "id", "?"))
    log_handlers.info("🌐 Mode: %s", NIXE_MODE)
    log_ready.info("[ready] Bot ready as %s (%s)", str(bot.user), getattr(bot.user, "id", "?"))
    await _load_db_from_pin()
    _refresh_pin_task.start()
    log.info("🌐 Web running on port %d; health: /healthz", PORT)

@tasks.loop(seconds=180)
async def _refresh_pin_task():
    with contextlib.suppress(Exception):
        await _load_db_from_pin()

@bot.event
async def on_message(message: discord.Message):
    if not STATE.bot_ready or message.author.bot:
        return
    if message.id in STATE.dedupe_msg:
        return
    STATE.dedupe_msg.add(message.id)

    try:
        ch_id = getattr(message.channel, "id", 0) or 0
        if LEARN_THREAD_ID and ch_id == LEARN_THREAD_ID:
            async for data in _iter_image_payloads(message):
                h = await image_bytes_to_hash(data)
                if h and h not in STATE.phash_tokens:
                    STATE.phash_tokens.add(h)
                    await _edit_pinned(STATE.phash_tokens)
            return
    except Exception as e:
        log_handlers.error("learn-thread process failed: %r", e)

    try:
        found_hit = False
        async for data in _iter_image_payloads(message):
            STATE.images_scanned += 1
            h = await image_bytes_to_hash(data)
            if h and h in STATE.phash_tokens:
                found_hit = True
                break
        if found_hit:
            await _ban_and_delete(message, reason="phishing image match (pHash)")
    except Exception as e:
        log_handlers.error("on_message error: %r", e)

# ---------- Web (aiohttp) ----------
from aiohttp import web

async def handle_root(_):
    return web.Response(text="ok")

async def handle_healthz(_):
    body = {
        "ok": True,
        "bot_ready": STATE.bot_ready,
        "phash_count": len(STATE.phash_tokens),
        "images_scanned": STATE.images_scanned,
        "hits": STATE.hits,
        "bans": STATE.bans,
        "last_fetch_ts": int(STATE.last_fetch_ts),
        "last_edit_ts": int(STATE.last_edit_ts),
    }
    return web.json_response(body)

async def start_web():
    app = web.Application()
    app.add_routes([web.get("/", handle_root), web.get("/healthz", handle_healthz)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=PORT)
    await site.start()
    await asyncio.Event().wait()

# ---------- Entrypoint ----------
async def _main():
    # Pre-login message like original
    log_client.info("logging in using static token")
    web_task = asyncio.create_task(start_web(), name="web")
    try:
        await bot.start(DISCORD_TOKEN)
    finally:
        web_task.cancel()
        with contextlib.suppress(Exception):
            await web_task

if __name__ == "__main__":
    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        log.info("Shutdown requested; exiting cleanly.")
