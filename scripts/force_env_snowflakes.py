
#!/usr/bin/env python3
import json, re
from pathlib import Path
root=Path(__file__).resolve().parents[1]
envp=root/'nixe'/'config'/'runtime_env.json'
try: data=json.loads(envp.read_text(encoding='utf-8'))
except Exception: data={}
def digits(x): return ''.join(re.findall(r'\d+', str(x)))
def normalize(k, default):
    v=digits(data.get(k,""))
    if not (6 <= len(v) <= 22):
        data[k]=default
    else:
        data[k]=v
for k,default in [
    ("PHASH_DB_MESSAGE_ID","1400000000000000000"),
    ("NIXE_PHASH_SOURCE_THREAD_ID","1400000000000000001"),
    ("NIXE_PHASH_DB_THREAD_ID","1400000000000000002")
]:
    normalize(k, default)
envp.write_text(json.dumps(data, indent=2), encoding='utf-8')
print("[OK] snowflakes:", {k:data[k] for k in ["PHASH_DB_MESSAGE_ID","NIXE_PHASH_SOURCE_THREAD_ID","NIXE_PHASH_DB_THREAD_ID"]})
