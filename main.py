from __future__ import annotations
import os, io, asyncio, logging, json, time as _time, contextlib, importlib, pkgutil, inspect
from typing import Optional, Set, Dict
from dataclasses import dataclass, field
# ---------- Logging ----------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=LOG_LEVEL, format="%(levelname)s:%(name)s:%(message)s")
log = logging.getLogger("nixe.main")
class _OnceFilter(logging.Filter):
    def __init__(self):
        super().__init__(); self.seen=set(); self.needles={
            "PyNaCl is not installed, voice will NOT be supported",
            "logging in using static token",
        }
    def filter(self, record):
        msg = record.getMessage(); hit=None
        for n in self.needles:
            if n in msg: hit=n; break
        if hit is None: return True
        if hit in self.seen: return False
        self.seen.add(hit); return True
logging.getLogger("discord.client").addFilter(_OnceFilter())
try:
    from aiohttp.web_log import AccessLogger
    class _SilentAccessLogger(AccessLogger):
        def log(self, request, response, time): return
    _aio = logging.getLogger("aiohttp.access")
    for h in list(_aio.handlers): _aio.removeHandler(h)
    _aio.propagate = False; _aio.setLevel(logging.CRITICAL); _aio.disabled = True
except Exception: pass
# ---------- Third-parties ----------
import discord
from discord.ext import commands, tasks
from aiohttp import web
from PIL import Image
try:
    import imagehash
except Exception:
    imagehash = None
# ---------- Module IDs ----------
from nixe.config_ids import LOG_BOTPHISHING as LOG_CH, TESTBAN_CHANNEL_ID, THREAD_IMAGEPHISH
from nixe.config_phash import (
    PHASH_DB_THREAD_ID as DB_THREAD_ID,
    PHASH_DB_MESSAGE_ID as DB_MESSAGE_ID,
    PHASH_DB_STRICT_EDIT as STRICT_EDIT,
    PHASH_DB_MAX_ITEMS as MAX_HASHES,
    PHASH_BOARD_EDIT_MIN_INTERVAL as EDIT_MIN_INTERVAL,
    BAN_DRY_RUN, BAN_DELETE_SECONDS, PHASH_HAMMING_MAX
)
# ---------- Bot ----------
DISCORD_TOKEN = (os.getenv("DISCORD_TOKEN") or "").strip()
if not DISCORD_TOKEN: raise SystemExit("[FATAL] DISCORD_TOKEN missing")
PORT = int(os.getenv("PORT", "10000"))
intents = discord.Intents.default()
intents.guilds=True; intents.members=True; intents.message_content=True
bot = commands.Bot(command_prefix="!", intents=intents, allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=True, replied_user=False))
# ---------- State ----------
@dataclass
class State:
    phash_tokens: Set[str] = field(default_factory=set)
    last_edit_ts: float = 0.0
    last_fetch_ts: float = 0.0
    images_scanned: int = 0
    hits: int = 0
    bans: int = 0
    dedupe_ban: Dict[int, float] = field(default_factory=dict)
    seen_msg_ids: Set[int] = field(default_factory=set)
    pinned_cache_content: str = ""
    discovered_db_message_id: int = 0
STATE = State()
# ---------- Helpers ----------
def compute_hash_from_image(img: Image.Image) -> str:
    if imagehash is not None:
        return str(imagehash.phash(img))
    g = img.convert("L").resize((8,8))
    px = list(g.getdata()); avg = sum(px)/len(px) if px else 0
    bits = "".join("1" if p > avg else "0" for p in px)
    return "".join(f"{int(bits[i:i+4],2):x}" for i in range(0,64,4))
async def image_bytes_to_hash(data: bytes) -> Optional[str]:
    try:
        with Image.open(io.BytesIO(data)) as img:
            return compute_hash_from_image(img.convert("RGB"))
    except Exception: return None
def _parse_tokens_from_pinned(text: str) -> Set[str]:
    tokens: Set[str] = set(); s = (text or "").strip()
    if not s: return tokens
    with contextlib.suppress(Exception):
        t = s
        if t.startswith("```"):
            t = t.strip("`").strip()
            if t.startswith("json"): t = t[4:]
        data = json.loads(t)
        if isinstance(data, dict) and isinstance(data.get("phash"), list):
            for x in data["phash"]:
                y = str(x).strip().lower()
                if y: tokens.add(y[:16])
            return tokens
    for part in s.replace("\n"," ").split():
        y = part.strip().lower()
        if len(y) in (16,64): tokens.add(y[:16])
    return tokens
def _looks_like_phash_db(text: str) -> bool:
    if not text: return False
    s = text.strip().lower()
    if "[phash-db-board]" in s: return True
    with contextlib.suppress(Exception):
        t = s
        if t.startswith("```"): t = t.strip("`").strip()
        if t.startswith("json"): t = t[4:]
        data = json.loads(t)
        return isinstance(data, dict) and "phash" in data
    return len(_parse_tokens_from_pinned(s)) >= 1
async def _discover_db_message_id_in_thread() -> int:
    if DB_THREAD_ID == 0: return 0
    try:
        ch = bot.get_channel(DB_THREAD_ID) or await bot.fetch_channel(DB_THREAD_ID)
    except Exception:
        return 0
    with contextlib.suppress(Exception):
        for m in await ch.pins():
            if _looks_like_phash_db(getattr(m, "content", "")): return int(m.id)
    with contextlib.suppress(Exception):
        async for m in ch.history(limit=500):
            if _looks_like_phash_db(getattr(m, "content", "")): return int(m.id)
    return 0
async def _fetch_pinned_message() -> Optional[discord.Message]:
    msg_id = DB_MESSAGE_ID or STATE.discovered_db_message_id or 0
    if DB_THREAD_ID == 0: return None
    if msg_id == 0:
        found = await _discover_db_message_id_in_thread()
        if found: STATE.discovered_db_message_id = found; msg_id = found
        else: return None
    try:
        ch = bot.get_channel(DB_THREAD_ID) or await bot.fetch_channel(DB_THREAD_ID)
        return await ch.fetch_message(msg_id)
    except Exception:
        return None
async def _load_db_from_pin(reason: str = "refresh") -> None:
    msg = await _fetch_pinned_message()
    if not msg: return
    new_content = msg.content or ""
    if new_content.strip() == STATE.pinned_cache_content.strip():
        STATE.last_fetch_ts = _time.time(); return
    tokens = _parse_tokens_from_pinned(new_content)
    prev = len(STATE.phash_tokens)
    STATE.phash_tokens = set(list(tokens)[:5000])
    STATE.pinned_cache_content = new_content
    STATE.last_fetch_ts = _time.time()
    log.info("🔄 pHash board updated: %d tokens (was %d) — reason=%s", len(STATE.phash_tokens), prev, reason)
async def _edit_pinned(tokens: Set[str]) -> bool:
    if (DB_THREAD_ID == 0 or (DB_MESSAGE_ID == 0 and STATE.discovered_db_message_id == 0)):
        return False
    if _time.time() - STATE.last_edit_ts < 180: return False
    msg = await _fetch_pinned_message()
    if not msg: return False
    items = sorted(set(tokens))[:5000]
    content_json = json.dumps({"phash": items}, ensure_ascii=False, indent=2)
    content = "```json\n" + content_json + "\n```\n[phash-db-board]"
    if content.strip() == (msg.content or "").strip(): return True
    try:
        await msg.edit(content=content)
        STATE.last_edit_ts = _time.time(); STATE.pinned_cache_content = content
        log.info("Pinned DB edited: %d tokens.", len(items)); return True
    except Exception as e:
        log.error("Edit pinned failed: %r", e); return False
async def _maybe_download(url: str) -> Optional[bytes]:
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
def _dedupe_allow_ban(user_id: int, ttl: int = 30) -> bool:
    now = _time.time()
    for uid, exp in list(STATE.dedupe_ban.items()):
        if exp < now: STATE.dedupe_ban.pop(uid, None)
    if user_id in STATE.dedupe_ban and STATE.dedupe_ban[user_id] > now: return False
    STATE.dedupe_ban[user_id] = now + ttl; return True
from nixe.cogs.ban_embed_leina import build_banned_embed
async def _ban_and_delete(msg: discord.Message, reason: str) -> None:
    STATE.hits += 1
    with contextlib.suppress(Exception): await msg.delete()
    banned_ok=False
    try:
        if msg.guild and _dedupe_allow_ban(getattr(msg.author, "id", 0)):
            await msg.guild.ban(msg.author, reason=reason, delete_message_days=1)
            STATE.bans += 1; banned_ok=True
    except Exception as e:
        logging.getLogger("nixe.discord.handlers_crucial").error("Ban failed: %r", e)
    try:
        ch = msg.guild.get_channel(LOG_CH) or await bot.fetch_channel(LOG_CH)
        if ch and isinstance(ch, (discord.TextChannel, discord.Thread)):
            evidence=None
            if msg.attachments: evidence = msg.attachments[0].url
            elif msg.embeds and getattr(msg.embeds[0], "image", None):
                evidence = getattr(msg.embeds[0].image, "url", None)
            emb = build_banned_embed(target=msg.author, moderator=msg.guild.me, reason=reason, evidence_url=evidence)
            await ch.send(embed=emb, allowed_mentions=discord.AllowedMentions.none())
    except Exception: pass
    if banned_ok:
        logging.getLogger("nixe.discord.handlers_crucial").warning("BANNED user=%s reason=%s", getattr(msg.author,"id","?"), reason)
async def _autoload_all_cogs(bot: commands.Bot):
    names = []
    try:
        pkg = importlib.import_module("nixe.cogs")
    except Exception as e:
        logging.getLogger("nixe.cogs_loader").error("Cannot import nixe.cogs: %r", e); return names
    for m in pkgutil.iter_modules(pkg.__path__, pkg.__name__ + "."):
        modname = m.name
        base = modname.rsplit(".", 1)[-1]
        if base.startswith("_") or base in ("__init__",): continue
        try:
            mod = importlib.import_module(modname)
            setup = getattr(mod, "setup", None) or getattr(mod, "setup_legacy", None)
            if setup is None: continue
            if inspect.iscoroutinefunction(setup): await setup(bot)
            else: setup(bot)
            names.append(modname)
        except Exception as e:
            logging.getLogger("nixe.cogs_loader").error("Failed to load %s: %r", modname, e)
    logging.getLogger("nixe.cogs_loader").info("✅ Autoloaded %d cogs", len(names)); return names
@bot.event
async def on_ready():
    logging.getLogger("nixe.discord.handlers_crucial").info("✅ Bot berhasil login sebagai %s (ID: %s)", getattr(bot.user, "name", "?"), getattr(bot.user, "id", "?"))
    logging.getLogger("nixe.discord.handlers_crucial").info("🌐 Mode: %s", os.getenv("NIXE_MODE", "production"))
    await _load_db_from_pin("startup"); _refresh_pin_task.start(); await _autoload_all_cogs(bot)
    log.info("🌐 Web service akan start pada port %d; health: /healthz", PORT)
@tasks.loop(seconds=180)
async def _refresh_pin_task(): await _load_db_from_pin("refresh")
@bot.event
async def on_message(message: discord.Message):
    if getattr(message.author, "bot", False): return
    if message.id in STATE.seen_msg_ids:
        await bot.process_commands(message); return
    STATE.seen_msg_ids.add(message.id)
    ch_id = getattr(message.channel, "id", 0) or 0
    if THREAD_IMAGEPHISH and ch_id == THREAD_IMAGEPHISH:
        try:
            async for data in _iter_image_payloads(message):
                h = await image_bytes_to_hash(data)
                if h and h not in STATE.phash_tokens:
                    STATE.phash_tokens.add(h); await _edit_pinned(STATE.phash_tokens)
        except Exception as e:
            logging.getLogger("nixe.discord.handlers_crucial").error("learn-thread error: %r", e)
        finally:
            await bot.process_commands(message); return
    try:
        match=False
        async for data in _iter_image_payloads(message):
            STATE.images_scanned += 1
            h = await image_bytes_to_hash(data)
            if h:
                if 0 <= 0:
                    if h in STATE.phash_tokens: match=True
                if match: break
        if match: await _ban_and_delete(message, "phishing image match (pHash)")
    except Exception as e:
        logging.getLogger("nixe.discord.handlers_crucial").error("on_message error: %r", e)
    finally:
        await bot.process_commands(message)
async def handle_root(_): return web.Response(text="ok")
async def handle_healthz(_):
    body = {"ok": True, "phash_count": len(STATE.phash_tokens), "images_scanned": STATE.images_scanned, "hits": STATE.hits, "bans": STATE.bans,
            "last_fetch_ts": int(STATE.last_fetch_ts), "last_edit_ts": int(STATE.last_edit_ts)}
    return web.json_response(body)
async def start_web():
    app = web.Application()
    app.add_routes([web.get("/", handle_root), web.get("/healthz", handle_healthz)])
    try:
        from aiohttp.web_log import AccessLogger
        class _SilentAccessLogger(AccessLogger):
            def log(self, request, response, time): return
        runner = web.AppRunner(app, access_log=None, access_log_class=_SilentAccessLogger)
    except Exception:
        runner = web.AppRunner(app)
    await runner.setup(); site = web.TCPSite(runner, host="0.0.0.0", port=PORT); await site.start(); await asyncio.Future()
async def _main():
    web_task = asyncio.create_task(start_web(), name="web")
    try:
        await bot.start(DISCORD_TOKEN)
    finally:
        web_task.cancel()
        with contextlib.suppress(BaseException):
            await web_task
if __name__ == "__main__":
    try:
        asyncio.run(_main())
    except BaseException as e:
        logging.getLogger("nixe.main").error("Top-level suppressed: %r", e)
