
import os, json, logging, asyncio, discord
from discord.ext import commands
from nixe.helpers.img_hashing import phash_list_from_bytes, dhash_list_from_bytes

log = logging.getLogger(__name__)

MARKER = (os.getenv("PHASH_DB_MARKER") or "NIXE_PHASH_DB_V1").strip()

SRC_THREAD_ID = int(os.getenv("NIXE_PHASH_SOURCE_THREAD_ID", "0") or 0)
SRC_THREAD_NAME = (os.getenv("NIXE_PHASH_SOURCE_THREAD_NAME") or "imagephising").lower()

DEST_THREAD_ID = int(os.getenv("NIXE_PHASH_DB_THREAD_ID", "0") or 0)
LOG_CH_ID = int(os.getenv("LOG_CHANNEL_ID", "0") or 0)
DEST_MSG_ID = int(os.getenv("PHASH_DB_MESSAGE_ID", "0") or 0)

STRICT_EDIT = int(os.getenv("PHASH_DB_STRICT_EDIT", "1") or 1) == 1

IMAGE_EXTS = (".png",".jpg",".jpeg",".webp",".gif",".bmp",".tif",".tiff",".heic",".heif")

def _render(phashes, dhashes):
    data = {"phash": phashes or []}
    if dhashes: data["dhash"] = dhashes
    return f"{MARKER}\n```json\n{json.dumps(data, separators=(',',':'), ensure_ascii=False)}\n```"

def _parse_db(msg):
    if not msg or not (msg.content or ""): return [], []
    s = msg.content; i, j = s.find("{"), s.rfind("}")
    if i != -1 and j != -1 and j > i:
        try:
            o = json.loads(s[i:j+1])
            ph = [str(x) for x in (o.get("phash") or []) if str(x)]
            dh = [str(x) for x in (o.get("dhash") or []) if str(x)]
            return ph, dh
        except Exception:
            return [], []
    return [], []

class PhashImagephisingWatcher(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._task = self.bot.loop.create_task(self._bootstrap())

    def cog_unload(self):
        try: self._task.cancel()
        except Exception: pass

    async def _bootstrap(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(2)
        log.info("[phash-inbox] target dest id=%s (fallback log=%s)", DEST_THREAD_ID, LOG_CH_ID)

    def _is_src(self, ch):
        if isinstance(ch, discord.Thread):
            if SRC_THREAD_ID and ch.id == SRC_THREAD_ID: return True
            return (ch.name or "").lower() == SRC_THREAD_NAME
        return False

    async def _get_dest_container(self):
        # prefer DB thread id
        if DEST_THREAD_ID:
            try:
                d = self.bot.get_channel(DEST_THREAD_ID) or await self.bot.fetch_channel(DEST_THREAD_ID)
                if isinstance(d, (discord.Thread, discord.TextChannel)):
                    return d
            except Exception: pass
        # fallback to LOG_CHANNEL_ID
        if LOG_CH_ID:
            try:
                d = self.bot.get_channel(LOG_CH_ID) or await self.bot.fetch_channel(LOG_CH_ID)
                if isinstance(d, (discord.Thread, discord.TextChannel)):
                    return d
            except Exception: pass
        return None

    async def _get_or_find_db_message(self, dest):
        # try direct id
        if DEST_MSG_ID:
            try:
                m = await dest.fetch_message(DEST_MSG_ID)
                return m, *_parse_db(m)
            except Exception: pass
        # search by marker in dest
        try:
            async for m in dest.history(limit=50):
                if m.author.id == self.bot.user.id and MARKER in (m.content or ""):
                    return m, *_parse_db(m)
        except Exception: pass
        return None, [], []

    async def _commit(self, dest, msg, phashes, dhashes):
        content = _render(phashes, dhashes)
        if msg:
            try:
                await msg.edit(content=content)
                return msg
            except Exception as e:
                log.warning("[phash-inbox] edit failed: %s", e)
                if STRICT_EDIT:
                    return msg
        try:
            return await dest.send(content)
        except Exception as e:
            log.warning("[phash-inbox] create failed: %s", e)
            return None

    @commands.Cog.listener("on_message")
    async def on_message(self, message):
        ch = getattr(message, "channel", None)
        if not self._is_src(ch): return
        if getattr(message.author, "bot", False): return
        if not message.attachments: return

        dest = await self._get_dest_container()
        if not dest: 
            log.warning("[phash-inbox] destination not resolved; skipping")
            return

        board, cur_p, cur_d = await self._get_or_find_db_message(dest)
        sp, sd = set(cur_p), set(cur_d)
        changed = False

        for att in message.attachments:
            name = (att.filename or "").lower()
            if not any(name.endswith(ext) for ext in IMAGE_EXTS): continue
            raw = await att.read()
            if not raw: continue
            for h in phash_list_from_bytes(raw, max_frames=6):
                if h not in sp: sp.add(h); cur_p.append(h); changed = True
            for h in dhash_list_from_bytes(raw, max_frames=6):
                if h not in sd: sd.add(h); cur_d.append(h); changed = True

        if changed:
            await self._commit(dest, board, cur_p, cur_d)

async def setup(bot):
    await bot.add_cog(PhashImagephisingWatcher(bot))
def legacy_setup(bot):
    bot.add_cog(PhashImagephisingWatcher(bot))
