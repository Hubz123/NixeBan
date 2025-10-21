from __future__ import annotations
import logging, inspect
try:
    from nixe.context_flags import should_skip_phash
except Exception:
    def should_skip_phash(_): return False
log = logging.getLogger(__name__)
def _wrap(fn):
    if not callable(fn) or getattr(fn, "_nixe_wrapped_skip", False): return fn
    if inspect.iscoroutinefunction(fn):
        async def awrap(*a, **kw):
            msg = kw.get("message")
            if msg is None and a:
                for x in a:
                    if getattr(x, "id", None) is not None and getattr(x, "attachments", None) is not None:
                        msg = x; break
            if msg is not None and should_skip_phash(getattr(msg, "id", None)): return None
            return await fn(*a, **kw)
        awrap._nixe_wrapped_skip=True; return awrap
    def swrap(*a, **kw):
        msg = kw.get("message")
        if msg is None and a:
            for x in a:
                if getattr(x, "id", None) is not None and getattr(x, "attachments", None) is not None:
                    msg = x; break
        if msg is not None and should_skip_phash(getattr(msg, "id", None)): return None
        return fn(*a, **kw)
    swrap._nixe_wrapped_skip=True; return swrap
def _try_patch(mod_name: str, names: list[str]) -> int:
    try: mod = __import__(mod_name, fromlist=["*"])
    except Exception: return 0
    n=0
    for nm in names:
        fn = getattr(mod, nm, None)
        if fn is None: continue
        wrapped = _wrap(fn)
        if wrapped is not fn:
            try: setattr(mod, nm, wrapped); n+=1
            except Exception: pass
    if n: log.info("[patch_collect_phash] patched %s", mod_name)
    return n
async def setup(_bot):
    total=0
    total+=_try_patch("nixe.cogs.phash_inbox_watcher", ["collect","collect_phash","handle"])
    total+=_try_patch("nixe.cogs.image_phish_guard", ["collect","collect_phash","handle"])
    total+=_try_patch("nixe.cogs.phash_runtime_log_tamer", ["collect","collect_phash","handle"])
    if not total: log.info("[patch_collect_phash] no targets found; noop")
