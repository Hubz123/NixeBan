# -*- coding: utf-8 -*-
from __future__ import annotations
import os, json
from pathlib import Path
from typing import Dict, Any

ROOT = Path(__file__).resolve().parents[1]
ENV  = ROOT / "config" / "runtime_env.json"

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
    # Return 1 for truthy (not in 0/false/no/off), else 0
    return 0 if str(v).strip().lower() in ("0","false","no","off") else 1

# Export strictly-typed INT values (smoke-friendly)
NIXE_PHASH_SOURCE_THREAD_ID: int = int(_digits(_get("NIXE_PHASH_SOURCE_THREAD_ID", "0")))
NIXE_PHASH_DB_THREAD_ID: int     = int(_digits(_get("NIXE_PHASH_DB_THREAD_ID", "0")))
PHASH_DB_MESSAGE_ID: int         = int(_digits(_get("PHASH_DB_MESSAGE_ID", "0")))

PHASH_DB_STRICT_EDIT: int        = _as01(_get("PHASH_DB_STRICT_EDIT", "1"))
NIXE_PHASH_AUTOBACKFILL: int     = _as01(_get("NIXE_PHASH_AUTOBACKFILL", "0"))

# Legacy aliases as ints too
PHASH_IMAGEPHISH_THREAD_ID: int  = NIXE_PHASH_SOURCE_THREAD_ID
PHASH_DB_THREAD_ID: int          = NIXE_PHASH_DB_THREAD_ID
