
from __future__ import annotations
import os, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
ENV_JSON = ROOT / "config" / "runtime_env.json"
def _json() -> dict:
    try: return json.loads(ENV_JSON.read_text(encoding="utf-8"))
    except Exception: return {}
def get(key: str, default: str = "") -> str:
    data = _json()
    v = data.get(key, None)
    if v is None: v = os.environ.get(key, default)
    return str(v).strip() if v is not None else str(default)
def get_bool01(key: str, default: str = "0") -> str:
    s = get(key, default).lower()
    return "1" if s in ("1","true","yes","y","on") else "0"
def get_int(key: str, default: int = 0) -> int:
    s = "".join(ch for ch in get(key, str(default)) if ch.isdigit())
    return int(s) if s else int(default)
