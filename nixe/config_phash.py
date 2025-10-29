# -*- coding: utf-8 -*-
"""pHash config resolver with aliases expected by phash_db_board.py.
Exports:
  - PHASH_DB_THREAD_ID (int)
  - PHASH_DB_MESSAGE_ID (int)  # alias for pinned board message ID
  - PHASH_DB_STRICT_EDIT (int 0/1)
  - PHASH_IMAGEPHISH_THREAD_ID (int)
  - NIXE_PHASH_SOURCE_THREAD_ID (int)
  - LOG_CHANNEL_ID (int)
"""
from __future__ import annotations

def _safe_int(x, default=0):
    try:
        return int(str(x).strip())
    except Exception:
        return int(default)

# Prefer env_reader if present
try:
    from nixe.helpers.env_reader import get as _cfg_get
except Exception:
    import os, json
    from pathlib import Path
    def _cfg_get(key: str, default: str = "") -> str:
        # minimal fallback: runtime_env.json -> ENV
        try:
            ROOT = Path(__file__).resolve().parents[1]
            j = json.loads((ROOT / "config" / "runtime_env.json").read_text(encoding="utf-8"))
            if key in j and str(j[key]).strip():
                return str(j[key]).strip()
        except Exception:
            pass
        return str(os.environ.get(key, default)).strip()

# --- Board pinned message id (provide canonical + aliases) ---
PHASH_DB_BOARD_MSG_ID = _safe_int(_cfg_get("PHASH_DB_BOARD_MSG_ID",
    _cfg_get("PHASH_DB_BOARD_MESSAGE_ID",
        _cfg_get("PHASH_DB_MESSAGE_ID",
            _cfg_get("PHASH_DB_PINNED_MSG_ID",
                _cfg_get("MSG_PHASH_DB_BOARD_ID", "0")
            )
        )
    )
))
# Alias expected by cogs: expose PHASH_DB_MESSAGE_ID
PHASH_DB_MESSAGE_ID = PHASH_DB_BOARD_MSG_ID

# --- DB thread id (canonical + synonyms) ---
PHASH_DB_THREAD_ID = _safe_int(_cfg_get("PHASH_DB_THREAD_ID",
    _cfg_get("NIXE_PHASH_DB_THREAD_ID",
        _cfg_get("PHASH_DB_BOARD_THREAD_ID",
            _cfg_get("PHASH_DB_THREAD", "0")
        )
    )
))

# --- Parent/log channel id ---
LOG_CHANNEL_ID = _safe_int(_cfg_get("PHASH_DB_PARENT_CHANNEL_ID",
    _cfg_get("LOG_CHANNEL_ID",
        _cfg_get("NIXE_PHISH_LOG_CHAN_ID", "0")
    )
))

# --- Source/imagephish thread id ---
PHASH_IMAGEPHISH_THREAD_ID = _safe_int(_cfg_get("PHASH_IMAGEPHISH_THREAD_ID", "0"))
NIXE_PHASH_SOURCE_THREAD_ID = _safe_int(_cfg_get("NIXE_PHASH_SOURCE_THREAD_ID",
    _cfg_get("PHASH_SOURCE_THREAD_ID", str(PHASH_IMAGEPHISH_THREAD_ID))
))

# --- Strict edit flag (default ON to avoid accidental posting) ---
def _bool01(key: str, default: str = "1") -> int:
    v = _cfg_get(key, default).strip().lower()
    return 1 if v in ("1","true","yes","y","on") else 0

PHASH_DB_STRICT_EDIT = _bool01("PHASH_DB_STRICT_EDIT", "1")
