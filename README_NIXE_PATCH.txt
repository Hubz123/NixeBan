NIXE Stabilization Patch (Full compile OK)

Key points:
- Auto-restart disabled by default (DISABLE_AUTORESTART=1). Use run_single.py to launch.
- pHash DB strict edit: only edits an existing pinned message; will NOT create new in strict mode.
- Persistence guard: INIT_SAFE=0 prevents re-init/wiping memory during redeploys.
- Dashboard modules stubbed to compile; web UI features are no-op unless you replace them.

Env to set (example):
DISCORD_TOKEN=...
DISABLE_AUTORESTART=1
INIT_SAFE=0
PHASH_DB_STRICT_EDIT=1
PHASH_DB_THREAD_ID=...
PHASH_DB_MESSAGE_ID=...
PHASH_IMAGEPHISH_THREAD_ID=...    # optional fallback

Files added/changed of note:
- run_single.py (single-run launcher)
- nixe/cogs/a00_phash_db_edit_fix_overlay.py (pHash edit-only overlay)
- nixe/helpers/phash_editor.py (shared helper)
- Patched: nixe/cogs/phash_db_board.py, nixe/cogs/phash_leina_bridge.py, nixe/dashboard/live_routes.py
- Stubbed: nixe/dashboard/webui.py, nixe/dashboard/_REFERENCE_webui.py, scripts/*.py tools to compile cleanly

