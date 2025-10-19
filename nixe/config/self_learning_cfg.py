# nixe/config/self_learning_cfg.py
from __future__ import annotations
import os

def _to_int(*keys, default=0):
    for k in keys:
        v = os.getenv(k)
        if v is None:
            continue
        try:
            return int(v)
        except Exception:
            pass
    return default

def _to_str(*keys, default=""):
    for k in keys:
        v = os.getenv(k)
        if v:
            return v
    return default

# Log/ban channel config (NIXE owns the truth)
BAN_LOG_CHANNEL_ID = _to_int("NIXE_BAN_LOG_CHANNEL_ID", "BAN_LOG_CHANNEL_ID", "LOG_CHANNEL_ID", default=0)
LOG_CHANNEL_ID = BAN_LOG_CHANNEL_ID

# pHash inbox thread (comma separated aliases; default variants of "imagephising")
PHASH_INBOX_THREAD = _to_str("NIXE_PHASH_INBOX_THREAD", "PHASH_INBOX_THREAD",
    default="imagephising,imagelogphising,image-phising,image_phising,image-phishing,image_phishing")

# pHash watcher schedule
PHASH_WATCH_FIRST_DELAY = _to_int("PHASH_WATCH_FIRST_DELAY", default=60)
PHASH_WATCH_INTERVAL = _to_int("PHASH_WATCH_INTERVAL", default=600)

# pHash matching
PHASH_HAMMING_MAX = _to_int("PHASH_HAMMING_MAX", default=0)  # 0 = exact only

# Autoban control (keep safe by default)
PHASH_AUTOBAN_ENABLED = bool(int(os.getenv("PHASH_AUTOBAN_ENABLED", "0")))

# BAN options
BAN_DELETE_SECONDS = _to_int("BAN_DELETE_SECONDS", default=0)
BAN_DRY_RUN = bool(int(os.getenv("BAN_DRY_RUN", "1")))  # default DRY for safety
BAN_BRAND_NAME = _to_str("BAN_BRAND_NAME", default="SatpamBot")

# Healthz
NIXE_HEALTHZ_PATH = _to_str("NIXE_HEALTHZ_PATH", default="/healthz")
NIXE_HEALTHZ_SILENCE = bool(int(os.getenv("NIXE_HEALTHZ_SILENCE", "1")))
