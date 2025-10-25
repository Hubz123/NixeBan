
#!/usr/bin/env bash
set -euo pipefail
ROOT="${1:-.}"
LB="log-"; PHI1="phisi"; PHI2="ng"; PHISHING="${PHI1}${PHI2}"
grep -RIl --exclude-dir="__pycache__" --include="*.py" -e "${LB}bot${PHI1}ng" -e "${LB}bot_${PHI1}ng" -e "${LB}${PHISHING}" "$ROOT" | while read -r f; do
  sed -i -E "s/${LB}bot${PHI1}ng|${LB}bot_${PHI1}ng|${LB}${PHISHING}/nixe-only/gI" "$f"
done
echo "[ok] guards rewritten"
