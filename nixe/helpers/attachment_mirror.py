# nixe/helpers/attachment_mirror.py — silent + resilient
import io, os, discord
def _env_int(key: str, default: int = 0) -> int:
    try: return int(os.getenv(key, str(default)))
    except Exception: return default
async def mirror_attachments_for_log(bot: discord.Client, message: discord.Message, reason: str="guard", dest_id: int|None=None):
    try:
        if not message.attachments: return None
        if dest_id is None:
            for key in ("MIRROR_DEST_ID","PHASH_IMAGEPHISH_THREAD_ID","PHASH_DB_THREAD_ID","LOG_CHANNEL_ID"):
                v=_env_int(key,0)
                if v: dest_id=v; break
        if not dest_id: return None
        dest = message.guild.get_channel(dest_id) if message.guild else None
        if dest is None:
            try: dest = await bot.fetch_channel(dest_id)
            except Exception: return None
        if isinstance(dest, discord.Thread):
            try: await dest.join()
            except Exception: pass
        files=[]
        for att in message.attachments:
            data=await att.read()
            files.append(discord.File(io.BytesIO(data), filename=att.filename))
        if not files: return None
        return await dest.send(content=f"[mirror:{reason}] id={message.id}", files=files)
    except Exception: return None
