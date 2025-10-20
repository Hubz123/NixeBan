# nixe/config/__init__.py  (v11: cfg.image is DotDict; load('image') still dict)
from __future__ import annotations
import os
from typing import Any, Dict, List, Tuple

try:
    from .self_learning_cfg import *  # noqa
    import nixe.config.self_learning_cfg as _cfg
except Exception:
    _cfg = None

class DotDict(dict):
    __slots__ = ()
    def __getattr__(self, k):
        try: return self[k]
        except KeyError as e: raise AttributeError(k) from e
    def __setattr__(self, k, v): self[k] = v
    def copy(self): return DotDict(super().copy())

def _env_int(name: str, default: int) -> int:
    try:
        v = os.getenv(name)
        if v is None: return default
        return int(str(v).strip())
    except Exception:
        return default

def _env_bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None: return default
    s = str(v).strip().lower()
    if s in {"1","true","yes","on"}: return True
    if s in {"0","false","no","off"}: return False
    try: return bool(int(s))
    except Exception: return default

_DEFAULTS: Dict[str, Any] = {
    "PHASH_DB_MARKER": os.getenv("PHASH_DB_MARKER", "SATPAMBOT_PHASH_DB_V1"),
    "LINK_DB_MARKER": os.getenv("LINK_DB_MARKER", "SATPAMBOT_LINK_BLACKLIST_V1"),
    "TEMPLATES_DIR": os.getenv("NIXE_TEMPLATES_DIR", "templates"),
    "PHASH_INBOX_THREAD": os.getenv(
        "NIXE_PHASH_INBOX_THREAD",
        os.getenv("PHASH_INBOX_THREAD", "imagephising,imagelogphising,image-phising,image_phising,image-phishing,image_phishing")
    ),
    "PHASH_HAMMING_MAX": _env_int("PHASH_HAMMING_MAX", 0),
    "PHASH_WATCH_FIRST_DELAY": _env_int("PHASH_WATCH_FIRST_DELAY", 60),
    "PHASH_WATCH_INTERVAL": _env_int("PHASH_WATCH_INTERVAL", 600),
    "BAN_DRY_RUN": _env_bool("BAN_DRY_RUN", True),
    "BAN_DELETE_SECONDS": _env_int("BAN_DELETE_SECONDS", 0),
    "BAN_BRAND_NAME": os.getenv("BAN_BRAND_NAME", "SatpamBot"),
    "NIXE_HEALTHZ_PATH": os.getenv("NIXE_HEALTHZ_PATH", "/healthz"),
    "NIXE_HEALTHZ_SILENCE": _env_bool("NIXE_HEALTHZ_SILENCE", True),
    "BAN_LOG_CHANNEL_ID": int(os.getenv("NIXE_BAN_LOG_CHANNEL_ID") or os.getenv("BAN_LOG_CHANNEL_ID") or "0"),
    "LOG_CHANNEL_ID": int(os.getenv("NIXE_BAN_LOG_CHANNEL_ID") or os.getenv("BAN_LOG_CHANNEL_ID") or "0"),
}

class _Config:
    def __init__(self):
        self._src: Dict[str, Any] = {}
        if _cfg is not None:
            for k, v in _cfg.__dict__.items():
                if k.isupper():
                    self._src[k] = v
        for k, v in _DEFAULTS.items():
            self._src.setdefault(k, v)
        self._sections: Dict[str, Dict[str, Any]] = {}

    def get(self, key: str, default: Any = None) -> Any:
        return self._src.get(key, os.getenv(key, default))

    def __getattr__(self, key: str) -> Any:
        if key in self._sections:
            return self._sections[key]
        if key == "image":
            sec = DotDict(_image_section(self)); self._sections[key] = sec; return sec
        if key == "link":
            sec = DotDict(_link_section(self)); self._sections[key] = sec; return sec
        if key == "ban":
            sec = DotDict(_ban_section(self)); self._sections[key] = sec; return sec
        if key == "healthz":
            sec = DotDict(_healthz_section(self)); self._sections[key] = sec; return sec
        raise AttributeError(key)

    def __dir__(self):
        base = set(super().__dir__()); base.update({"image","link","ban","healthz"}); return sorted(base)

def _split_threads(raw: Any) -> List[str]:
    if raw is None: return []
    if isinstance(raw, (list, tuple, set)):
        return [str(x).strip() for x in raw if str(x).strip()]
    s = str(raw)
    parts = [p.strip() for p in s.replace(";", ",").split(",")]
    return [p for p in parts if p]

def _image_section(cfg: _Config) -> Dict[str, Any]:
    names = [t.lower() for t in _split_threads(cfg.get("PHASH_INBOX_THREAD"))]
    primary = names[0] if names else "imagephising"
    marker = str(cfg.get("PHASH_DB_MARKER"))
    strict = _env_int("IMAGE_PHASH_DISTANCE_STRICT", _env_int("PHASH_HAMMING_MAX", 0))
    lenient = _env_int("IMAGE_PHASH_DISTANCE_LENIENT", strict)
    warmup = _env_int("IMAGE_WARMUP_SECONDS", 0)
    ban_cooldown = _env_int("IMAGE_BAN_COOLDOWN_SECONDS", 0)
    ban_ceiling = _env_int("IMAGE_BAN_CEILING_PER_10MIN", 0)
    first = _env_int("PHASH_WATCH_FIRST_DELAY", 60)
    interval = _env_int("PHASH_WATCH_INTERVAL", 600)
    csv = ",".join(names)
    return {
        "THREADS": tuple(names),
        "THREADS_LIST": list(names),
        "THREAD_NAMES": list(names),
        "THREADS_CSV": csv,
        "IMAGE_PHISH_THREAD_NAMES": csv,
        "INBOX_THREAD": primary,
        "THREAD_NAME": primary,
        "THREAD": primary,
        "THREAD_ID": int(os.getenv("IMAGE_THREAD_ID") or "0"),
        "PHASH_DB_MARKER": marker, "DB_MARKER": marker, "MARKER": marker,
        "LOG_CHANNEL_ID": int(cfg.get("LOG_CHANNEL_ID") or 0),
        "CHANNEL_ID": int(cfg.get("LOG_CHANNEL_ID") or 0),
        "phash_distance_strict": strict,
        "phash_distance_lenient": lenient,
        "warmup_seconds": warmup,
        "ban_cooldown_seconds": ban_cooldown,
        "ban_ceiling_per_10min": ban_ceiling,
        "HAMMING_MAX": strict,
        "WATCH_FIRST_DELAY": first,
        "WATCH_INTERVAL": interval,
        "TEMPLATES_DIR": cfg.get("TEMPLATES_DIR"),
        "PHASH_DISTANCE_STRICT": strict,
        "PHASH_DISTANCE_LENIENT": lenient,
        "WARMUP_SECONDS": warmup,
        "BAN_COOLDOWN_SECONDS": ban_cooldown,
        "BAN_CEILING_PER_10MIN": ban_ceiling,
    }

def _link_section(cfg: _Config) -> Dict[str, Any]:
    marker = str(cfg.get("LINK_DB_MARKER"))
    return {"LINK_DB_MARKER": marker, "DB_MARKER": marker, "MARKER": marker}

def _ban_section(cfg: _Config) -> Dict[str, Any]:
    return {
        "DRY_RUN": bool(cfg.get("BAN_DRY_RUN", True)),
        "DELETE_SECONDS": int(cfg.get("BAN_DELETE_SECONDS", 0) or 0),
        "BRAND": str(cfg.get("BAN_BRAND_NAME", "SatpamBot")),
        "BAN_LOG_CHANNEL_ID": int(cfg.get("BAN_LOG_CHANNEL_ID", 0) or 0),
    }

def _healthz_section(cfg: _Config) -> Dict[str, Any]:
    return {"PATH": str(cfg.get("NIXE_HEALTHZ_PATH", "/healthz")), "SILENCE": bool(cfg.get("NIXE_HEALTHZ_SILENCE", True))}

def load(section: str | None = None):
    cfg = _Config()
    if not section:
        return cfg
    s = str(section).strip().lower()
    if s in {"image","images","phash"}: return _image_section(cfg)   # still plain dict
    if s in {"link","links","url"}: return _link_section(cfg)        # still plain dict
    if s in {"ban","moderation"}: return _ban_section(cfg)           # still plain dict
    if s in {"healthz","health"}: return _healthz_section(cfg)       # still plain dict
    return cfg

# Module-level section objects (as DotDict for attr access)
image = DotDict(_image_section(_Config()))
link = DotDict(_link_section(_Config()))
ban = DotDict(_ban_section(_Config()))
healthz = DotDict(_healthz_section(_Config()))

__all__ = ["load", "image", "link", "ban", "healthz"]
