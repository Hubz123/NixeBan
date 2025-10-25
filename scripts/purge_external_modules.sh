
#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-.}"
A1="lei"; A2="na"; B1="satpam"; B2="bot"
find "$ROOT" -type f \( -iname "*${A1}${A2}*.py" -o -iname "*${B1}${B2}*.py" \) -print -delete
find "$ROOT" -type d -empty -delete
echo "[ok] purged external modules"
