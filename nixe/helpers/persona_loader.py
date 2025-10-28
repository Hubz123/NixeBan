from __future__ import annotations
import json
import random
import pathlib
from typing import Dict, Optional, List

# Lazy cache & default search path: nixe/config/personas
_BASE = pathlib.Path(__file__).resolve().parents[1]  # points to .../nixe
_DEFAULT_DIR = _BASE / "config" / "personas"
_CACHE: Dict[str, Dict] = {}

def _load(name: str) -> Dict:
    """Load and cache a persona definition by file stem (e.g., 'yandere')."""
    if name in _CACHE:
        return _CACHE[name]
    path = _DEFAULT_DIR / f"{name}.json"
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    _CACHE[name] = data
    return data

def list_groups(name: str) -> List[str]:
    data = _load(name)
    groups = data.get("groups", {})
    return list(groups.keys())

def pick_line(name: str, tone: Optional[str] = None, **fmt):
    """Return one formatted line from persona templates.
    - name: persona file stem (e.g., 'yandere')
    - tone: optional group key ('soft'|'agro'|'sharp'); if None, weighted random.
    - fmt: placeholders like user, channel, reason.
    """
    data = _load(name)
    groups = data.get("groups", {})
    if not groups:
        return ""

    if tone is None or tone not in groups:
        weights = data.get("select", {}).get("weights", {})
        keys = list(groups.keys())
        ws = [weights.get(k, 1) for k in keys]
        tone = random.choices(keys, weights=ws, k=1)[0]

    template = random.choice(groups.get(tone, [""]))
    try:
        return template.format(**fmt)
    except Exception:
        # If formatting fails (missing keys), return raw template
        return template

def reload_persona(name: str) -> None:
    """Drop cache entry for a persona so next use re-reads the JSON."""
    _CACHE.pop(name, None)
