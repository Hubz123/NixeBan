# -*- coding: utf-8 -*-
from __future__ import annotations
import os, json
from pathlib import Path

try:
    from dotenv import load_dotenv, find_dotenv  # type: ignore
    p = find_dotenv(usecwd=True)
    if p: load_dotenv(p)
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[1]
ENV_JSON = ROOT / "config" / "runtime_env.json"
SECRETS_JSON = ROOT / "config" / "secrets.json"

_SENSITIVE_EXACT = {
    "DISCORD_TOKEN","GEMINI_API_KEY","GEMINI_API_KEY",
    "OPENAI_API_KEY","GROQ_API_KEY",
    "UPSTASH_REDIS_REST_URL","UPSTASH_REDIS_REST_TOKEN",
    "ANTHROPIC_API_KEY","COHERE_API_KEY",
}
_SENSITIVE_FRAGMENTS = ("API_KEY","ACCESS_TOKEN","REFRESH_TOKEN","_TOKEN","_SECRET","_PASSWORD")

def _load_json(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _is_sensitive(name: str) -> bool:
    n = (name or "").upper()
    if n in _SENSITIVE_EXACT: return True
    for frag in _SENSITIVE_FRAGMENTS:
        if frag in n: return True
    return False

def _get_flag(name: str, default: str = "0") -> str:
    v = os.environ.get(name, None)
    if v is not None: return str(v).strip()
    j = _load_json(ENV_JSON).get(name, None)
    if j is not None: return str(j).strip()
    s = _load_json(SECRETS_JSON).get(name, None)
    return str(s).strip() if s is not None else str(default)

def get(key: str, default: str = "") -> str:
    allow_json_secrets = _get_flag("NIXE_ALLOW_JSON_SECRETS", "1") == "1"
    if _is_sensitive(key):
        env_v = os.environ.get(key, None)
        if env_v is not None: return str(env_v).strip()
        if allow_json_secrets:
            s = _load_json(SECRETS_JSON).get(key, None)
            if s is not None and str(s).strip(): return str(s).strip()
            j = _load_json(ENV_JSON).get(key, None)
            if j is not None and str(j).strip(): return str(j).strip()
        return str(default)
    v = _load_json(ENV_JSON).get(key, None)
    if v is None or str(v).strip() in ("", "<inherit>", "<placeholder>"):
        v = os.environ.get(key, default)
    return str(v).strip() if v is not None else str(default)

def get_int(key: str, default: int = 0) -> int:
    try:
        return int(float(get(key, str(default))))
    except Exception:
        return int(default)

def get_bool01(key: str, default: str = "0") -> str:
    s = get(key, default).lower()
    return "1" if s in ("1","true","yes","y","on") else "0"

def source(key: str) -> str:
    allow_json_secrets = _get_flag("NIXE_ALLOW_JSON_SECRETS", "1") == "1"
    if _is_sensitive(key):
        if os.environ.get(key, None) is not None: return "env"
        if allow_json_secrets:
            if _load_json(SECRETS_JSON).get(key, None): return "secrets.json"
            if _load_json(ENV_JSON).get(key, None): return "runtime_env.json"
        return "<default>"
    if _load_json(ENV_JSON).get(key, None): return "runtime_env.json"
    if os.environ.get(key, None) is not None: return "env"
    return "<default>"
