from __future__ import annotations
import json, random, pathlib
from typing import Dict, Optional, List

_BASE = pathlib.Path(__file__).resolve().parents[1]  # .../nixe
_DEFAULT_DIR = _BASE / "config" / "personas"
_CACHE: Dict[str, Dict] = {}

def _load(name: str) -> Dict:
    if name in _CACHE:
        return _CACHE[name]
    path = _DEFAULT_DIR / f"{name}.json"
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    _CACHE[name] = data
    return data

def list_groups(name: str) -> List[str]:
    return list(_load(name).get("groups", {}).keys())

def pick_line(name: str, **fmt) -> str:
    """Always pick a random tone and a random line within that tone."""
    data = _load(name)
    groups = data.get("groups", {})
    if not groups: return ""
    tone = random.choice(list(groups.keys()))
    template = random.choice(groups.get(tone, [""]))
    try:
        return template.format(**fmt)
    except Exception:
        return template

def reload_persona(name: str) -> None:
    _CACHE.pop(name, None)
