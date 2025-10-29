from __future__ import annotations
import os, json
from pathlib import Path

# Try to autoload .env (local dev). Ignore if library missing.
try:
    from dotenv import load_dotenv, find_dotenv  # type: ignore
    _p = find_dotenv(usecwd=True)
    if _p:
        load_dotenv(_p)
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
ENV_JSON = ROOT / "config" / "runtime_env.json"

_SENSITIVE_EXACT = {
    "DISCORD_TOKEN",
    "GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY", "GROQ_API_KEY",
    "UPSTASH_REDIS_REST_TOKEN", "UPSTASH_REDIS_REST_URL",
    "HUGGINGFACEHUB_API_TOKEN", "HF_TOKEN",
    "ANTHROPIC_API_KEY", "COHERE_API_KEY",
}

_SENSITIVE_FRAGMENTS = (
    "API_KEY", "ACCESS_TOKEN", "REFRESH_TOKEN", "SESSION_TOKEN",
    "_TOKEN", "_SECRET", "_PASSWORD",
)

def _json() -> dict:
    try:
        return json.loads(ENV_JSON.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _is_sensitive(name: str) -> bool:
    n = (name or "").upper()
    if n in _SENSITIVE_EXACT:
        return True
    for frag in _SENSITIVE_FRAGMENTS:
        if frag in n:
            return True
    return False

def get(key: str, default: str = "") -> str:
    """Bridge policy:
    - Sensitive keys (tokens/API keys/etc) are ALWAYS taken from OS env (Render/.env).
    - Non-sensitive settings prefer runtime_env.json, with fallback to OS env.
    """
    if _is_sensitive(key):
        v = os.environ.get(key, None)
        return str(v).strip() if v is not None else str(default)
    # Non-sensitive: prefer JSON overrides first
    data = _json()
    v = data.get(key, None)
    if v is None or str(v).strip() in ("", "<inherit>", "<placeholder>", "<gemini>"):
        v = os.environ.get(key, default)
    return str(v).strip() if v is not None else str(default)

def get_bool01(key: str, default: str = "0") -> str:
    s = get(key, default).lower()
    return "1" if s in ("1","true","yes","y","on") else "0"

def get_int(key: str, default: int = 0) -> int:
    s = "".join(ch for ch in get(key, str(default)) if ch.isdigit())
    return int(s) if s else int(default)

def source(key: str) -> str:
    """Return 'env' or 'json' to help debug where a value came from."""
    if _is_sensitive(key):
        return "env"
    data = _json()
    return "json" if key in data and str(data.get(key, "")).strip() not in ("", "<inherit>", "<placeholder>", "<gemini>") else "env"
