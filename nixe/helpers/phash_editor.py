import os
import asyncio

async def get_edit_target(bot):
    """Return (channel, message) to edit for pHash DB.
    Returns (None, None) if strict edit mode is on and target not found.
    """
    msg = getattr(bot, "_phash_db_edit_message", None)
    if msg:
        try:
            channel = msg.channel
            # Refresh latest message reference (optional)
            m = await channel.fetch_message(msg.id)
            return channel, m
        except Exception:
            return None, None

    # If not preloaded via overlay, try env
    strict = os.environ.get("PHASH_DB_STRICT_EDIT", "1") == "1"
    thread_id = int(os.environ.get("PHASH_DB_THREAD_ID", "0")) or int(os.environ.get("PHASH_IMAGEPHISH_THREAD_ID", "0")) if os.environ.get("PHASH_IMAGEPHISH_THREAD_ID") else 0
    msg_id = int(os.environ.get("PHASH_DB_MESSAGE_ID", "0"))
    if not thread_id or not msg_id:
        return (None, None) if strict else (None, None)

    try:
        channel = bot.get_channel(thread_id) or await bot.fetch_channel(thread_id)
        m = await channel.fetch_message(msg_id)
        return channel, m
    except Exception:
        return (None, None)
