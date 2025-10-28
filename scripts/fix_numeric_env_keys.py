
#!/usr/bin/env python3
import json, re
from pathlib import Path
root = Path(__file__).resolve().parents[1]
envp = root/'nixe'/'config'/'runtime_env.json'
envp.parent.mkdir(parents=True, exist_ok=True)
try:
    data = json.loads(envp.read_text(encoding='utf-8'))
except Exception:
    data = {}
def digits_only(x): 
    s = ''.join(re.findall(r'\d+', str(x)))
    return s if s else '0'
for k in ('NIXE_PHASH_SOURCE_THREAD_ID','NIXE_PHASH_DB_THREAD_ID','PHASH_DB_MESSAGE_ID'):
    data[k] = digits_only(data.get(k, '0'))
envp.write_text(json.dumps(data, indent=2), encoding='utf-8')
print('[OK] Numeric keys fixed:', {k:data[k] for k in ('NIXE_PHASH_SOURCE_THREAD_ID','NIXE_PHASH_DB_THREAD_ID','PHASH_DB_MESSAGE_ID')})
