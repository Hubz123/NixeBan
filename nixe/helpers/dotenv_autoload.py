# lightweight dotenv autoload (works even if python-dotenv not installed)
import os, io, re, pathlib, logging
log = logging.getLogger(__name__)

_LOADED = False

def _parse_line(line: str):
    # supports KEY=VALUE and KEY="VALUE"
    m = re.match(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$', line)
    if not m: return None, None
    k, v = m.group(1), m.group(2)
    if v.startswith(("'", '"')) and v.endswith(("'", '"')) and len(v)>=2:
        v = v[1:-1]
    return k, v

def autoload(dotenv_path: str | None = None):
    global _LOADED
    if _LOADED: return
    try:
        # prefer python-dotenv if available
        try:
            from dotenv import load_dotenv
            load_dotenv(dotenv_path or ".env", override=False)
            _LOADED = True
            log.warning("[dotenv] loaded via python-dotenv")
            return
        except Exception:
            pass
        # manual parse
        p = pathlib.Path(dotenv_path or ".env")
        if not p.exists():
            return
        for line in io.open(p, "r", encoding="utf-8", errors="ignore"):
            line=line.strip()
            if not line or line.startswith("#"): continue
            k, v = _parse_line(line)
            if not k: continue
            if k not in os.environ:
                os.environ[k] = v
        _LOADED = True
        log.warning("[dotenv] loaded via manual parser")
    except Exception as e:
        log.warning("[dotenv] load failed: %s: %s", type(e).__name__, e)
