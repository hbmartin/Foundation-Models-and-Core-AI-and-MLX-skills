#!/usr/bin/env bash
# Regenerate guides/SILENT-FAILURES.md and guides/API-INDEX.md from the current guides.
#
#   ./scripts/build-indexes.sh [classified-dir]
#
# The default classified directory is committed at
# notes/synthesis/callout-classifications/. An override holds one part-NN.tsv
# per part with rows
#   file<TAB>line<TAB>anchor<TAB>kind<TAB>symptom-id<TAB>blurb
# (symptom ids per notes/synthesis/SYMPTOM-TAXONOMY.md). Classification is the
# one step that needs judgment: re-run scripts/extract-callouts.py, classify any
# NEW rows, then invoke this. The symbol side is fully automatic.
set -euo pipefail
cd "$(dirname "$0")/.."
if [ "$#" -gt 1 ]; then
  echo "usage: build-indexes.sh [classified-dir]" >&2
  exit 2
fi
CLASSIFIED="${1:-notes/synthesis/callout-classifications}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
python3 scripts/extract-callouts.py guides > "$TMP/callouts.tsv"
python3 scripts/extract-symbols.py > "$TMP/symbols.tsv"
python3 scripts/build-indexes.py "$CLASSIFIED" "$TMP/callouts.tsv" "$TMP/symbols.tsv" guides guides
echo "Wrote guides/SILENT-FAILURES.md and guides/API-INDEX.md"
