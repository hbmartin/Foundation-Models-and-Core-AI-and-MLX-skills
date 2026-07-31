#!/usr/bin/env bash
# Regenerate guides/SILENT-FAILURES.md and guides/API-INDEX.md from the current guides.
#
#   ./scripts/build-indexes.sh notes/synthesis/callout-classification
#
# The classified dir holds one part-NN.tsv per part with rows
#   file<TAB>line<TAB>anchor<TAB>kind<TAB>symptom-id<TAB>blurb
# (symptom ids per notes/synthesis/SYMPTOM-TAXONOMY.md). Classification is the
# one step that needs judgment: re-run scripts/extract-callouts.py, classify any
# NEW rows, then invoke this. The symbol side is fully automatic.
set -euo pipefail
cd "$(dirname "$0")/.."
CLASSIFIED="${1:?usage: build-indexes.sh <classified-dir>}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
python3 scripts/extract-symbols.py > "$TMP/symbols.tsv"
python3 scripts/build-indexes.py "$CLASSIFIED" "$TMP/symbols.tsv" guides guides
echo "Wrote guides/SILENT-FAILURES.md and guides/API-INDEX.md"
