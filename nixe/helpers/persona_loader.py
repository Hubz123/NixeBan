
# -*- coding: utf-8 -*-
import os, json

def _repo_root():
    here = os.path.abspath(os.path.dirname(__file__))
    return os.path.abspath(os.path.join(here, "..", ".."))

def candidate_paths():
    root = _repo_root()
    env_path = os.getenv("LPG_PERSONA_PATH") or os.getenv("PERSONA_PATH")
    cands = []
    if env_path:
        cands.append(env_path)
    cands.append(os.path.join(root, "nixe", "config", "yandere.json"))
    cands.append(os.path.join(root, "nixe", "config", "personas", "yandere.json"))
    cands.append(os.path.join(root, "nixe", "config", "lpg_persona.json"))
    return cands

def _normalize(data):
    if isinstance(data, dict) and {"soft","agro","sharp"} <= set(data.keys()):
        return {"yandere": data}
    return data

def load_persona():
    for p in candidate_paths():
        try:
            if not os.path.exists(p):
                continue
            with open(p, "r", encoding="utf-8") as f:
                raw = f.read()
            data = json.loads(raw)
            data = _normalize(data)
            if not isinstance(data, dict) or not data:
                continue
            mode = next(iter(data.keys()))
            block = data.get(mode) or {}
            if not isinstance(block, dict):
                continue
            if not {"soft","agro","sharp"} <= set(block.keys()):
                continue
            return mode, data, p
        except Exception:
            continue
    return None, {}, None

def pick_line(data, mode, tone):
    mode = mode if (mode in data) else (next(iter(data.keys())) if data else "yandere")
    tones = data.get(mode, {})
    tone = tone if tone in ("soft","agro","sharp") else "soft"
    bucket = tones.get(tone) or tones.get("soft") or []
    if not bucket:
        return "..."
    import random
    return random.choice(bucket)
