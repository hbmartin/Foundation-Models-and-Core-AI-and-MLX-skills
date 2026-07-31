#!/usr/bin/env bash
# The per-beta ritual: re-dump the currently-selected Xcode's SDK interfaces
# (via scripts/dump-sdk-interfaces.sh) and show, per framework, how the fresh
# capture drifts from the committed one — added/removed public declarations,
# counted and sampled, so a new beta's API drift fits on one screen. Read-only
# apart from rewriting the notes/sdk-interfaces/ dumps themselves (which is what
# dump-sdk-interfaces.sh always does); git decides what actually changed.
#
#   ./scripts/diff-interfaces.sh                          # fresh dump vs HEAD
#   ./scripts/diff-interfaces.sh --against v1.0           # ...vs another git ref
#   ./scripts/diff-interfaces.sh --baseline 26.5 --framework Speech
#                                                         # cross-major: Speech-26.5 vs newest Speech
#   ./scripts/diff-interfaces.sh --examples 20            # more sample lines per framework
#
# The drift filter keeps diff lines that begin (after indent) with
# public|open|@available|case — i.e. declaration-level changes. Doc comments,
# SPI noise and attribute reshuffles below that bar are counted but not shown.
# "clean — no drift" for every framework is the expected output when the dumps
# are freshly committed and the selected Xcode has not changed since.

set -uo pipefail
cd "$(dirname "$0")/.."
DEST="notes/sdk-interfaces"

AGAINST="HEAD"
BASELINE=""
FRAMEWORK=""
EXAMPLES=8
while [ $# -gt 0 ]; do
  case "$1" in
    --against)   AGAINST="${2:?--against needs a git ref}"; shift 2 ;;
    --baseline)  BASELINE="${2:?--baseline needs an SDK version, e.g. 26.5}"; shift 2 ;;
    --framework) FRAMEWORK="${2:?--framework needs a name, e.g. Speech}"; shift 2 ;;
    --examples)  EXAMPLES="${2:?--examples needs a number}"; shift 2 ;;
    -h|--help)   sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1 (see header of scripts/diff-interfaces.sh)" >&2; exit 2 ;;
  esac
done

# Unified-diff drift filter: keep +/- lines whose content starts with a
# declaration keyword. (+++/--- file headers don't survive the keyword match.)
DRIFT_RE='^[+-][[:space:]]*(public |open |@available|case )'

report_drift() { # $1=label  $2=diff-file
  local added removed raw
  added=$(grep -E "$DRIFT_RE" "$2" | grep -c '^+')
  removed=$(grep -E "$DRIFT_RE" "$2" | grep -c '^-')
  raw=$(grep -c '^[+-]' "$2")
  if [ ! -s "$2" ]; then
    printf "  %-28s clean — no drift\n" "$1"
  elif [ "$((added + removed))" -eq 0 ]; then
    printf "  %-28s no declaration drift (%s raw +/- lines below the filter)\n" "$1" "$raw"
  else
    printf "  %-28s +%s / -%s declaration lines (%s raw +/- lines); first %s:\n" \
      "$1" "$added" "$removed" "$raw" "$EXAMPLES"
    grep -E "$DRIFT_RE" "$2" | head -"$EXAMPLES" | sed 's/^/      /'
  fi
}

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# ---- cross-major mode: one framework, two SDK versions, plain file diff -------
if [ -n "$BASELINE" ]; then
  [ -n "$FRAMEWORK" ] || { echo "--baseline needs --framework <name> (cross-major is per-framework by design: the diffs are huge)" >&2; exit 2; }
  base="$DEST/${FRAMEWORK}-${BASELINE}-macos.swiftinterface"
  [ -f "$base" ] || { echo "no capture at $base" >&2; exit 2; }
  # Newest other capture of the same framework = highest embedded SDK version.
  newest="$(ls "$DEST/$FRAMEWORK"-*-macos.swiftinterface 2>/dev/null | grep -v "$BASELINE" | sort -V | tail -1)"
  [ -n "$newest" ] || { echo "no non-$BASELINE capture of $FRAMEWORK to compare against" >&2; exit 2; }
  echo "=== $FRAMEWORK: $(basename "$base") -> $(basename "$newest") ==="
  diff -u "$base" "$newest" > "$TMP/d" 2>/dev/null
  report_drift "$FRAMEWORK" "$TMP/d"
  exit 0
fi

# ---- normal mode: fresh dump, then git-diff each current-SDK capture ----------
./scripts/dump-sdk-interfaces.sh
echo
SDKVER="$(xcrun --sdk macosx --show-sdk-version 2>/dev/null)"
echo "=== drift of fresh ${SDKVER} dumps vs ${AGAINST} ==="

found=0
for f in "$DEST"/*-"$SDKVER"-macos.swiftinterface; do
  [ -f "$f" ] || continue
  found=1
  fw="$(basename "$f" | sed "s/-$SDKVER-macos\.swiftinterface//")"
  if [ -n "$FRAMEWORK" ] && [ "$fw" != "$FRAMEWORK" ]; then continue; fi
  if ! git cat-file -e "$AGAINST:$f" 2>/dev/null; then
    # Not in the ref at all: a brand-new capture (new framework, or first dump
    # of a new SDK version). Whole-file counts instead of a diff.
    printf "  %-28s NEW capture (absent from %s): %s lines, %s public decls\n" \
      "$fw" "$AGAINST" "$(wc -l < "$f" | tr -d ' ')" \
      "$(grep -cE '^[[:space:]]*(public |open )' "$f")"
    continue
  fi
  git diff "$AGAINST" -- "$f" > "$TMP/d"
  report_drift "$fw" "$TMP/d"
done
[ "$found" -eq 1 ] || echo "  (no $DEST/*-$SDKVER-*.swiftinterface captures found — did the dump fail?)"

echo
echo "Cross-major on request, e.g.: ./scripts/diff-interfaces.sh --baseline 26.5 --framework FoundationModels"
echo "If a new beta produced drift: commit the new dumps, then work the watch-list in notes/NEXT-BETA-CHECKLIST.md."
