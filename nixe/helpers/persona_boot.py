from __future__ import annotations
import json, pathlib, logging

log = logging.getLogger(__name__)
PERSONA_PATH = pathlib.Path(__file__).resolve().parents[1] / "config" / "personas" / "yandere.json"

def persona_version() -> str:
    try:
        with PERSONA_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
        ver = data.get("version", "?")
        persona = data.get("persona","?")
        return f"{persona}@v{ver}"
    except Exception as e:
        return f"yandere@<unreadable> ({e})"
