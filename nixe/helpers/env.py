from __future__ import annotations
import os
from typing import Any

def _cfg_get(k: str, default=None):
    try:
        from nixe.config import load as _load_cfg  # type: ignore
        cfg = _load_cfg()
        if isinstance(cfg, dict):
            return cfg.get(k, default)
    except Exception:
        pass
    return default

BOT_PREFIX = os.getenv("COMMAND_PREFIX") or _cfg_get("COMMAND_PREFIX", "!")
BOT_TOKEN  = os.getenv("DISCORD_TOKEN") or os.getenv("BOT_TOKEN") or _cfg_get("BOT_TOKEN","")
FLASK_ENV  = os.getenv("FLASK_ENV", "production")

try:
    LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID") or _cfg_get("BAN_LOG_CHANNEL_ID", 0) or 0)
except Exception:
    LOG_CHANNEL_ID = 0
LOG_CHANNEL_NAME = os.getenv("LOG_CHANNEL_NAME") or _cfg_get("LOG_CHANNEL_NAME","")

BOT_INTENTS = {
    "guilds": True,
    "members": True,
    "presences": True,
    "message_content": True,
}
