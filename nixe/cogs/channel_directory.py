
# -*- coding: utf-8 -*-
"""
Channel Directory / List Command
- Robust config resolver + optional COMPACT mode (single-line per item)
- Per-section overrides: "buttons": 0/1, "compact": 0/1

Triggers:
  • "!channel list"
  • "nixe @channel list" / "nixe channel list"

ENV keys:
  CHANNEL_DIR_JSON_PATH           -> path to JSON (relative or absolute, '/' preferred)
  CHANNEL_DIR_ADD_LINK_BUTTONS    -> "1"|"0" (default "1")
  CHANNEL_DIR_SHOW_IDS            -> "1"|"0" (default "0")
  CHANNEL_DIR_TITLE               -> default title
  CHANNEL_DIR_COLOR               -> hex or int
  CHANNEL_DIR_FOOTER              -> footer text
  CHANNEL_DIR_THUMB               -> thumbnail URL
  CHANNEL_DIR_AUTO_DELETE_SEC     -> seconds (stringified int)
  CHANNEL_DIR_PING_ON_HELP        -> "1"|"0"
  CHANNEL_DIR_COMPACT             -> "1"|"0" (default "0")  <<< NEW
  CHANNEL_DIR_ITEMS_JSON          -> fallback items list JSON-string

JSON file format:
{
  "title": "...",
  "color": "#60a5fa",
  "footer": "...",
  "sections": [
    {
      "title": "📺 Channel Utama",
      "buttons": 0,      // optional override
      "compact": 1,      // optional override
      "items": [
        {"id": "123", "name": "{channel}", "desc": "optional"}
      ]
    }
  ]
}
"""

import os, json, re, logging, asyncio, pathlib
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

_last_cfg_origin = "unknown"

def _try_load_json_file(path: pathlib.Path) -> Optional[Dict[str, Any]]:
    global _last_cfg_origin
    try:
        if path.exists() and path.is_file():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    _last_cfg_origin = str(path)
                    log.info("[chan-dir] loaded config: %s", path)
                    return data
    except Exception as e:
        log.warning("[chan-dir] failed to load %s: %r", path, e)
    return None

def _load_cfg() -> Dict[str, Any]:
    tried = []
    base = pathlib.Path(__file__).resolve().parent.parent  # .../nixe
    p = _get("CHANNEL_DIR_JSON_PATH")
    data = None
    if p:
        p = p.replace("\\", "/")
        for cand in [pathlib.Path(p), pathlib.Path.cwd() / p, base.parent / p]:
            tried.append(str(cand))
            data = _try_load_json_file(cand)
            if data is not None:
                break
    if data is None:
        cand = base / "config" / "channel_directory.json"
        tried.append(str(cand))
        data = _try_load_json_file(cand)
    if data is None:
        jstr = _get("CHANNEL_DIR_ITEMS_JSON")
        if jstr:
            try:
                items = json.loads(jstr)
                if isinstance(items, list):
                    _last_cfg_origin = "ENV:CHANNEL_DIR_ITEMS_JSON"
                    data = {
                        "title": _get("CHANNEL_DIR_TITLE", default="📌 Direktori Channel & Thread"),
                        "color": _get("CHANNEL_DIR_COLOR", default="#60a5fa"),
                        "footer": _get("CHANNEL_DIR_FOOTER", default="Gunakan channel sesuai fungsinya ya ✨"),
                        "items": items
                    }
                    log.info("[chan-dir] using CHANNEL_DIR_ITEMS_JSON with %d items", len(items))
            except Exception as e:
                log.warning("[chan-dir] bad CHANNEL_DIR_ITEMS_JSON: %r", e)
    if data is None:
        _last_cfg_origin = "EMPTY"
        log.warning("[chan-dir] config not found; tried: %s", " | ".join(tried))
        data = {
            "title": _get("CHANNEL_DIR_TITLE", default="📌 Direktori Channel & Thread"),
            "color": _get("CHANNEL_DIR_COLOR", default="#60a5fa"),
            "footer": _get("CHANNEL_DIR_FOOTER", default="Gunakan channel sesuai fungsinya ya ✨"),
            "items": []
        }
    return data

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
                    return f"https://discord.com/channels/{guild.id}/{t.parent_id}/{t.id}"
        if ch is not None:
            return f"https://discord.com/channels/{guild.id}/{ch.id}"
    except Exception:
        pass
    return None

def _build_view_buttons(guild: Optional[discord.Guild], items: list, limit: int = 25, enabled: bool = True) -> Optional[discord.ui.View]:
    add_buttons = enabled and bool(int(_get("CHANNEL_DIR_ADD_LINK_BUTTONS", default="1") or "1"))
    if not add_buttons or guild is None:
        return None
    view = discord.ui.View()
    cnt = 0
    for it in items:
        if cnt >= limit:
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
        if len(label) > 22:
            label = label[:21] + "…"
        try:
            view.add_item(discord.ui.Button(label=label, url=url))
            cnt += 1
        except Exception:
            pass
    return view if cnt > 0 else None

def _build_embeds_and_views(cfg: Dict[str, Any], guild: Optional[discord.Guild]) -> list[tuple[discord.Embed, Optional[discord.ui.View]]]:
    title  = cfg.get("title")  or _get("CHANNEL_DIR_TITLE",  default="📌 Direktori Channel & Thread")
    color  = _color_int(str(cfg.get("color")  or _get("CHANNEL_DIR_COLOR",  default="#60a5fa")))
    thumb_cfg  = cfg.get("thumbnail") or _get("CHANNEL_DIR_THUMB")
    footer = cfg.get("footer") or _get("CHANNEL_DIR_FOOTER", default="Gunakan channel sesuai fungsinya ya ✨")
    show_ids = bool(int(_get("CHANNEL_DIR_SHOW_IDS", default="0") or "0"))
    compact_default = bool(int(_get("CHANNEL_DIR_COMPACT", default="0") or "0"))

    def _emb(title_local: str) -> discord.Embed:
        e = discord.Embed(title=title_local, color=color)
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

    out = []
    sections = cfg.get("sections")
    if isinstance(sections, list) and sections:
        for sec in sections:
            stitle = sec.get("title") or title
            sec_buttons = sec.get("buttons")
            sec_compact = sec.get("compact")
            compact_mode = bool(int(str(sec_compact)) if sec_compact is not None else compact_default)
            e = _emb(stitle)
            items_for_view = []
            count = 0
            for it in sec.get("items", []):
                cid = str(it.get("id","")).strip()
                if not cid: continue
                try: cid_i = int(cid)
                except: continue

                name_tpl = str(it.get("name") or "{channel}")
                resolved_name = _resolve_name(guild, cid_i) if name_tpl == "{channel}" else name_tpl

                mention = f"<#{cid}>"
                desc = str(it.get("desc") or "")

                if compact_mode:
                    field_name = "\u200B"  # invisible
                    field_value = mention if not desc else f"{mention}\n{desc}"
                else:
                    field_name = resolved_name
                    field_value = mention if not desc else f"{mention}\n{desc}"

                if show_ids:
                    field_value = f"{field_value}\n`{cid}`"

                e.add_field(name=field_name, value=field_value, inline=False)
                items_for_view.append({"id": cid})
                count += 1
                if count >= 25:
                    out.append((e, _build_view_buttons(guild, items_for_view, 25, enabled=(sec_buttons!=0))))
                    e = _emb(stitle); items_for_view = []; count = 0
            out.append((e, _build_view_buttons(guild, items_for_view, 25, enabled=(sec_buttons!=0))))
    else:
        e = _emb(title)
        items_for_view = []
        count = 0
        for it in cfg.get("items", []):
            cid = str(it.get("id","")).strip()
            if not cid: continue
            try: cid_i = int(cid)
            except: continue

            name_tpl = str(it.get("name") or "{channel}")
            resolved_name = _resolve_name(guild, cid_i) if name_tpl == "{channel}" else name_tpl

            mention = f"<#{cid}>"
            desc = str(it.get("desc") or "")

            if compact_default:
                field_name = "\u200B"
                field_value = mention if not desc else f"{mention}\n{desc}"
            else:
                field_name = resolved_name
                field_value = mention if not desc else f"{mention}\n{desc}"

            if show_ids:
                field_value = f"{field_value}\n`{cid}`"

            e.add_field(name=field_name, value=field_value, inline=False)
            items_for_view.append({"id": cid})
            count += 1
            if count >= 25:
                out.append((e, _build_view_buttons(guild, items_for_view, 25)))
                e = _emb(title); items_for_view = []; count = 0
        out.append((e, _build_view_buttons(guild, items_for_view, 25)))
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
        sub = (sub or "").lower()
        if sub == "list":
            await self._send_embeds(ctx.channel, ctx.author)
        elif sub == "diag":
            cfg = _load_cfg()
            origin = _last_cfg_origin
            if isinstance(cfg.get("sections"), list):
                sec_counts = [len(s.get("items",[])) for s in cfg["sections"]]
                detail = f"sections={len(sec_counts)} items={sum(sec_counts)} ({sec_counts})"
            else:
                items = len(cfg.get("items",[]))
                detail = f"flat items={items}"
            compact_default = bool(int(_get("CHANNEL_DIR_COMPACT", default="0") or "0"))
            await ctx.send(f"[chan-dir] origin: `{origin}` • {detail} • compact={int(compact_default)}")

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
