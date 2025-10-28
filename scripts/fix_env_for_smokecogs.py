#!/usr/bin/env python3
import json, re
from pathlib import Path
root = Path(__file__).resolve().parents[1]
envp = root/'nixe'/'config'/'runtime_env.json'
if not envp.exists():
    envp.parent.mkdir(parents=True, exist_ok=True)
    envp.write_text("{}", encoding="utf-8")
data = {}
try:
    data = json.loads(envp.read_text(encoding='utf-8') or "{}")
except Exception:
    data = {}
def put(k,v):
    if str(data.get(k,'')).strip()=='':
        data[k]=v
# digits-only for numeric keys
for k in ['PHASH_DB_MESSAGE_ID','LUCKYPULL_REDIRECT_CHANNEL_ID']:
    s = ''.join(re.findall(r'\d+', str(data.get(k,'0'))))
    data[k] = s if s!='' else '0'
# normalize bool keys to "0"/"1"
for k in ['PHASH_DB_STRICT_EDIT','NIXE_PHASH_AUTOBACKFILL','LUCKYPULL_MENTION','LUCKYPULL_IMAGE_HEURISTICS','LUCKYPULL_GEMINI_ENABLE','NIXE_ENV_OVERRIDE','NIXE_ENV_BOOT_LOG']:
    v = str(data.get(k,'')).strip().lower()
    data[k] = '1' if v in ('1','true','yes','y','on') else '0'
envp.write_text(json.dumps(data, indent=2), encoding='utf-8')
print('[OK] runtime_env.json normalized for smoke_cogs')
