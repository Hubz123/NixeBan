
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Apply minimal concurrency patch to main.py so Uvicorn and Discord bot run concurrently.
- Keeps the exact logging lines already present ("Starting Uvicorn web server...", "Starting Discord bot task...").
- Replaces blocking awaits with asyncio.create_task + wait(FIRST_EXCEPTION).
Run:
    python scripts/patch_concurrency_main.py
"""
import re, sys, io, os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
target = ROOT / "main.py"
if not target.exists():
    print("[PATCH] main.py not found at", target)
    sys.exit(2)

src = target.read_text(encoding="utf-8")

# Heuristic 1: replace a common sequential pattern with concurrent form
pattern = re.compile(
    r'(log\.info\("Starting Uvicorn web server\.*?"\)\s*\n\s*)(await\s+run_uvicorn\(\)\s*\n\s*)(log\.info\("Starting Discord bot task\.*?"\)\s*\n\s*)(await\s+[^\n]*shim_runner\.start_bot\(\)\s*)',
    re.DOTALL
)

replacement = (
    r''
    r'web_task = asyncio.create_task(run_uvicorn(), name="uvicorn-server")\n'
    r'\3'
    r'bot_task = asyncio.create_task(shim_runner.start_bot(), name="discord-bot")\n'
    r'\n'
    r'    done, pending = await asyncio.wait({web_task, bot_task}, return_when=asyncio.FIRST_EXCEPTION)\n'
    r'    crashed = False\n'
    r'    for t in done:\n'
    r'        exc = t.exception()\n'
    r'        if exc:\n'
    r'            crashed = True\n'
    r'            log.error("Background task crashed: %r", exc, exc_info=True)\n'
    r'    if crashed:\n'
    r'        for t in pending:\n'
    r'            t.cancel()\n'
    r'        await asyncio.gather(*pending, return_exceptions=True)\n'
)

out, n = pattern.subn(replacement, src)

if n == 0:
    # Heuristic 2: insert a non-blocking start even if run_uvicorn() was not awaited immediately
    # We find the first "Starting Uvicorn web server..." and ensure the next await run_uvicorn is turned into a task.
    src2 = src
    src2 = re.sub(r'(log\.info\("Starting Uvicorn web server.*?"\)\s*\n\s*)await\s+run_uvicorn\(\)',
                  r'web_task = asyncio.create_task(run_uvicorn(), name="uvicorn-server")',
                  src2)
    src2 = re.sub(r'(log\.info\("Starting Discord bot task.*?"\)\s*\n\s*)await\s*([^\n]*shim_runner\.start_bot\(\))',
                  r'bot_task = asyncio.create_task(\2, name="discord-bot")\n'
                  r'    done, pending = await asyncio.wait({web_task, bot_task}, return_when=asyncio.FIRST_EXCEPTION)\n'
                  r'    crashed = False\n'
                  r'    for t in done:\n'
                  r'        exc = t.exception()\n'
                  r'        if exc:\n'
                  r'            crashed = True\n'
                  r'            log.error("Background task crashed: %r", exc, exc_info=True)\n'
                  r'    if crashed:\n'
                  r'        for t in pending:\n'
                  r'            t.cancel()\n'
                  r'        await asyncio.gather(*pending, return_exceptions=True)',
                  src2)
    out2 = src2
    if out2 != src:
        target.write_text(out2, encoding="utf-8")
        print("[PATCH] Applied heuristic concurrency patch to main.py")
        sys.exit(0)
    else:
        print("[PATCH] No change applied. Please patch manually.")
        sys.exit(3)
else:
    target.write_text(out, encoding="utf-8")
    print("[PATCH] Applied concurrency patch to main.py")
