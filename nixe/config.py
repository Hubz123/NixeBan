import os
import os
from dataclasses import dataclass
from typing import List, Set

def _bool(name: str, default: bool=False) -> bool:
    v = os.getenv(name)
    if v is None: return default
    return v.strip().lower() in ("1","true","yes","on","y")

def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)).strip())
    except Exception:
        return default

def _csv_set(name: str) -> Set[int]:
    v = os.getenv(name) or ""
    out: Set[int] = set()
    for tok in [t.strip() for t in v.replace(";",",").split(",") if t.strip()]:
        if tok.isdigit():
            out.add(int(tok))
    return out

def _csv_list(name: str) -> list[str]:
    v = os.getenv(name) or ""
    return [t.strip() for t in v.replace(";",",").split(",") if t.strip()]

@dataclass
class ImageGuardCfg:
    enable_autoban: bool
    phash_distance_strict: int
    phash_distance_lenient: int
    db_thread_id: int
    db_channel_id: int
    whitelist_roles: Set[int]
    delete_message_days: int
    warmup_seconds: int
    ban_cooldown_seconds: int
    ban_ceiling_per_10min: int
    quarantine_minutes: int
    ban_only_newer_than_days: int

@dataclass
class LinkGuardCfg:
    enable_automod: bool
    autoban_on_match: bool
    db_channel_id: int
    blacklist_domains: list[str]
    regexes: list[str]
    delete_message_days: int

@dataclass
class AppCfg:
    token: str
    log_level: str
    mod_log_channel_id: int
    mod_log_channel_name: str
    image: ImageGuardCfg
    link: LinkGuardCfg

def load() -> AppCfg:
    token = os.getenv("BOT_TOKEN","").strip()
    level = os.getenv("LOG_LEVEL","INFO").upper()

    image = ImageGuardCfg(
        enable_autoban=_bool("ENABLE_PHISH_AUTOBAN", True),
        phash_distance_strict=_int("PHASH_DISTANCE_STRICT", 4),
        phash_distance_lenient=_int("PHASH_DISTANCE_LENIENT", 6),
        db_thread_id=_int("PHISH_DB_THREAD_ID", 0),
        db_channel_id=_int("PHISH_DB_CHANNEL_ID", 0),
        whitelist_roles=_csv_set("PHISH_WHITELIST_ROLES"),
        delete_message_days=_int("DELETE_MESSAGE_DAYS", 1),
        warmup_seconds=_int("WARMUP_SECONDS", 120),
        ban_cooldown_seconds=_int("BAN_COOLDOWN_SECONDS", 20),
        ban_ceiling_per_10min=_int("BAN_CEILING_PER_10MIN", 5),
        quarantine_minutes=_int("QUARANTINE_MINUTES", 60),
        ban_only_newer_than_days=_int("BAN_ONLY_NEWER_THAN_DAYS", 14),
    )

    link = LinkGuardCfg(
        enable_automod=_bool("ENABLE_LINK_AUTOMOD", True),
        autoban_on_match=_bool("LINK_AUTOBAN_ON_MATCH", False),
        db_channel_id=_int("LINK_DB_CHANNEL_ID", 0),
        blacklist_domains=_csv_list("LINK_BLACKLIST"),
        regexes=_csv_list("LINK_REGEXES"),
        delete_message_days=_int("DELETE_MESSAGE_DAYS", 1)
    )

    mod_log_channel_id = _int("MOD_LOG_CHANNEL_ID", 0)
    mod_log_channel_name = os.getenv("MOD_LOG_CHANNEL_NAME", "log-botphising")
    return AppCfg(token, level, mod_log_channel_id, mod_log_channel_name, image, link)