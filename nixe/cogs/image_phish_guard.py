import os, io, logging, re, time, pathlib, datetime as dt
from typing import Optional, Set
from discord.ext import commands, tasks
import discord

try:
    from PIL import Image
except Exception:
    Image = None

from nixe.config import load
from nixe.helpers.safeawait import safe_await
from nixe.helpers.discord_locator import find_text_channel, find_thread, ensure_thread

log = logging.getLogger("nixe.image_phish_guard")

appcfg = load()
cfg = appcfg.image

AUTO_CREATE = (os.getenv("AUTO_CREATE_DB_THREAD", "1").strip().lower() in ("1","true","yes","on","y"))
PHISH_DB_CHANNEL_NAME = os.getenv("PHISH_DB_CHANNEL_NAME", "log-botphising")
PHISH_DB_THREAD_NAME  = os.getenv("PHISH_DB_THREAD_NAME",  "imagephising")
MOD_LOG_CHANNEL_NAME  = os.getenv("MOD_LOG_CHANNEL_NAME", appcfg.mod_log_channel_name or "log-botphising")

MAGIC_WEBP  = b"RIFF"
MAGIC_PNG   = b"\x89PNG\r\n\x1a\n"
MAGIC_JPEG  = b"\xff\xd8\xff"

def sniff_mime(b: bytes) -> str:
    if b.startswith(MAGIC_PNG): return "image/png"
    if b.startswith(MAGIC_JPEG): return "image/jpeg"
    if len(b) >= 12 and b[:4] == MAGIC_WEBP and b[8:12] == b"WEBP": return "image/webp"
    return "application/octet-stream"

def _img_to_ahash(img: "Image.Image", size: int=8) -> int:
    g = img.convert("L").resize((size, size))
    px = list(g.getdata())
    avg = sum(px)/len(px)
    bits = 0
    for i, p in enumerate(px):
        if p > avg: bits |= (1 << i)
    return bits

def _img_to_dhash(img: "Image.Image", size: int=8) -> int:
    g = img.convert("L").resize((size+1, size))
    bits = 0
    i = 0
    for y in range(size):
        for x in range(size):
            left  = g.getpixel((x, y))
            right = g.getpixel((x+1, y))
            if right > left: bits |= (1 << i)
            i += 1
    return bits

def _hamming(a: int, b: int) -> int: return (a ^ b).bit_count()
def _hex64(x: int) -> str: return f"{x:016x}"

def _hash_image_bytes(b: bytes) -> Optional[int]:
    if Image is None:
        log.error("Pillow not available; cannot compute image hash")
        return None
    try:
        with Image.open(io.BytesIO(b)) as im:
            im = im.convert("RGB")
            try:
                return _img_to_dhash(im, 8)
            except Exception:
                return _img_to_ahash(im, 8)
    except Exception as e:
        log.warning("Failed to open image for hashing: %s", e)
        return None

class PhashDB:
    def __init__(self):
        self.hashes: Set[int] = set()
        self.loaded_from: str = ""

    def __len__(self): return len(self.hashes)

    def add_hex(self, hx: str):
        hx = hx.strip().lower().replace("0x", "")
        try:
            self.hashes.add(int(hx, 16))
        except Exception:
            pass

    def match(self, h: int, strict: int, lenient: int):
        # returns (verdict: "ban"/"quarantine"/None, dist, ref)
        best = None
        for ref in self.hashes:
            d = _hamming(h, ref)
            if best is None or d < best[0]:
                best = (d, ref)
        if not best: return (None, None, None)
        d, ref = best
        if d <= strict:  return ("ban",        d, ref)
        if d <= lenient: return ("quarantine", d, ref)
        return (None, d, ref)

    @staticmethod
    def parse_from_text(txt: str) -> "PhashDB":
        db = PhashDB()
        for m in re.finditer(r"\b([0-9a-fA-F]{16})\b", txt):
            db.add_hex(m.group(1))
        for m in re.finditer(r"phash\s*[:=]\s*([0-9a-fA-F]{16})", txt, re.I):
            db.add_hex(m.group(1))
        return db

class ImagePhishGuard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = PhashDB()
        self._start_ts = time.time()
        self._last_ban_ts = 0.0
        self._ban_window = []  # timestamps of bans within last 10 min
        self.refresh_db_task.start()

    def cog_unload(self):
        self.refresh_db_task.cancel()

    @tasks.loop(minutes=10.0)
    async def refresh_db_task(self):
        try:
            loaded = await self._load_db()
            if loaded:
                log.info("[db] loaded %d entries from %s", len(self.db), self.db.loaded_from)
        except Exception as e:
            log.exception("[db] refresh error: %s", e)

    @refresh_db_task.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()

    async def _load_db(self) -> bool:
        # Resolve parent channel by ID or NAME
        channel: Optional[discord.TextChannel] = None
        thread: Optional[discord.Thread] = None

        if cfg.db_channel_id:
            channel = self.bot.get_channel(cfg.db_channel_id)  # type: ignore

        if channel is None and PHISH_DB_CHANNEL_NAME:
            for g in self.bot.guilds:
                ch = await find_text_channel(g, channel_name=PHISH_DB_CHANNEL_NAME)
                if ch:
                    channel = ch
                    break

        if channel is None:
            return False

        # Resolve thread by ID or NAME; create if allowed
        if cfg.db_thread_id:
            try:
                thread = self.bot.get_thread(cfg.db_thread_id)  # type: ignore
            except Exception:
                thread = None

        if thread is None and PHISH_DB_THREAD_NAME:
            thread = await find_thread(channel.guild, thread_name=PHISH_DB_THREAD_NAME, parent_hint=channel)

        created = False
        if thread is None and AUTO_CREATE:
            thread, created = await ensure_thread(channel.guild, thread_name=PHISH_DB_THREAD_NAME or "imagephising", parent=channel)

        if thread is None:
            return False

        # Load DB from thread pins/history
        target = thread
        texts = []
        try:
            pins = await target.pins()
        except Exception:
            pins = []

        if pins:
            for m in pins:
                texts.append(m.content or "")
                # also parse small text attachments
                for a in m.attachments:
                    try:
                        if a.size and a.size < 2_000_000 and (a.content_type or "").startswith("text/"):
                            b = await a.read()
                            texts.append(b.decode("utf-8", "ignore"))
                    except Exception:
                        pass
        else:
            try:
                async for m in target.history(limit=200):
                    texts.append(m.content or "")
            except Exception as e:
                log.warning("thread history read failed: %s", e)

        merged = "\n".join(texts)
        db = PhashDB.parse_from_text(merged)
        if len(db) > 0:
            self.db = db
            self.db.loaded_from = f"thread:{target.id}"

            # If newly created and empty DB, pin a template to guide admins
            if created and not texts:
                try:
                    tmpl_path = pathlib.Path("templates/pinned_phash_db_template.txt")
                    content = tmpl_path.read_text(encoding="utf-8") if tmpl_path.exists() else "phash: 0123456789abcdef"
                    msg = await target.send(content)
                    try:
                        await msg.pin()
                    except Exception:
                        pass
                except Exception as e:
                    log.warning("Failed to pin template to new thread: %s", e)

            return True

        return False

    def _should_skip_member(self, member: discord.Member) -> bool:
        if member is None: return True
        if member.guild_permissions.administrator: return True
        if cfg.whitelist_roles and any((rid in cfg.whitelist_roles) for rid in [r.id for r in member.roles]): return True
        return False

    def _warmup(self) -> bool:
        return (time.time() - self._start_ts) < cfg.warmup_seconds

    def _ban_ceiling_hit(self) -> bool:
        now = time.time()
        self._ban_window = [t for t in self._ban_window if now - t < 600]
        return len(self._ban_window) >= cfg.ban_ceiling_per_10min

    def _ban_cooldown_hit(self) -> bool:
        return (time.time() - self._last_ban_ts) < cfg.ban_cooldown_seconds

    def _account_is_new(self, member: discord.Member) -> bool:
        try:
            age_days = (dt.datetime.utcnow() - member.created_at.replace(tzinfo=None)).days
            return age_days <= cfg.ban_only_newer_than_days
        except Exception:
            return True

    async def _modlog(self, guild: discord.Guild, text: str):
        try:
            app = load()
            ch = None
            if app.mod_log_channel_id:
                try:
                    ch = guild.get_channel(app.mod_log_channel_id) or (await guild.fetch_channel(app.mod_log_channel_id))
                except Exception:
                    ch = None
            if ch is None and (app.mod_log_channel_name or MOD_LOG_CHANNEL_NAME):
                name = (app.mod_log_channel_name or MOD_LOG_CHANNEL_NAME).lower()
                for c in guild.text_channels:
                    if c.name.lower() == name:
                        ch = c
                        break
            if ch:
                await ch.send(text)
        except Exception:
            pass

    async def _timeout(self, member: discord.Member, minutes: int, reason: str):
        try:
            if hasattr(member, "timeout"):
                until = dt.timedelta(minutes=minutes)
                await member.timeout(until=dt.datetime.utcnow()+until, reason=reason)
                return True
        except Exception as e:
            log.warning("timeout failed: %s", e)
        return False

    async def _act(self, message: discord.Message, verdict: str, dist: int, hhex: str):
        if self._warmup():
            await self._modlog(message.guild, f"[warmup] {message.author} ({message.author.id}) match {verdict} dist={dist} hash={hhex}")
            log.info("[warmup] would %s %s dist=%d", verdict, message.author.id, dist)
            return
        if cfg.enable_autoban is False:
            await self._modlog(message.guild, f"[dryrun] {message.author} ({message.author.id}) match {verdict} dist={dist} hash={hhex}")
            log.info("[dryrun] would %s %s dist=%d", verdict, message.author.id, dist)
            return

        if verdict == "ban":
            # extra rails
            if self._ban_cooldown_hit() or self._ban_ceiling_hit() or not self._account_is_new(message.author):
                verdict = "quarantine"

        if verdict == "ban":
            if not message.guild.me.guild_permissions.ban_members:
                await self._modlog(message.guild, f"[ban-skip] missing Ban Members perms for {message.author}")
                return
            try:
                await message.author.ban(reason=f"image-phish match (dist={dist}, hash={hhex})",
                                         delete_message_days=cfg.delete_message_days)
                self._last_ban_ts = time.time()
                self._ban_window.append(self._last_ban_ts)
                await self._modlog(message.guild, f"[ban] {message.author} ({message.author.id}) dist={dist} hash={hhex}")
                log.info("[ban] user=%s dist=%d hash=%s", message.author.id, dist, hhex)
                return
            except Exception as e:
                log.exception("ban failed: %s", e)
                verdict = "quarantine"

        if verdict == "quarantine":
            ok = await self._timeout(message.author, cfg.quarantine_minutes, f"image-phish match (dist={dist})")
            await self._modlog(message.guild, f"[quarantine {'OK' if ok else 'FAIL'}] {message.author} ({message.author.id}) dist={dist} hash={hhex}")
            return

    async def _check_bytes(self, b: bytes, message: discord.Message) -> Optional[str]:
        mime = sniff_mime(b)
        if not mime.startswith("image/"): return None
        h = _hash_image_bytes(b)
        if h is None: return None
        verdict, dist, ref = self.db.match(h, cfg.phash_distance_strict, cfg.phash_distance_lenient)
        if verdict:
            await self._act(message, verdict, dist, _hex64(h))
        return verdict

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        try:
            if message.author.bot or message.guild is None: return
            if self._should_skip_member(message.author): return
            for a in (message.attachments or []):
                if a.size and a.size <= 10_000_000:
                    b = await a.read()
                    verdict = await self._check_bytes(b, message)
                    if verdict:
                        break
        except Exception as e:
            log.exception("[image-guard] on_message error: %s", e)

    @commands.command(name="phishguard")
    @commands.has_permissions(manage_guild=True)
    async def phishguard_cmd(self, ctx: commands.Context, sub: str = "status"):
        if sub == "reload":
            ok = await self._load_db()
            await ctx.reply(f"Reload DB: {'OK' if ok else 'NO-OP'}; entries={len(self.db)}; from={self.db.loaded_from}")
            return
        await ctx.reply(
            f"status: entries={len(self.db)} from={self.db.loaded_from or 'n/a'}  "
            f"strict<={cfg.phash_distance_strict} lenient<={cfg.phash_distance_lenient} "
            f"warmup={cfg.warmup_seconds}s ban_cooldown={cfg.ban_cooldown_seconds}s "
            f"ceiling/10m={cfg.ban_ceiling_per_10min}"
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(ImagePhishGuard(bot))
