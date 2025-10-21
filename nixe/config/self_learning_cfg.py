from __future__ import annotations
import os

def _int(name: str, default: int) -> int:
    try:
        raw = os.getenv(name, str(default))
        raw = str(raw).strip()
        return int(raw) if raw else int(default)
    except Exception:
        return int(default)

def _bool(name: str, default: bool) -> bool:
    raw = (os.getenv(name, "1" if default else "0") or "").strip().lower()
    return raw in ("1", "true", "yes", "on")

def _str(name: str, default: str) -> str:
    return os.getenv(name, default)

BAN_BRAND_NAME: str = _str("BAN_BRAND_NAME", "NIXE")
BAN_DRY_RUN: bool = _bool("BAN_DRY_RUN", False)
BAN_DELETE_SECONDS: int = _int("BAN_DELETE_SECONDS", 5)

LOG_CHANNEL_ID: int = _int("LOG_CHANNEL_ID", 0)
BAN_LOG_CHANNEL_ID: int = _int("BAN_LOG_CHANNEL_ID", LOG_CHANNEL_ID)
PHASH_INBOX_THREAD: str = os.getenv("PHASH_INBOX_THREAD", "")

PHASH_DB_MARKER: str = _str("PHASH_DB_MARKER", "PHASH_DB_PINNED")
PHASH_HAMMING_MAX: int = _int("PHASH_HAMMING_MAX", 10)

PHASH_FIRST_DELAY_SECONDS: int = _int("PHASH_FIRST_DELAY_SECONDS", 5)
PHASH_INTERVAL_SECONDS: int = _int("PHASH_INTERVAL_SECONDS", 180)
PHASH_LOG_SCAN_LIMIT: int = _int("PHASH_LOG_SCAN_LIMIT", 5000)

PHASH_WATCH_FIRST_DELAY: int = _int("PHASH_WATCH_FIRST_DELAY", 5)
PHASH_WATCH_INTERVAL: int = _int("PHASH_WATCH_INTERVAL", 180)

NIXE_HEALTHZ_PATH: str = _str("NIXE_HEALTHZ_PATH", "/tmp/nixe_healthz")
NIXE_HEALTHZ_SILENCE: bool = _bool("NIXE_HEALTHZ_SILENCE", True)

__all__ = [
    "BAN_BRAND_NAME", "BAN_DRY_RUN", "BAN_DELETE_SECONDS",
    "LOG_CHANNEL_ID", "BAN_LOG_CHANNEL_ID", "PHASH_INBOX_THREAD",
    "PHASH_DB_MARKER", "PHASH_HAMMING_MAX",
    "PHASH_FIRST_DELAY_SECONDS", "PHASH_INTERVAL_SECONDS",
    "PHASH_LOG_SCAN_LIMIT",
    "PHASH_WATCH_FIRST_DELAY", "PHASH_WATCH_INTERVAL",
    "NIXE_HEALTHZ_PATH", "NIXE_HEALTHZ_SILENCE",
]
