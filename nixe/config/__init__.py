from __future__ import annotations
import os, json
from typing import Any, Dict, List

def _as_bool(v: Any, default: bool=False) -> bool:
    if isinstance(v, bool): return v
    if v is None: return default
    s = str(v).strip().lower()
    if s in {'1','true','yes','on'}: return True
    if s in {'0','false','no','off'}: return False
    return default

def _as_int(v: Any, default: int=0) -> int:
    try:
        return int(v)
    except Exception:
        return default

def _as_list(v: Any) -> List[str]:
    if v is None: return []
    if isinstance(v, list): return v
    s = str(v).strip()
    if not s: return []
    try:
        j = json.loads(s)
        if isinstance(j, list):
            return [str(x) for x in j]
    except Exception:
        pass
    return [x.strip() for x in s.split(',') if x.strip()]

def _env_str(name: str, default: str = '') -> str:
    return os.getenv(name, default)

def _env_int(name: str, default: int = 0) -> int:
    try:
        return int(os.getenv(name, default))
    except Exception:
        return default

def _env_bool(name: str, default: bool = False) -> bool:
    return _as_bool(os.getenv(name), default)

DEFAULTS: Dict[str, Any] = {
    'COMMAND_PREFIX': os.getenv('COMMAND_PREFIX', '!'),
    'BOT_TOKEN': _env_str('DISCORD_TOKEN', _env_str('BOT_TOKEN', '')),
    'FLASK_ENV': os.getenv('FLASK_ENV', 'production'),
    'BAN_LOG_CHANNEL_ID': _env_int('BAN_LOG_CHANNEL_ID', _env_int('LOG_CHANNEL_ID', 0)),
    'HEARTBEAT_ENABLE': False,
    'STATUS_EMBED_ON_READY': False,
    'URL_BAN_PATTERNS': [],
    'PHASH_LOG_SCAN_LIMIT': _env_int('PHASH_LOG_SCAN_LIMIT', 500),
    'SELF_LEARNING_ENABLE': _env_bool('SELF_LEARNING_ENABLE', False),
    'SELF_LEARNING_MAX_ITEMS': _env_int('SELF_LEARNING_MAX_ITEMS', 2000),
}

OVERRIDES: Dict[str, Any] = {}
try:
    from .local_overrides import OVERRIDES as _LOCAL_OVERRIDES  # type: ignore
    if isinstance(_LOCAL_OVERRIDES, dict):
        OVERRIDES.update(_LOCAL_OVERRIDES)
except Exception:
    pass

def load() -> Dict[str, Any]:
    cfg = dict(DEFAULTS)
    cfg.update(OVERRIDES)
    return cfg

def get(key: str, default: Any=None) -> Any:
    return load().get(key, default)

# constants for legacy imports
COMMAND_PREFIX: str = get('COMMAND_PREFIX', '!')
BOT_TOKEN: str = get('BOT_TOKEN', '')
FLASK_ENV: str = get('FLASK_ENV', 'production')
BAN_LOG_CHANNEL_ID: int = int(get('BAN_LOG_CHANNEL_ID', 0))
HEARTBEAT_ENABLE: bool = bool(get('HEARTBEAT_ENABLE', False))
STATUS_EMBED_ON_READY: bool = bool(get('STATUS_EMBED_ON_READY', False))
URL_BAN_PATTERNS = get('URL_BAN_PATTERNS', [])
PHASH_LOG_SCAN_LIMIT: int = int(get('PHASH_LOG_SCAN_LIMIT', 500))
SELF_LEARNING_ENABLE: bool = bool(get('SELF_LEARNING_ENABLE', False))
SELF_LEARNING_MAX_ITEMS: int = int(get('SELF_LEARNING_MAX_ITEMS', 2000))


# ---- NIXE structured config for smoke ----
class _CfgNS:
    def __init__(self, d):
        # expose dict on attributes, and nested sections
        self.__dict__.update(d)
        # Provide 'image' structured thresholds for smoke
        img = {
            "phash_distance_strict": int(os.getenv("PHASH_DISTANCE_STRICT", "6")),
            "phash_distance_lenient": int(os.getenv("PHASH_DISTANCE_LENIENT", "10")),
            "warmup_seconds": int(os.getenv("PHASH_WARMUP_SECONDS", "0")),
            "ban_cooldown_seconds": int(os.getenv("BAN_COOLDOWN_SECONDS", "10")),
            "ban_ceiling_per_10min": int(os.getenv("BAN_CEILING_PER_10MIN", "5")),
        }
        self.image = img

def load() -> _CfgNS:  # type: ignore[override]
    cfg = dict(DEFAULTS)
    cfg.update(OVERRIDES)
    return _CfgNS(cfg)
