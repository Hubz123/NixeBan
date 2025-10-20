from __future__ import annotations
import re, urllib.parse
URL_RE = re.compile(r'https?://[^\s)\]">]+', re.I)
def extract_urls(text: str):
    if not text: return []
    return URL_RE.findall(text)
def domain_from_url(url: str):
    try:
        netloc = urllib.parse.urlparse(url).netloc.lower()
        return netloc.split(':')[0]
    except Exception:
        return ''
