# -*- coding: utf-8 -*-
from __future__ import annotations
import os, json
from pathlib import Path
from typing import Dict, Any, Optional

# Robust resolver: works for both nixe/config_phash.py and nixe/config/config_phash.py
_THIS = Path(__file__).resolve()
def _find_env_file() -> Path:
    cand = [
        _THIS.parent / "config" / "runtime_env.json",           # if file is nixe/config_phash.py  -> nixe/config/...
        _THIS.parents[1] / "config" / "runtime_env.json",       # if file is nixe/config/config_phash.py -> nixe/config/...
        _THIS.parent.parent / "config" / "runtime_env.json",    # extra fallback
    ]
    for p in cand:
        if p.exists():
            return p
    # last resort: return the most likely location (under nixe/config)
    return (_THIS.parents[1] / "config" / "runtime_env.json")

ENV = _find_env_file()

def _json() -> Dict[str, Any]:
    try:
        return json.loads(ENV.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _get(key: str, default: str = "0") -> str:
    v = os.environ.get(key, None)
    if v is None:
        v = _json().get(key, default)
    return ("" if v is None else str(v)).strip()

def _digits(v: str) -> str:
    s = "".join(ch for ch in str(v) if ch.isdigit())
    return s or "0"

def _as01(v: str) -> int:
    return 0 if str(v).strip().lower() in ("0","false","no","off") else 1

# Snowflake/thread IDs (INT-typed for smoke)
NIXE_PHASH_SOURCE_THREAD_ID: int = int(_digits(_get("NIXE_PHASH_SOURCE_THREAD_ID", "0")))
NIXE_PHASH_DB_THREAD_ID: int     = int(_digits(_get("NIXE_PHASH_DB_THREAD_ID", "0")))
PHASH_DB_MESSAGE_ID: int         = int(_digits(_get("PHASH_DB_MESSAGE_ID", "0")))

# Allow imagephish thread to be independent; fallback to source if missing
PHASH_IMAGEPHISH_THREAD_ID: int  = int(_digits(_get("PHASH_IMAGEPHISH_THREAD_ID", str(NIXE_PHASH_SOURCE_THREAD_ID))))

# Booleans as 0/1 ints
PHASH_DB_STRICT_EDIT: int        = _as01(_get("PHASH_DB_STRICT_EDIT", "1"))
NIXE_PHASH_AUTOBACKFILL: int     = _as01(_get("NIXE_PHASH_AUTOBACKFILL", "0"))

# Legacy alias for compatibility
PHASH_DB_THREAD_ID: int          = NIXE_PHASH_DB_THREAD_ID
