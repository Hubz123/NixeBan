# -*- coding: utf-8 -*-
from __future__ import annotations

# ASGI wrapper for Flask app so uvicorn can serve it
from uvicorn.middleware.wsgi import WSGIMiddleware  # type: ignore
try:
    from app import app as _flask_app  # Flask WSGI app exported by Leina
except Exception as e:
    _flask_app = None
    _import_err = e

if _flask_app is None:
    raise RuntimeError(f"Failed to import Flask app: {_import_err}")

# Expose ASGI app for uvicorn
app = WSGIMiddleware(_flask_app)
