"""
Gacha Luck Guard (NIXE)
-----------------------
Tujuan:
- Menghapus post "hasil gacha/lucky pull" yang salah tempat di channel ngobrol tertentu.
- Mengarahkan user untuk post di channel gacha (#garem-moment).
- Tidak pernah melakukan ban/kick/mute — hanya delete pesan + mention arahan.
- Semua konfigurasi di modul (tanpa ENV), aman untuk Render free plan.
- Anti false-positive via skor teks + deteksi gambar berbasis dHash/pHash prototipe.

Cara pakai ringkas:
1) Taruh file ini: nixe/cogs/gacha_luck_guard.py
2) Taruh beberapa screenshot contoh banner result di: data/gacha_phash/prototypes/
3) Pastikan bot punya izin Manage Messages di channel yang dijaga.
4) Tambahkan "nixe.cogs.gacha_luck_guard" ke loader/DEFAULT_COGS jika diperlukan.

Catatan:
- Discord tidak mendukung "memindahkan" pesan user. Kita hanya bisa menghapus dan memberi arahan.
- dHash/pHash di sini sederhana; cukup akurat untuk pola UI banner populer. Atur ambang hamming jika perlu.
"""

from __future__ import annotations

import re
import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Set, Optional

import discord
from discord.ext import commands

# =====================
# KONFIGURASI DI MODUL
# =====================
@dataclass
class GachaGuardConfig:
    # Channel yang DIPERBOLEHKAN untuk post hasil gacha
    allowed_gacha_channel_ids: Set[int]

    # Channel yang DIJAGA (hanya di sini rules berlaku):
    # -> jika terdeteksi gambar hasil gacha, hapus & arahkan
    guard_channel_ids: Set[int] = None  # contoh: {886534544688308265}

    # (Tidak dipakai untuk hapus SEMUA gambar; dijaga agar gambar umum tetap boleh)
    blocked_image_channel_ids: Set[int] = None

    # Notice publik singkat di channel salah (auto delete)
    send_public_notice: bool = True
    public_notice_ttl: int = 8  # detik

    # Role yang di-bypass (misal moderator) — opsional
    bypass_role_ids: Set[int] = None  # contoh: {987654321012345678}

    # Opsi mirror ke channel gacha (OFF bawaan, demi privasi)
    mirror_to_allowed: bool = False

    # Channel untuk logging kejadian (opsional)
    log_channel_id: Optional[int] = None

    # Deteksi: perlu attachment/embeds image untuk diproses?
    require_image_hint: bool = True

    # Skor teks minimum agar dianggap gacha (semakin tinggi = semakin ketat)
    score_threshold: int = 4

    # Deteksi gambar berbasis dHash/pHash prototipe
    phash_enabled: bool = True
    phash_db_dir: Path = Path("data/gacha_phash/prototypes")
    phash_cache_path: Path = Path("data/gacha_phash/db.json")
    phash_hamming_threshold: int = 10  # 7–12 umum

    # Channel tujuan (untuk pesan arahan)
    redirect_channel_id: Optional[int] = 1293200121063936052  # #garem-moment
    redirect_channel_name: Optional[str] = "garem-moment"


CONFIG = GachaGuardConfig(
    allowed_gacha_channel_ids={
        1293200121063936052,  # channel khusus share lucky pull (boleh) -> #garem-moment
    },
    guard_channel_ids={
        886534544688308265,   # chat channel: gambar umum boleh, GAMBAR GACHA dihapus
    },
    blocked_image_channel_ids=set(),  # tidak dipakai
    bypass_role_ids=set(),
    require_image_hint=True,       # butuh ada gambar untuk diproses
    score_threshold=4,             # ketat untuk teks
    phash_enabled=True,            # aktifkan deteksi gambar berbasis pHash/dHash
    phash_hamming_threshold=10,    # semakin kecil = semakin ketat (7–12 umum)
    redirect_channel_id=1293200121063936052,
    redirect_channel_name="garem-moment",
)


# =====================
# HEURISTIK DETEKSI
# =====================
STAR_RE = re.compile(r"[\u2B50\uFE0F\u2605\u2606]|⭐|🌟")
MULTI_PULL_RE = re.compile(r"\b(10|20|30|50|100)\s*(pull|warp|wish)(es)?\b", re.I)
PITY_RE = re.compile(r"\b(soft\s*)?pity\s*(\d+)?\b", re.I)
RANK_RE = re.compile(r"\b(SSR|UR|SR|R\s?[1-5]|C\s?[1-6]|5\s?\*|6\s?\*)\b", re.I)

GACHA_TERMS = (
    "gacha", "wish", "warp", "banner", "rate up", "limited", "standard",
    "pull", "multi", "single pull", "lucky pull", "early pity",
    # Indonesia
    "narik", "tarik", "hasil gacha", "bintang 5", "bintang lima",
)

GAME_TERMS = (
    # Umum
    "limited banner", "event banner", "off-banner", "standard banner",
    # Wuthering Waves
    "wuthering waves", "wuwa", "yinlin", "jinhsi", "jiyan", "encore", "calcharo", "lingyang", "rover",
    # Genshin Impact & ZZZ
    "genshin", "genshin impact", "nahida", "raiden", "hutao", "kazuha", "ayaka", "zzz", "zenless zone zero",
    # Honkai: Star Rail & HI3
    "hsr", "honkai star rail", "jingliu", "dan heng il", "bronya", "hi3", "honkai impact",
    # Reverse: 1999
    "reverse: 1999", "r1999", "regulus", "centurion", "melania", "an-an lee",
    # Punishing: Gray Raven
    "pgr", "punishing gray raven", "lucia", "nanami", "rosetta",
    # Blue Archive
    "blue archive", "ba", "araka", "wakamo", "ny", "fes",
    # Arknights
    "arknights", "ak", "surtr", "ch'en", "skadi", "exusiai",
    # Nikke
    "nikke", "goddess of victory nikke", "scarlet", "modernia",
    # FGO
    "fgo", "fate grand order", "sq", "saint quartz", "ssr",
    # Others
    "epic seven", "e7", "alchemystars", "alchemy stars", "azur lane", "counter:side", "another eden",
    "afk arena", "summoners war", "granblue fantasy", "umamusume", "path to nowhere", "guardian tales",
    "tower of fantasy", "tof", "db legends", "dokkan", "one piece treasure cruise", "optc",
)

NEGATIVE_HINTS = (
    "build", "guide", "panduan", "tips", "artifact", "relic", "team comp", "tier list", "schedule",
)

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


def _count_bulks(content: str, terms: List[str]) -> int:
    c = 0
    low = content.lower()
    for t in terms:
        if t in low:
            c += 1
    return c


def _has_image_hint(msg: discord.Message) -> bool:
    # Attachments image
    for a in msg.attachments:
        if (a.content_type and a.content_type.startswith("image/")) or any(a.filename.lower().endswith(ext) for ext in IMAGE_EXTS):
            return True
    # Embeds w/ image/thumbnail
    for e in msg.embeds:
        if (e.image and getattr(e.image, 'url', None)) or (e.thumbnail and getattr(e.thumbnail, 'url', None)):
            return True
    return False


def _gacha_score(msg: discord.Message) -> int:
    content = msg.content or ""
    score = 0

    # Bintang berulang (⭐ banyak)
    stars = len(STAR_RE.findall(content))
    if stars >= 3:
        score += 2

    # Istilah gacha umum & game-spesifik
    score += _count_bulks(content, list(GACHA_TERMS))
    score += min(2, _count_bulks(content, list(GAME_TERMS)))  # batasi

    # Pola numerik khas
    if MULTI_PULL_RE.search(content):
        score += 2
    if PITY_RE.search(content):
        score += 1
    if RANK_RE.search(content):
        score += 2

    # Penalti jika terlihat obrolan teknis
    score -= _count_bulks(content, list(NEGATIVE_HINTS))

    # Bonus jika ada gambar
    if _has_image_hint(msg):
        score += 1

    return score


class GachaLuckGuard(commands.Cog):
    """Cog yang menghapus gambar hasil gacha di channel ngobrol tertentu dan mengarahkan user."""

    def __init__(self, bot: commands.Bot, cfg: GachaGuardConfig):
        self.bot = bot
        self.cfg = cfg
        # lazy init phash db, bila perlu

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Abaikan: DM/bot/tidak ada guild
        if not message.guild or message.author.bot:
            return

        # Bypass roles (opsional)
        if self.cfg.bypass_role_ids:
            author_roles = {r.id for r in getattr(message.author, 'roles', [])}
            if author_roles & self.cfg.bypass_role_ids:
                return

        # Izinkan di channel gacha
        if message.channel.id in self.cfg.allowed_gacha_channel_ids:
            return

        # GUARD MODE: hanya aktif di channel tertentu
        if self.cfg.guard_channel_ids and message.channel.id in self.cfg.guard_channel_ids:
            if _has_image_hint(message):
                score = _gacha_score(message)
                is_gacha_img = await self._looks_like_gacha_banner(message)
                if (score >= self.cfg.score_threshold) or is_gacha_img:
                    await self._delete_and_ping_redirect(message)
            return

    # ---------------
    # AKSI & UTIL
    # ---------------
    async def _looks_like_gacha_banner(self, message: discord.Message) -> bool:
        """Deteksi kasar screenshot banner gacha via dHash/pHash terhadap prototipe."""
        if not self.cfg.phash_enabled:
            return False
        try:
            from PIL import Image
        except Exception:
            return False

        # Lazy init cache
        if not hasattr(self, "_phash_db"):
            self._phash_db = self._load_phash_db()

        # Periksa beberapa attachment gambar saja
        checked = 0
        for a in message.attachments:
            if checked >= 3:
                break
            if not ((a.content_type and a.content_type.startswith("image/")) or any(a.filename.lower().endswith(ext) for ext in IMAGE_EXTS)):
                continue
            try:
                data = await a.read()
                from io import BytesIO
                img = Image.open(BytesIO(data)).convert("L")
                d = self._dhash(img)
                for name, proto in self._phash_db.items():
                    if self._hamming(d, proto) <= self.cfg.phash_hamming_threshold:
                        return True
                checked += 1
            except Exception:
                continue
        return False

    def _load_phash_db(self) -> dict:
        # Bangun DB dari folder prototipe; cache JSON {name: int_hash}
        db = {}
        try:
            self.cfg.phash_db_dir.mkdir(parents=True, exist_ok=True)
            if self.cfg.phash_cache_path.exists():
                with self.cfg.phash_cache_path.open("r", encoding="utf-8") as f:
                    db = json.load(f)
            # Scan folder untuk file gambar baru
            for p in self.cfg.phash_db_dir.glob("**/*"):
                if p.suffix.lower() in IMAGE_EXTS:
                    key = str(p.relative_to(self.cfg.phash_db_dir)).replace("\\", "/")
                    if key not in db:
                        try:
                            from PIL import Image
                            img = Image.open(p).convert("L")
                            db[key] = self._dhash(img)
                        except Exception:
                            pass
            # Simpan cache
            self.cfg.phash_cache_path.parent.mkdir(parents=True, exist_ok=True)
            with self.cfg.phash_cache_path.open("w", encoding="utf-8") as f:
                json.dump(db, f)
        except Exception:
            pass
        return db

    def _dhash(self, img, size=8) -> int:
        """Difference hash sederhana (64-bit)."""
        w, h = size + 1, size
        img = img.resize((w, h))
        px = list(img.getdata())
        bits = 0
        for y in range(h):
            row = px[y * w:(y + 1) * w]
            for x in range(w - 1):
                bits = (bits << 1) | (1 if row[x] > row[x + 1] else 0)
        return bits

    def _hamming(self, a: int, b: int) -> int:
        return (a ^ b).bit_count()

    def _dest_mention(self, guild: discord.Guild) -> str:
        # ID → mention
        if self.cfg.redirect_channel_id:
            ch = guild.get_channel(self.cfg.redirect_channel_id)
            if isinstance(ch, (discord.TextChannel, discord.Thread, discord.VoiceChannel, discord.StageChannel, discord.ForumChannel)):
                return ch.mention
        # Name → cari dan mention bila ada
        if self.cfg.redirect_channel_name:
            for ch in guild.channels:
                if isinstance(ch, discord.TextChannel) and ch.name == self.cfg.redirect_channel_name:
                    return ch.mention
            return f"#{self.cfg.redirect_channel_name}"
        return "#garem-moment"

    async def _delete_and_ping_redirect(self, message: discord.Message):
        dest = self._dest_mention(message.guild)

        # Opsional mirror (OFF by default)
        if self.cfg.mirror_to_allowed and self.cfg.allowed_gacha_channel_ids:
            try:
                dest_id = next(iter(self.cfg.allowed_gacha_channel_ids))
                dest_ch = message.guild.get_channel(dest_id)
                if isinstance(dest_ch, (discord.TextChannel, discord.Thread)):
                    files = []
                    for a in message.attachments:
                        try:
                            files.append(await a.to_file())
                        except Exception:
                            pass
                    content = f"**Mirror dari {message.author.mention}** (salah channel)\n\n{message.content}".strip()
                    await dest_ch.send(content=content if content else None, files=files if files else None)
            except Exception:
                pass

        # Hapus pesan (jika punya izin)
        try:
            await message.delete()
        except discord.Forbidden:
            pass

        # Notice publik singkat, ping user sesuai permintaan
        if self.cfg.send_public_notice:
            try:
                await message.channel.send(
                    f"{message.author.mention} tolong post di channel {dest}",
                    delete_after=self.cfg.public_notice_ttl,
                )
            except Exception:
                pass

        # Logging opsional
        if self.cfg.log_channel_id:
            try:
                logch = message.guild.get_channel(self.cfg.log_channel_id)
                if isinstance(logch, (discord.TextChannel, discord.Thread)):
                    emb = discord.Embed(
                        title="Gacha image tertangkap",
                        description=(
                            f"User: {message.author.mention} ({message.author.id})\n"
                            f"Channel: {message.channel.mention} ({message.channel.id})\n"
                        ),
                        color=discord.Color.orange(),
                    )
                    await logch.send(embed=emb)
            except Exception:
                pass


async def setup(bot: commands.Bot):
    if not CONFIG.allowed_gacha_channel_ids:
        print("[gacha_luck_guard] WARNING: allowed_gacha_channel_ids kosong.")
    await bot.add_cog(GachaLuckGuard(bot, CONFIG))
