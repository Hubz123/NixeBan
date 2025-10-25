
import os, json, asyncio, discord
from discord.ext import commands
from discord import AllowedMentions
from nixe.helpers import img_hashing

PHASH_DB_MARKER = os.getenv("PHASH_DB_MARKER", "NIXE_PHASH_DB_V1").strip()
TARGET_THREAD_NAME = os.getenv("NIXE_PHASH_SOURCE_THREAD_NAME", "imagephising").lower()
IMAGE_EXTS = (".png",".jpg",".jpeg",".webp",".gif",".bmp",".tif",".tiff",".heic",".heif")
NOTIFY_THREAD = bool(int(os.getenv("PHISH_NOTIFY_THREAD", "0")))
LOG_TTL_SECONDS = int(os.getenv("PHISH_LOG_TTL", "0"))
AUGMENT = bool(int(os.getenv("PHASH_AUGMENT_REGISTER", "1")))
MAX_FRAMES = int(os.getenv("PHASH_MAX_FRAMES", "6"))
AUG_PER = int(os.getenv("PHASH_AUGMENT_PER_FRAME", "5"))
TILE_GRID = int(os.getenv("TILE_GRID", "3"))
ENABLE = os.getenv("NIXE_ENABLE_HASH_PORT", "1") == "1"

def _render_db(phashes, dhashes=None, tiles=None):
    data = {"phash": phashes or []}
    if dhashes: data["dhash"] = dhashes
    if tiles:   data["tphash"] = tiles
    body = json.dumps(data, ensure_ascii=False, separators=(',', ':'), sort_keys=True)
    return f"{PHASH_DB_MARKER}\n```json\n{body}\n```"

def _extract_hashes_from_json_msg(msg: discord.Message):
    if not msg or not msg.content:
        return [], [], []
    s = msg.content
    i, j = s.find("{"), s.rfind("}")
    if i != -1 and j != -1 and j > i:
        try:
            obj = json.loads(s[i:j+1])
            arr_p = obj.get("phash", []) or []
            arr_d = obj.get("dhash", []) or []
            arr_t = obj.get("tphash", []) or []
            P = [str(x).strip() for x in arr_p if str(x).strip()]
            D = [str(x).strip() for x in arr_d if str(x).strip()]
            T = [str(x).strip() for x in arr_t if str(x).strip()]
            return P, D, T
        except Exception:
            return [], [], []
    return [], [], []

class PhashInboxPort(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener("on_message")
    async def on_message_inbox(self, message: discord.Message):
        if not ENABLE:
            return
        try:
            ch = message.channel
            if not isinstance(ch, discord.Thread): return
            if (ch.name or "").lower() != TARGET_THREAD_NAME: return
            if getattr(message.author, "bot", False) or not message.attachments: return

            all_p, all_d, all_t = [], [], []
            for att in message.attachments:
                name = (att.filename or "").lower()
                if not any(name.endswith(ext) for ext in IMAGE_EXTS): continue
                try:
                    raw = await att.read()
                except Exception:
                    continue
                if not raw: continue

                hs = img_hashing.phash_list_from_bytes(raw, max_frames=MAX_FRAMES, augment=AUGMENT, augment_per_frame=AUG_PER)
                if hs: all_p.extend(hs)

                dh_func = getattr(img_hashing, "dhash_list_from_bytes", None)
                if dh_func:
                    ds = dh_func(raw, max_frames=MAX_FRAMES, augment=AUGMENT, augment_per_frame=AUG_PER)
                    if ds: all_d.extend(ds)

                t_func = getattr(img_hashing, "tile_phash_list_from_bytes", None)
                if t_func:
                    ts = t_func(raw, grid=TILE_GRID, max_frames=4, augment=AUGMENT, augment_per_frame=3)
                    if ts: all_t.extend(ts)

            if not (all_p or all_d or all_t): return

            parent = ch.parent if hasattr(ch, "parent") else None
            db_msg = None
            if parent:
                try:
                    async for m in parent.history(limit=50):
                        if m.author.id == self.bot.user.id and PHASH_DB_MARKER in (m.content or ""):
                            db_msg = m; break
                except Exception:
                    db_msg = None

            existing_p, existing_d, existing_t = ([], [], [])
            if db_msg:
                existing_p, existing_d, existing_t = _extract_hashes_from_json_msg(db_msg)

            sp, sd, st = set(existing_p), set(existing_d), set(existing_t)
            added_p = [h for h in all_p if h not in sp and not sp.add(h)]
            added_d = [h for h in all_d if h not in sd and not sd.add(h)]
            added_t = [t for t in all_t if t not in st and not st.add(t)]
            existing_p += added_p; existing_d += added_d; existing_t += added_t

            content = _render_db(existing_p, existing_d, existing_t)

            if db_msg:
                try: await db_msg.edit(content=content)
                except Exception: pass
            else:
                if parent:
                    try: db_msg = await parent.send(content)
                    except Exception: db_msg = None

            if NOTIFY_THREAD and message:
                try:
                    e = discord.Embed(title="pHash update", colour=0xFF8C00)
                    e.add_field(name="Hashes added", value=str(len(added_p) + len(added_d) + len(added_t)), inline=True)
                    e.add_field(name="pHash total", value=str(len(existing_p)), inline=True)
                    e.add_field(name="dHash total", value=str(len(existing_d)), inline=True)
                    await message.reply(embed=e, mention_author=False, allowed_mentions=AllowedMentions.none())
                except Exception:
                    pass
        except Exception:
            return

async def setup(bot: commands.Bot):
    await bot.add_cog(PhashInboxPort(bot))
def legacy_setup(bot: commands.Bot):
    bot.add_cog(PhashInboxPort(bot))
