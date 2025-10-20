from __future__ import annotations
import logging
from typing import Iterable
from ..config.self_learning_cfg import NIXE_HEALTHZ_PATH, NIXE_HEALTHZ_SILENCE
HEALTHZ_PATH = NIXE_HEALTHZ_PATH
SILENCE = NIXE_HEALTHZ_SILENCE
class _DropHealthz(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try: msg = record.getMessage()
        except Exception: msg = str(record.msg)
        p = HEALTHZ_PATH
        bad = (f' {p} ' in msg) or (f'{p} HTTP' in msg) or (p in msg)
        return (not bad) if SILENCE else True
def install_quiet_accesslog(logger_names: Iterable[str] = ('werkzeug','uvicorn.access','gunicorn.access')) -> None:
    if not SILENCE: return
    f = _DropHealthz()
    for name in [''] + list(logger_names):
        try: logging.getLogger(name).addFilter(f)
        except Exception: pass
def install_flask_quiet_healthz(app):
    try: from flask import Response
    except Exception: Response = None
    @app.get(HEALTHZ_PATH)  # type: ignore[attr-defined]
    def _nixe_healthz():
        if Response is not None: return Response(status=204)
        return ('', 204)
    install_quiet_accesslog(); return app
def install_fastapi_quiet_healthz(app):
    try:
        from fastapi import APIRouter
        from starlette.responses import Response
    except Exception:
        APIRouter = None; Response = None
    if APIRouter is not None:
        r = APIRouter()
        @r.get(HEALTHZ_PATH)
        def _healthz():
            return Response(status_code=204) if Response is not None else ('', 204)
        try: app.include_router(r)  # type: ignore[attr-defined]
        except Exception:
            try: app.add_route(HEALTHZ_PATH, lambda request: Response(status_code=204), methods=['GET'])  # type: ignore[attr-defined]
            except Exception: pass
    try:
        from starlette.middleware.base import BaseHTTPMiddleware
        from starlette.requests import Request
        from starlette.responses import Response as StarletteResponse
    except Exception:
        BaseHTTPMiddleware = None; StarletteResponse = None
    if BaseHTTPMiddleware is not None and StarletteResponse is not None:
        class QuietHealthzMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next):
                if request.url.path == HEALTHZ_PATH:
                    return StarletteResponse(status_code=204)
                return await call_next(request)
        try: app.add_middleware(QuietHealthzMiddleware)  # type: ignore[attr-defined]
        except Exception: pass
    install_quiet_accesslog(); return app
