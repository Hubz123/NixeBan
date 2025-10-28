#!/usr/bin/env python3
# Normalize runtime_env.json for Nixe (numeric/bool 0/1)
import json, re, sys, os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / "nixe" / "config" / "runtime_env.json"
if not ENV.exists():
    # create minimal
    ENV.parent.mkdir(parents=True, exist_ok=True)
    ENV.write_text("{}", encoding="utf-8")

data = {}
try:
    data = json.loads(ENV.read_text(encoding="utf-8") or "{}")
except Exception:
    print("[WARN] runtime_env.json invalid JSON; rewriting minimal")
    data = {}

def put_if_missing(k, v):
    if str(data.get(k,"")).strip() == "":
        data[k] = v

# Ensure required keys exist
put_if_missing("PHASH_DB_MESSAGE_ID", "0")
put_if_missing("LUCKYPULL_REDIRECT_CHANNEL_ID", "0")
put_if_missing("PHASH_DB_STRICT_EDIT", "1")
put_if_missing("NIXE_PHASH_AUTOBACKFILL", "0")
put_if_missing("LUCKYPULL_MENTION", "0")
put_if_missing("LUCKYPULL_IMAGE_HEURISTICS", "1")
put_if_missing("LUCKYPULL_GEMINI_ENABLE", "1")
put_if_missing("NIXE_ENV_OVERRIDE", "1")
put_if_missing("NIXE_ENV_BOOT_LOG", "1")

# Coerce to numeric digits only where required
def digits_only(s):
    s = str(s)
    m = re.findall(r"\d+", s)
    return "".join(m) if m else "0"

for numkey in ("PHASH_DB_MESSAGE_ID","LUCKYPULL_REDIRECT_CHANNEL_ID"):
    data[numkey] = digits_only(data.get(numkey, "0"))

# Coerce booleans to "0"/"1"
def to_bool01(v):
    s = str(v).strip().lower()
    if s in ("1","true","yes","y","on"): return "1"
    return "0"

for bkey in ("PHASH_DB_STRICT_EDIT","NIXE_PHASH_AUTOBACKFILL","LUCKYPULL_MENTION",
             "LUCKYPULL_IMAGE_HEURISTICS","LUCKYPULL_GEMINI_ENABLE",
             "NIXE_ENV_OVERRIDE","NIXE_ENV_BOOT_LOG"):
    data[bkey] = to_bool01(data.get(bkey, "0"))

ENV.write_text(json.dumps(data, indent=2), encoding="utf-8")
print("[OK] normalized runtime_env.json")
