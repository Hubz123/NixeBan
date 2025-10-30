
# -*- coding: utf-8 -*-
"""
Channel Directory / List Command (sections + {channel} resolver + link buttons)
- Triggers:
  • Text command: !channel list
  • Natural: "nixe @channel list" / "nixe channel list" (case-insensitive)
- Config file (recommended): CHANNEL_DIR_JSON_PATH -> JSON with either:
  A) {"sections":[{"title":"...","items":[{"id":"...", "name":"{channel}", "desc":"..."}]}]}
  B) {"items":[{"id":"...", "name":"{channel}", "desc":"..."}]}
- Mentions: value selalu tampil <#ID> agar clickable & auto-resolve nama.
- Buttons: per embed/section, dibuat link ke kanal/thread (maks 25 tombol per pesan).
"""

import os, json, re, logging, asyncio
from typing import List, Dict, Any, Optional, Tuple
import discord
from discord.ext import commands

log = logging.getLogger("nixe.cogs.channel_directory")

def _get(*names: str, default: str | None = None) -> Optional[str]:
    for n in names:
        v = os.getenv(n)
        if v is not None and str(v) != "":
            return v
    return default

def _color_int(s: str | None, default: int = 0x60a5fa) -> int:
    if not s:
        return default
    try:
        s = s.strip()
        if s.startswith("#"):
            return int(s[1:], 16)
        return int(s, 0)
    except Exception:
        return default

def _load_cfg() -> Dict[str, Any]:
    jpath = _get("CHANNEL_DIR_JSON_PATH")
    if jpath:
        try:
            with open(jpath, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception as e:
            log.warning("[chan-dir] failed to load %s: %r", jpath, e)

    jstr = _get("CHANNEL_DIR_ITEMS_JSON")
    if jstr:
        try:
            items = json.loads(jstr)
            if isinstance(items, list):
                return {"items": items}
        except Exception as e:
            log.warning("[chan-dir] bad CHANNEL_DIR_ITEMS_JSON: %r", e)

    # Fallback minimal
    return {
        "title": _get("CHANNEL_DIR_TITLE", default="📌 Direktori Channel & Thread"),
        "color": _get("CHANNEL_DIR_COLOR", default="#60a5fa"),
        "footer": _get("CHANNEL_DIR_FOOTER", default="Gunakan channel sesuai fungsinya ya ✨"),
        "items": []
    }

def _resolve_name(guild: Optional[discord.Guild], cid: int, default_label: str = "channel") -> str:
    if guild is None:
        return default_label
    try:
        ch = guild.get_channel(cid)
        if ch is None:
            for t in getattr(guild, "threads", []):
                if int(t.id) == cid:
                    ch = t
                    break
        if ch is not None:
            if isinstance(ch, (discord.TextChannel, discord.VoiceChannel, discord.StageChannel, discord.CategoryChannel, discord.ForumChannel)):
                return f"#{ch.name}"
            return str(getattr(ch, "name", default_label))
    except Exception:
        pass
    return default_label

def _channel_url(guild: Optional[discord.Guild], cid: int) -> Optional[str]:
    if guild is None:
        return None
    try:
        ch = guild.get_channel(cid)
        if ch is None:
            for t in getattr(guild, "threads", []):
                if int(t.id) == cid:
                    # thread URL requires parent id
                    return f"https://discord.com/channels/{guild.id}/{t.parent_id}/{t.id}"
        if ch is not None:
            return f"https://discord.com/channels/{guild.id}/{ch.id}"
    except Exception:
        pass
    return None

def _build_view_buttons(guild: Optional[discord.Guild], items: List[Dict[str, Any]], limit: int = 25) -> Optional[discord.ui.View]:
    add_buttons = bool(int(_get("CHANNEL_DIR_ADD_LINK_BUTTONS", default="1") or "1"))
    if not add_buttons or guild is None:
        return None
    view = discord.ui.View()
    count = 0
    for it in items:
        if count >= limit:
            break
        cid_str = str(it.get("id","")).strip()
        if not cid_str:
            continue
        try:
            cid = int(cid_str)
        except Exception:
            continue
        url = _channel_url(guild, cid)
        if not url:
            continue
        label = _resolve_name(guild, cid, default_label=cid_str).lstrip("#")
        # Discord button label max ~80; kita jaga <= 22 biar rapi
        if len(label) > 22:
            label = label[:21] + "…"
        try:
            view.add_item(discord.ui.Button(label=label, url=url))
            count += 1
        except Exception:
            pass
    return view if count > 0 else None

def _build_embeds_and_views(cfg: Dict[str, Any], guild: Optional[discord.Guild]) -> List[Tuple[discord.Embed, Optional[discord.ui.View]]]:
    title  = cfg.get("title")  or _get("CHANNEL_DIR_TITLE",  default="📌 Direktori Channel & Thread")
    color  = _color_int(str(cfg.get("color")  or _get("CHANNEL_DIR_COLOR",  default="#60a5fa")))
    thumb_cfg  = cfg.get("thumbnail") or _get("CHANNEL_DIR_THUMB")
    footer = cfg.get("footer") or _get("CHANNEL_DIR_FOOTER", default="Gunakan channel sesuai fungsinya ya ✨")
    show_ids = bool(int(_get("CHANNEL_DIR_SHOW_IDS", default="0") or "0"))

    def _emb(title_local: str) -> discord.Embed:
        e = discord.Embed(title=title_local, color=color)
        # Auto thumbnail fallback ke icon server
        if thumb_cfg:
            e.set_thumbnail(url=thumb_cfg)
        else:
            try:
                if guild and guild.icon:
                    e.set_thumbnail(url=guild.icon.url)
            except Exception:
                pass
        if footer: e.set_footer(text=footer)
        return e

    out: List[Tuple[discord.Embed, Optional[discord.ui.View]]] = []
    sections = cfg.get("sections")
    if isinstance(sections, list) and sections:
        for sec in sections:
            stitle = sec.get("title") or title
            e = _emb(stitle)
            items_for_view: List[Dict[str, Any]] = []
            count = 0
            sec_items = sec.get("items", [])
            for it in sec_items:
                cid = str(it.get("id","")).strip()
                if not cid: continue
                try: cid_i = int(cid)
                except: continue

                name_tpl = str(it.get("name") or "{channel}")
                name = _resolve_name(guild, cid_i) if name_tpl == "{channel}" else name_tpl

                mention = f"<#{cid}>"
                desc = str(it.get("desc") or "")
                val = f"{mention}" if not desc else f"{mention}\n{desc}"
                if show_ids:
                    val = f"{val}\n`{cid}`"
                e.add_field(name=name, value=val, inline=False)
                items_for_view.append({"id": cid})
                count += 1
                if count >= 25:
                    view = _build_view_buttons(guild, items_for_view, limit=25)
                    out.append((e, view))
                    e = _emb(stitle); items_for_view = []; count = 0
            view = _build_view_buttons(guild, items_for_view, limit=25)
            out.append((e, view))
    else:
        e = _emb(title)
        items_for_view: List[Dict[str, Any]] = []
        count = 0
        for it in cfg.get("items", []):
            cid = str(it.get("id","")).strip()
            if not cid: continue
            try: cid_i = int(cid)
            except: continue

            name_tpl = str(it.get("name") or "{channel}")
            name = _resolve_name(guild, cid_i) if name_tpl == "{channel}" else name_tpl

            mention = f"<#{cid}>"
            desc = str(it.get("desc") or "")
            val = f"{mention}" if not desc else f"{mention}\n{desc}"
            if show_ids:
                val = f"{val}\n`{cid}`"
            e.add_field(name=name, value=val, inline=False)
            items_for_view.append({"id": cid})
            count += 1
            if count >= 25:
                view = _build_view_buttons(guild, items_for_view, limit=25)
                out.append((e, view))
                e = _emb(title); items_for_view = []; count = 0
        view = _build_view_buttons(guild, items_for_view, limit=25)
        out.append((e, view))

    return out

def _match_natural_command(text: str) -> bool:
    return bool(re.search(r"(?i)\b(?:nixe|leina)\s*@?channel\s+list\b", text))

class ChannelDirectory(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._auto_delete = int(_get("CHANNEL_DIR_AUTO_DELETE_SEC", default="0") or "0")
        self._ping_on_help = bool(int(_get("CHANNEL_DIR_PING_ON_HELP", default="0") or "0"))

    async def _send_embeds(self, destination: discord.abc.Messageable, author: Optional[discord.abc.User] = None):
        cfg = _load_cfg()
        guild = getattr(destination, "guild", None)
        items = _build_embeds_and_views(cfg, guild)
        mention = (author.mention + " ") if (author and self._ping_on_help) else ""
        try:
            first_msg = None
            for em, view in items:
                if first_msg is None:
                    first_msg = await destination.send(mention, embed=em, view=view)
                else:
                    await destination.send(embed=em, view=view)
            if self._auto_delete > 0 and first_msg:
                await asyncio.sleep(self._auto_delete)
                await first_msg.delete()
        except Exception as e:
            log.warning("[chan-dir] failed to send embed: %r", e)

    @commands.command(name="channel")
    async def channel_group(self, ctx: commands.Context, sub: str = None):
        if sub and sub.lower() == "list":
            await self._send_embeds(ctx.channel, ctx.author)

    @commands.Cog.listener("on_message")
    async def _on_message(self, message: discord.Message):
        try:
            if message.author.bot:
                return
            if _match_natural_command(message.content or ""):
                await self._send_embeds(message.channel, message.author)
        except Exception as e:
            log.debug("[chan-dir] on_message fail: %r", e)

async def setup(bot: commands.Bot):
    await bot.add_cog(ChannelDirectory(bot))
