# -*- coding: utf-8 -*-
import os, re, json
SEARCH_JSON = [
    os.path.join("nixe","config","runtime_env.json"),
    os.path.join("runtime_env.json"),
]
SEARCH_ENV = [".env", os.path.join("nixe","config",".env")]

def _load_json(path):
    try:
        with open(path,"r",encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def _load_dotenv(path):
    try:
        out={}
        with open(path,"r",encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"): continue
                m = re.match(r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)", line)
                if not m: continue
                k, v = m.group(1), m.group(2)
                if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                    v=v[1:-1]
                out[k]=v
        return out
    except Exception:
        return None

def init(verbose=False):
    for p in SEARCH_JSON:
        if os.path.exists(p):
            js=_load_json(p) or {}
            for k,v in js.items():
                if k not in os.environ and isinstance(v,(str,int,float)):
                    os.environ[k]=str(v)
            if verbose: print(f"[env-hybrid] loaded json: {p} -> {len(js)} keys")
            break
    for p in SEARCH_ENV:
        if os.path.exists(p):
            js=_load_dotenv(p) or {}
            for k,v in js.items():
                if k not in os.environ and isinstance(v,(str,int,float)):
                    os.environ[k]=str(v)
            if verbose: print(f"[env-hybrid] loaded .env: {p} -> {len(js)} keys")
            break
