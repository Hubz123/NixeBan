#!/usr/bin/env python3
import json, urllib.request
import sys
url = "http://localhost:10000/healthz"
try:
    data = json.loads(urllib.request.urlopen(url, timeout=2).read().decode())
    print("[HEALTHZ]", data.get("status"), data.get("bot_restart_count"))
except Exception as e:
    print("[HEALTHZ] error:", e)
    sys.exit(2)
