import re, idna
from urllib.parse import urlparse

def normalize_domain(d: str) -> str:
    d = (d or "").strip().lower()
    d = d.rstrip(".")
    try:
        # idna decode then encode to ascii (punycode canonical)
        d = idna.decode(d)
    except Exception:
        pass
    try:
        d = idna.encode(d).decode("ascii")
    except Exception:
        pass
    return d

def extract_domains(text: str):
    text = text or ""
    # crude URL pattern
    urls = re.findall(r"https?://[\w\-\.:/%#\?=&]+", text, flags=re.I)
    hosts = []
    for u in urls:
        try:
            host = urlparse(u).hostname or ""
            if host:
                hosts.append(normalize_domain(host))
        except Exception:
            pass
    # also pick bare domains like example.com
    for m in re.findall(r"([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", text):
        hosts.append(normalize_domain(m))
    return hosts
