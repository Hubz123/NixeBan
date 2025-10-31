from __future__ import annotations
import json, random, pathlib
from typing import Dict, Optional, List

_BASE = pathlib.Path(__file__).resolve().parents[1]  # .../nixe
_DIRS = [
    _BASE / "config" / "personas",   # preferred
    _BASE / "config",                # fallback (v3 files like yandere.json)
]
_CACHE: Dict[str, Dict] = {}

def _coerce_groups(data: Dict) -> Dict[str, list]:
    """Accept both v1 (soft/agro/sharp at top-level) and v3 ({'groups': {...}})."""
    if isinstance(data, dict) and "groups" in data and isinstance(data["groups"], dict):
        return data["groups"]
    # legacy schema: collect top-level soft/agro/sharp/possessive if present
    groups = {}
    for k in ("soft", "agro", "sharp", "possessive", "killer", "yandere_killer", "poss"):
        v = data.get(k)
        if isinstance(v, list) and v:
            groups[k if k != "poss" else "possessive"] = v
    return groups

def _load(name: str) -> Dict:
    if name in _CACHE:
        return _CACHE[name]
    data = {}
    for d in _DIRS:
        path = d / f"{name}.json"
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except Exception:
                    data = {}
            break
    # normalize to unified structure
    groups = _coerce_groups(data)
    payload = {"groups": groups, "version": data.get("version", 1), "persona": data.get("persona", name)}
    _CACHE[name] = payload
    return payload

def reload_persona(name: str) -> None:
    _CACHE.pop(name, None)

def list_groups(name: str) -> List[str]:
    return list(_load(name).get("groups", {}).keys())

def _choose_group_by_mode(groups: Dict[str, list], mode: Optional[str] = None, tone: Optional[str] = None, score: Optional[int] = None) -> str:
    keys = list(groups.keys())
    if not keys:
        return ""
    if tone and tone in groups:
        return tone
    if mode in (None, "", "random"):
        return random.choice(keys)
    if mode == "aggressive":
        for pref in ("sharp","agro","possessive","soft"):
            if pref in groups:
                return pref
        return random.choice(keys)
    if mode == "by_score":
        try:
            s = int(score if score is not None else 50)
        except Exception:
            s = 50
        # buckets: 0..25 soft, 26..50 possessive, 51..80 agro, 81..100 sharp
        if s <= 25 and "soft" in groups: return "soft"
        if s <= 50 and "possessive" in groups: return "possessive"
        if s <= 80 and "agro" in groups: return "agro"
        if "sharp" in groups: return "sharp"
        return random.choice(keys)
    return random.choice(keys)

def pick_line(name: str, mode: Optional[str] = None, tone: Optional[str] = None, score: Optional[int] = None, **fmt) -> str:
    data = _load(name)
    groups = data.get("groups", {})
    if not groups:
        return ""
    g = _choose_group_by_mode(groups, mode=mode, tone=tone, score=score)
    tmpl = random.choice(groups.get(g, [""]))
    # safe-format: if a placeholder is missing, leave it empty
    class _D(dict):
        def __missing__(self, key): return ""
    try:
        return tmpl.format_map(_D(fmt))
    except Exception:
        try:
            return tmpl.format(**fmt)
        except Exception:
            return tmpl
