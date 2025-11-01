
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, json, base64

def _print(k, v):
    print(f"[SMOKE] {k} {v}")

def _ensure_sys_path():
    here = os.path.abspath(os.path.dirname(__file__))
    root = os.path.abspath(os.path.join(here, ".."))
    if root not in sys.path:
        sys.path.insert(0, root)
    return os.path.isdir(os.path.join(root, "nixe"))

def _load_runtime_env_json():
    here = os.path.abspath(os.path.dirname(__file__))
    root = os.path.abspath(os.path.join(here, ".."))
    cfg = os.path.join(root, "nixe", "config", "runtime_env.json")
    rel = os.path.join("nixe", "config", "runtime_env.json")  # avoid backslash escapes in literals
    if os.path.exists(cfg):
        try:
            data = json.load(open(cfg, "r", encoding="utf-8"))
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, (str, int, float)):
                        os.environ.setdefault(str(k), str(v))
                print(f"[env-hybrid] loaded json: {rel} -> {len(data)} keys")
        except Exception as e:
            print("[env-hybrid] json load failed:", e)

def _load_dot_env():
    env_path = os.path.join(os.getcwd(), ".env")
    if os.path.exists(env_path):
        cnt = 0
        for line in open(env_path, "r", encoding="utf-8", errors="ignore"):
            line=line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip()); cnt += 1
        print(f"[env-hybrid] loaded .env: .env -> {cnt} keys")
    else:
        print("[env-hybrid] loaded .env: .env -> 0 keys")

def _load_image_bytes():
    path = os.environ.get("SMOKE_IMAGE_PATH")
    if path and os.path.exists(path):
        b = open(path, "rb").read()
        print(f"[SMOKE] loaded image from {path} -> {len(b)} bytes")
        return b
    # tiny fallback
    b64 = ("/9j/4AAQSkZJRgABAQAAAQABAAD/2wCEAAkGBxISEhISEhIVFRUVFRUVFRUVFRUVFRUWFhUVFRUYHSggGBolHRUVITEhJSkrLi4u"
           "FyAzODMtNygtLisBCgoKDg0OGhAQGy0lHyUtLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLS0tLf/A"
           "ABEIAAEAAQMBIgACEQEDEQH/xAAbAAEAAgMBAQAAAAAAAAAAAAAABQYBAwQCB//EADkQAAEDAgQDBgQEBwAAAAAAAAEAAgMEEQUS"
           "ITEGQRMiUWEUcYGRMjKhscHRQlNigrI0Q1PC8P/EABgBAQADAQAAAAAAAAAAAAAAAAQBAgMF/8QAHBEBAAIDAQEAAAAAAAAAAAAA"
           "AAERAhIhMUFR/9oADAMBAAIRAxEAPwD5wREQEREBERAREQEREBERB5r9jI4OQ3YTF0i7bAtwC9b7b4Xr2bPq3vH0ZQmVnD0bZQqK"
           "4E7KqvB3c1qkq4w9QfypZbR2q1X2mT1bM8A3HQ8r8f8A4z1N3G1l9LZ3a2rPzqF8Z6m2p1l2J7tH0Z8m0r4ZpX1Qh1aZk2yM0F6y"
           "T9U2+7b4e0c5S1KfaXH0drkq2h6W+V1+f+qvY6d3H9T1S0sYp0sR4X4k2k0q9oK6y0q2bZbUbbI3f7Fa0O0nM5XoS6o5L3E2EwWc"
           "Xh7A1+e3S3q2tma+fkdZc9cv3G+1z3Wb9gAAAAAAAB//2Q==")
    return base64.b64decode(b64)

def main():
    if not _ensure_sys_path():
        print("[SMOKE] result ok=False score=0.000 provider=none reason=Package 'nixe' not found"); return
    _load_runtime_env_json()
    _load_dot_env()

    print("[SMOKE] GEMINI_API_KEY?", "True" if os.environ.get("GEMINI_API_KEY") else "False")
    print("[SMOKE] GROQ_API_KEY?", "True" if os.environ.get("GROQ_API_KEY") else "False")
    os.environ.setdefault("LPG_IMAGE_PROVIDER_ORDER", "gemini,groq")

    img = _load_image_bytes()
    _print("src", f"len={len(img)} first8={img[:8].hex()} (ffd8=jpeg?={img[:2]==b'\\xff\\xd8'})")

    try:
        from nixe.helpers.gemini_bridge import classify_lucky_pull_bytes as classify
        ok, score, provider, reason = classify(img, 0.75, 20000.0)
        print(f"[SMOKE] result ok={ok} score={score:.3f} provider={provider} via=gemini_bridge reason={reason}")
    except Exception as e:
        print(f"[SMOKE] result ok=False score=0.000 provider=none reason={e}")

if __name__ == "__main__":
    main()
