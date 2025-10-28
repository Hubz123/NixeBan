
import os, json

def apply_env_from_json(path: str, override: bool = True) -> int:
    """Return number of keys applied."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return 0
    except Exception:
        return 0
    n = 0
    for k, v in data.items():
        if v is None:
            continue
        if override or (k not in os.environ or os.environ.get(k, "") == ""):
            os.environ[str(k)] = str(v)
            n += 1
    return n
