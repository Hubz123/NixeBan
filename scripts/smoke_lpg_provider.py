
# -*- coding: utf-8 -*-
"""
SMOKE: Lucky Pull Provider (with file input)
Usage:
  python scripts/smoke_lpg_provider.py [optional_image_path]
If no path is given, uses the embedded tiny JPEG sample.
"""
import os, sys, base64, hashlib

# Ensure repo root on sys.path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Try to autoload env (runtime_env.json / .env)
try:
    from nixe.helpers.env_hybrid_bootstrap import init as env_init
    env_init(verbose=True)
except Exception as e:
    print("[SMOKE] env bootstrap skipped:", e)

from nixe.helpers.gemini_bridge import classify_lucky_pull_bytes

# Embedded valid tiny JPEG as fallback
SAMPLE_B64 = (
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wCEAAkGBxAQEA8QEA8PDw8PDw8PDw8PDw8PFREWFhUR"
    "FhUYHSggGBolGxUVITEhJSkrLi4uFx8zODMtNygtLisBCgoKDg0OGxAQGy0lICUtLS0tLS0t"
    "LS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLf/AABEIAAEAAQMBIgAA"
    "AAEFAAECAwQABQYHCAkKCwEAAQIDAAEFBwYIBwEBAAECAwQFBgcICQoLEAABAgMEBQYHCAkK"
    "CwEQAQIRAwQhEjEFQQYiUWFxgZGh8BMywdFCIhQjUmJykrLR8QMzQ1Oi0hUWJDRDcoKysgAA"
    "AAAwEBAAIDAAEFAAAAAAAAAAECAxEEEiExQQUTIlFxgQYyQqH/2gAMAwEAAhEDEQA/APpCAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA//Z"
)

def _load_image_bytes(argv):
    if len(argv) >= 2 and os.path.isfile(argv[1]):
        path = argv[1]
        with open(path, "rb") as f:
            b = f.read()
        return ("file:" + os.path.abspath(path), b)
    # fallback to embedded
    return ("embedded", base64.b64decode(SAMPLE_B64))

if __name__ == "__main__":
    src, IMG = _load_image_bytes(sys.argv)
    sha = hashlib.sha1(IMG).hexdigest()
    first8 = IMG[:8].hex()
    print(f"[SMOKE] src={src} len={len(IMG)} sha1={sha[:10]} first8={first8} (ffd8=jpeg)")

    # Smoke-friendly defaults
    os.environ.setdefault("LPG_SMOKE_FORCE_SAMPLE", "0")   # use real bytes if you passed a file
    os.environ.setdefault("LPG_SMOKE_ALLOW_FALLBACK", "1")
    os.environ.setdefault("LPG_GEM_429_COOLDOWN_SEC", "600")

    print("[SMOKE] GEMINI_API_KEY?", bool(os.getenv("GEMINI_API_KEY")))
    print("[SMOKE] GROQ_API_KEY?", bool(os.getenv("GROQ_API_KEY")))

    thr = float(os.getenv("LPG_GROQ_THRESHOLD", "0.5"))
    ok, score, provider, reason = classify_lucky_pull_bytes(IMG, threshold=thr, timeout=12)
    print(f"[SMOKE] result ok={ok} score={score:.3f} provider={provider} reason={reason}")
