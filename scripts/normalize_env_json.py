
#!/usr/bin/env python3
import json, re
from pathlib import Path
root = Path(__file__).resolve().parents[1]
envp = root/'nixe'/'config'/'runtime_env.json'
try: data=json.loads(envp.read_text(encoding='utf-8'))
except Exception: data={}
def digits(x): return ''.join(re.findall(r'\d+', str(x)))
nums = ["PHASH_DB_MESSAGE_ID","NIXE_PHASH_SOURCE_THREAD_ID","NIXE_PHASH_DB_THREAD_ID","LUCKYPULL_REDIRECT_CHANNEL_ID","PHISH_FTF_TIMEOUT_SEC","PHISH_HASH_HAMMING_MAX"]
for k in nums:
    v = digits(data.get(k,""))
    data[k] = v if v else "1400000000000000000"
bools = ["PHASH_DB_STRICT_EDIT","NIXE_PHASH_AUTOBACKFILL","LUCKYPULL_MENTION","LUCKYPULL_IMAGE_HEURISTICS","LUCKYPULL_GEMINI_ENABLE","NIXE_ENV_OVERRIDE","NIXE_ENV_BOOT_LOG","PHISH_FTF_ENABLE","LUCKYPULL_ENABLE"]
for k in bools:
    v=str(data.get(k,"")).strip().lower()
    data[k] = "1" if v in ("1","true","yes","y","on") else "0"
envp.write_text(json.dumps(data, indent=2), encoding='utf-8')
print("[OK] runtime_env normalized")
