#!/usr/bin/env python3
from pathlib import Path
import json, sys

ENV = Path(__file__).resolve().parents[1] / "nixe" / "config" / "runtime_env.json"
if not ENV.exists():
    print("[WARN] runtime_env.json not found. See runtime_env.json.sample.")
    sys.exit(0)

data = json.loads(ENV.read_text(encoding="utf-8"))
required = ["DISCORD_TOKEN","LOG_CHANNEL_ID","PHASH_DB_THREAD_ID","PHISH_LOG_CHAN_ID",
            "NIXE_PHISH_LOG_CHAN_ID","PHASH_IMAGEPHISH_THREAD_ID","STRICT_PHASH_EDIT",
            "GACHA_GUARD_ENABLED","GACHA_REDIRECT_CHANNEL_ID"]
missing = [k for k in required if str(data.get(k,"")).strip() in ("","0","None","null")]
if missing:
    print("[WARN] Missing/empty:", ", ".join(missing))
else:
    print("[OK] All required keys present")
