# -*- coding: utf-8 -*-
"""Single source of truth for NIXE pHash configuration."""
import os

def _to_int(v, d):
    try:
        return int(v)
    except Exception:
        return int(d)

# === Required ===
PHASH_DB_THREAD_ID         = _to_int(os.getenv("PHASH_DB_THREAD_ID") or 1430048839556927589, 1430048839556927589)
PHASH_DB_MESSAGE_ID        = _to_int(os.getenv("PHASH_DB_MESSAGE_ID") or 0, 0)
PHASH_IMAGEPHISH_THREAD_ID = _to_int(os.getenv("PHASH_IMAGEPHISH_THREAD_ID") or 1409949797313679492, 1409949797313679492)
PHASH_DB_STRICT_EDIT       = bool(int(os.getenv("PHASH_DB_STRICT_EDIT") or 1))

# === Optional / policy ===
PHASH_DB_MARKER               = os.getenv("PHASH_DB_MARKER") or "[phash-db-board]"
PHASH_DB_MAX_ITEMS            = _to_int(os.getenv("PHASH_DB_MAX_ITEMS") or 5000, 5000)
PHASH_BOARD_EDIT_MIN_INTERVAL = _to_int(os.getenv("PHASH_BOARD_EDIT_MIN_INTERVAL") or 180, 180)
BAN_DRY_RUN        = _to_int(os.getenv("BAN_DRY_RUN") or 0, 0)
BAN_DELETE_SECONDS = _to_int(os.getenv("BAN_DELETE_SECONDS") or 86400, 86400)
PHASH_HAMMING_MAX  = _to_int(os.getenv("PHASH_HAMMING_MAX") or 0, 0)

__all__ = [
    "PHASH_DB_THREAD_ID",
    "PHASH_DB_MESSAGE_ID",
    "PHASH_IMAGEPHISH_THREAD_ID",
    "PHASH_DB_STRICT_EDIT",
    "PHASH_DB_MARKER",
    "PHASH_DB_MAX_ITEMS",
    "PHASH_BOARD_EDIT_MIN_INTERVAL",
    "BAN_DRY_RUN",
    "BAN_DELETE_SECONDS",
    "PHASH_HAMMING_MAX",
]
