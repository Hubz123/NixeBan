# -*- coding: utf-8 -*-
"""
nixe.helpers.attachment_mirror
Mirror attachments to a safe thread/channel before original message is deleted by guards.
"""
from __future__ import annotations
import io, os, logging
import discord

log = logging.getLogger("nixe.helpers.attachment_mirror")

def _env_int(key: str, default: int) -> int:
    try: return int(os.getenv(key, str(default)))
    except Exception: return default

async def mirror_attachments_for_log(
    bot: discord.Client,
    message: discord.Message,
    reason: str = "guard",
    dest_id: int | None = None,
    include_phash: bool = True,
) -> discord.Message | None:
    """
    Download image attachments of `message`, re-upload to dest channel/thread, and return mirror message.
    Skips non-images and files over MIRROR_MAX_BYTES.
    """
    try:
        if not message.attachments:
            return None
        if dest_id is None:
            # prefer explicit mirror dest, then imagephish thread, then phash DB thread, finally log channel
            for key in ("MIRROR_DEST_ID", "PHASH_IMAGEPHISH_THREAD_ID", "PHASH_DB_THREAD_ID", "LOG_CHANNEL_ID"):
                v = os.getenv(key, "0")
                if v and v.isdigit() and int(v) != 0:
                    dest_id = int(v); break
        if not dest_id:
            log.warning("[mirror] dest not resolved")
            return None

        dest = bot.get_channel(int(dest_id))
        if dest is None:
            log.warning("[mirror] dest channel not found: %s", dest_id)
            return None

        max_bytes = _env_int("MIRROR_MAX_BYTES", _env_int("SUS_ATTACH_MAX_BYTES", 5_000_000))
        files, phash_lines = [], []

        # Optional pHash
        pfunc = None
        if include_phash:
            try:
                from nixe.helpers.phash_board import phash_hex_from_bytes as pfunc  # type: ignore
            except Exception:
                pfunc = None

        for att in message.attachments:
            ctype = att.content_type or ""
            if not ctype.startswith("image/"):
                continue
            data = await att.read()
            if len(data) > max_bytes:
                phash_lines.append(f"- {att.filename}: skipped (>{max_bytes} bytes)")
                continue
            if pfunc:
                try:
                    h = pfunc(data)
                    phash_lines.append(f"- {att.filename}: {h}")
                except Exception:
                    pass
            files.append(discord.File(io.BytesIO(data), filename=att.filename))

        if not files:
            return None

        header = (f"[mirror:{reason}] from #{message.channel.name} "
                  f"(author={getattr(message.author, 'display_name', message.author)}, msg_id={message.id})")
        content = header + ("\n" + "\n".join(phash_lines) if phash_lines else "")
        mirror_msg = await dest.send(content=content, files=files)
        log.info("[mirror] uploaded %d file(s) -> %s", len(files), mirror_msg.jump_url)
        return mirror_msg
    except Exception as e:
        log.warning("[mirror] failed: %r", e)
        return None