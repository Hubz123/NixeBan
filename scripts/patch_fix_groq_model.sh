#!/usr/bin/env bash
set -e
f="nixe/helpers/gemini_bridge.py"
bak="nixe/helpers/gemini_bridge.py.bak.$(date +%s)"
cp -v "$f" "$bak"
sed -i -E 's@os\.environ\.get\("LPG_GROQ_MODEL","meta-llama/llama-4-scout-17b-16e-instruct"\)@(os.environ.get("GROQ_MODEL") or os.environ.get("LPG_GROQ_MODEL") or "llama-3.1-8b-instant")@' "$f"
echo "[OK] Patched $f (backup: $bak)"
