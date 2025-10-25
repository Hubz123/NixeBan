#!/usr/bin/env bash
set -euo pipefail

# Target IDs (new)
NEW_LOG=1431178130155896882
NEW_DB=1431192568221270108

# Compose legacy tokens dynamically (no plain literals in file or comments)
LB="log-bot"; HY="-"; UND="_"
PHI="phi"; SING="sing"; X1="${PHI}${SING}"
PHIS="phish"; ING="ing"; X2="${PHIS}${ING}"

LEG1="${LB}${HY}${X1}"     # legacy-1
LEG2="${LB}${HY}${X2}"     # legacy-2
LEG3="log_${X1}"           # legacy-3
LEG4="log-${X2}"           # legacy-4
LEG5="log-${X1}"           # legacy-5
LEG_SET="(${LEG1}|${LEG2}|${LEG3}|${LEG4}|${LEG5})"

echo "[1/5] Patch hardcoded IDs in nixe/config.py and nixe/config_phash.py"
if [[ -f nixe/config.py ]]; then
  sed -i -E "s/(THREAD_NIXE\s*=\s*)[0-9]+/\1 ${NEW_DB}/" nixe/config.py || true
  sed -i -E "s/(LOG_BOTPHISHING\s*=\s*)[0-9]+/\1 ${NEW_LOG}/" nixe/config.py || true
fi
if [[ -f nixe/config_phash.py ]]; then
  sed -i -E "s/(PHASH_DB_THREAD_ID\s*=\s*)[0-9]+/\1 ${NEW_DB}/" nixe/config_phash.py || true
fi

echo "[2/5] Replace legacy channel-name fallbacks with 'nixe-only'"
targets=(
  "nixe/cogs/phash_auto_ban.py"
  "nixe/cogs/phash_match_guard.py"
  "nixe/helpers/banlog.py"
)
for f in "${targets[@]}"; do
  [[ -f "$f" ]] || continue
  # Collapse any set containing a legacy token -> {'nixe-only'}
  perl -0777 -pe "s/\{[^}]*'${LEG_SET}'[^}]*\}/\{'nixe-only'\}/gi" -i "$f" || true
  # Replace standalone occurrences of any legacy token -> 'nixe-only'
  perl -0777 -pe "s/(['\"])${LEG_SET}\1/'nixe-only'/gi" -i "$f" || true
done

echo "[3/5] Optional doc defaults -> 'nixe-only'"
for f in README.md render.yaml; do
  [[ -f "$f" ]] || continue
  sed -i -E "s/${LEG1}/nixe-only/gi" "$f" || true
  sed -i -E "s/${LEG2}/nixe-only/gi" "$f" || true
done

echo "[4/5] Clear caches"
find . -type d -name "__pycache__" -prune -exec rm -rf {} + || true
find . -type f -name "*.pyc" -delete || true

echo "[5/5] Verify (should print nothing):"
grep -R "${LEG1}" -n . || true
grep -R "${LEG2}" -n . || true
grep -R "${LEG3}" -n . || true
grep -R "${LEG4}" -n . || true
grep -R "${LEG5}" -n . || true
# IDs (compose to avoid raw literals here too)
OLDA=1400375; OLDB=1840487; OLDC=87566
OLDID="${OLDA}${OLDB}${OLDC}"
ODA=1430048; ODB=8395569; ODC=27589
OLDDB="${ODA}${ODB}${ODC}"
grep -R "${OLDID}" -n . || true
grep -R "${OLDDB}" -n . || true

echo "Done."
