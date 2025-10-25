
import os
import json
import logging
import asyncio
import discord
from discord.ext import commands
from nixe.helpers.img_hashing import phash_list_from_bytes, dhash_list_from_bytes

log = logging.getLogger(__name__)

MARKER = (os.getenv("PHASH_DB_MARKER") or "NIXE_PHASH_DB_V1").strip()
SRC_THREAD_ID = int(os.getenv("NIXE_PHASH_SOURCE_THREAD_ID", "0") or 0)
SRC_THREAD_NAME = (os.getenv("NIXE_PHASH_SOURCE_THREAD_NAME") or "imagephising").lower()

# Rescan configuration
RESCAN_ON_START = int(os.getenv("NIXE_PHASH_RESCAN_ON_START", "1") or 1) == 1
RESCAN_INTERVAL = int(os.getenv("NIXE_PHASH_RESCAN_INTERVAL", "0") or 0)  # 0 = no periodic rescan
RESCAN_LIMIT_MSGS = int(os.getenv("NIXE_PHASH_RESCAN_LIMIT", "1200") or 1200)  # messages per rescan
RESCAN_MAX_ATTACH = int(os.getenv("NIXE_PHASH_RESCAN_MAX_ATTACH", "6") or 6)
STRICT_EDIT = int(os.getenv("PHASH_DB_STRICT_EDIT", "1") or 1) == 1

IMAGE_EXTS = (".png",".jpg",".jpeg",".webp",".gif",".bmp",".tif",".tiff",".heic",".heif")

def _render(phashes, dhashes):
    data = {"phash": phashes or []}
    if dhashes:
        data["dhash"] = dhashes
    return f"{MARKER}\n```json\n{json.dumps(data, separators=(',',':'), ensure_ascii=False)}\n```"

def _parse_db(msg: discord.Message):
    if not msg or not (msg.content or ""):
        return [], []
    s = msg.content
    i, j = s.find("{"), s.rfind("}")
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
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._task = self.bot.loop.create_task(self._bootstrap())

    def cog_unload(self):
        try:
            self._task.cancel()
        except Exception:
            pass

    async def _bootstrap(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(2)
        if RESCAN_ON_START:
            try:
                await self._rescan_history_once()
            except Exception as e:
                log.warning("[phash-rescan] error on start: %s", e)
        if RESCAN_INTERVAL > 0:
            while not self.bot.is_closed():
                await asyncio.sleep(RESCAN_INTERVAL)
                try:
                    await self._rescan_history_once()
                except Exception as e:
                    log.warning("[phash-rescan] periodic error: %s", e)

    def _is_target_thread(self, ch: discord.abc.GuildChannel) -> bool:
        if isinstance(ch, discord.Thread):
            if SRC_THREAD_ID and ch.id == SRC_THREAD_ID:
                return True
            return (ch.name or "").lower() == SRC_THREAD_NAME
        return False

    async def _get_src_thread(self) -> discord.Thread | None:
        # prefer ID
        if SRC_THREAD_ID:
            try:
                th = self.bot.get_channel(SRC_THREAD_ID) or await self.bot.fetch_channel(SRC_THREAD_ID)
                if isinstance(th, discord.Thread):
                    return th
            except Exception:
                pass
        # fallback by name: search text channels' threads (first match)
        try:
            for ch in self.bot.get_all_channels():
                if isinstance(ch, discord.Thread) and (ch.name or "").lower() == SRC_THREAD_NAME:
                    return ch
        except Exception:
            pass
        return None

    async def _get_db_message(self, parent: discord.TextChannel) -> tuple[discord.Message | None, list[str], list[str]]:
        # look for existing DB board by MARKER
        try:
            async for m in parent.history(limit=50):
                if m.author.id == self.bot.user.id and MARKER in (m.content or ""):
                    ph, dh = _parse_db(m)
                    return m, ph, dh
        except Exception:
            pass
        return None, [], []

    async def _commit_board(self, parent: discord.TextChannel, msg: discord.Message | None, phashes: list[str], dhashes: list[str]):
        content = _render(phashes, dhashes)
        if msg:
            try:
                await msg.edit(content=content)
                return msg
            except Exception as e:
                log.warning("[phash-rescan] edit failed: %s", e)
                if STRICT_EDIT:
                    return msg
        try:
            return await parent.send(content)
        except Exception as e:
            log.warning("[phash-rescan] create failed: %s", e)
            return None

    async def _rescan_history_once(self):
        th = await self._get_src_thread()
        if not th:
            log.warning("[phash-rescan] source thread not found (id=%s name=%s)", SRC_THREAD_ID, SRC_THREAD_NAME)
            return
        parent = th.parent
        if not isinstance(parent, discord.TextChannel):
            log.warning("[phash-rescan] parent channel invalid for thread id=%s", th.id)
            return
        board, cur_p, cur_d = await self._get_db_message(parent)
        sp, sd = set(cur_p), set(cur_d)
        new_p, new_d = list(cur_p), list(cur_d)

        scanned = 0
        async for msg in th.history(limit=RESCAN_LIMIT_MSGS, oldest_first=True):
            scanned += 1
            if not msg.attachments:
                continue
            # ignore bot authors
            if getattr(msg.author, "bot", False):
                continue
            count = 0
            for att in msg.attachments:
                if count >= RESCAN_MAX_ATTACH:
                    break
                name = (att.filename or "").lower()
                if not any(name.endswith(ext) for ext in IMAGE_EXTS):
                    continue
                try:
                    raw = await att.read()
                except Exception:
                    continue
                if not raw:
                    continue
                for h in phash_list_from_bytes(raw, max_frames=6):
                    if h not in sp:
                        sp.add(h); new_p.append(h)
                for h in dhash_list_from_bytes(raw, max_frames=6):
                    if h not in sd:
                        sd.add(h); new_d.append(h)
                count += 1

        # Only write when something changed
        if len(new_p) != len(cur_p) or len(new_d) != len(cur_d):
            await self._commit_board(parent, board, new_p, new_d)
            log.info("[phash-rescan] board updated: +%d phash, +%d dhash (scanned=%d)", len(new_p)-len(cur_p), len(new_d)-len(cur_d), scanned)
        else:
            log.info("[phash-rescan] no changes (scanned=%d)", scanned)

    # still keep per-message incremental path
    @commands.Cog.listener("on_message")
    async def on_message(self, message: discord.Message):
        ch = getattr(message, "channel", None)
        if not self._is_target_thread(ch):
            return
        if getattr(message.author, "bot", False):
            return
        if not message.attachments:
            return

        parent = ch.parent if hasattr(ch, "parent") else None
        if not isinstance(parent, discord.TextChannel):
            return

        board, cur_p, cur_d = await self._get_db_message(parent)
        sp, sd = set(cur_p), set(cur_d)
        changed = False
        for att in message.attachments:
            name = (att.filename or "").lower()
            if not any(name.endswith(ext) for ext in IMAGE_EXTS):
                continue
            raw = await att.read()
            if not raw:
                continue
            for h in phash_list_from_bytes(raw, max_frames=6):
                if h not in sp:
                    sp.add(h); cur_p.append(h); changed = True
            for h in dhash_list_from_bytes(raw, max_frames=6):
                if h not in sd:
                    sd.add(h); cur_d.append(h); changed = True
        if changed:
            await self._commit_board(parent, board, cur_p, cur_d)

async def setup(bot: commands.Bot):
    await bot.add_cog(PhashImagephisingWatcher(bot))

def legacy_setup(bot: commands.Bot):
    bot.add_cog(PhashImagephisingWatcher(bot))
