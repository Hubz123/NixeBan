
#!/usr/bin/env python3
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / "nixe" / "config" / "runtime_env.json"
ENV.parent.mkdir(parents=True, exist_ok=True)
data = {}
try:
    data = json.loads(ENV.read_text(encoding="utf-8"))
except Exception:
    data = {}

def digits(x): 
    s = "".join(ch for ch in str(x) if ch.isdigit())
    return s if s else "0"

# Ensure keys expected by smoke exist
defaults = {
    "NIXE_PHASH_SOURCE_THREAD_ID": "0",
    "NIXE_PHASH_DB_THREAD_ID": "0",
    "PHASH_DB_MESSAGE_ID": "0",
    "PHASH_DB_STRICT_EDIT": "1",
    "NIXE_PHASH_AUTOBACKFILL": "0"
}
for k,v in defaults.items():
    if str(data.get(k,"")).strip() == "":
        data[k]=v

# Force numeric-only on these three
for k in ("NIXE_PHASH_SOURCE_THREAD_ID","NIXE_PHASH_DB_THREAD_ID","PHASH_DB_MESSAGE_ID"):
    data[k] = digits(data.get(k,"0"))

ENV.write_text(json.dumps(data, indent=2), encoding="utf-8")
print("[OK] Ensured keys & numeric format in runtime_env.json")
