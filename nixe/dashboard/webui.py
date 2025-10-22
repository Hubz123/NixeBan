# Minimal webui stubs for NIXE (compile-safe)
from __future__ import annotations
from typing import Optional
from flask import Response

def _ensure_gtake_layout_signature(html: str) -> str: return html
def _ensure_gtake_css(html: str) -> str: return html
def _ensure_canvas(html: str) -> str: return html
def _ensure_dropzone(html: str) -> str: return html
def _ensure_dashboard_dropzone(html: str) -> str: return html
def _ensure_smokemarkers_dashboard(html: str) -> str: return html

def _extract_theme_from_request() -> str: return "gtake"
def _set_theme_value(val: Optional[str]) -> dict: return {"ok": True, "theme": (val or "gtake")}

def after_request_filter(resp):
    # No-op HTML injection; simply return the response
    return resp


def register_webui_builtin(app):
    # No-op for this build
    return None
