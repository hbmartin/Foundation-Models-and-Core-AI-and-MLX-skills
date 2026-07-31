#!/usr/bin/env bash
# Compare a temporary capture of the selected Xcode against committed evidence.
# Normal mode never rewrites notes/sdk-interfaces. Cross-major mode compares two
# already-tracked SDK versions and is also read-only.
#
#   ./scripts/diff-interfaces.sh
#   ./scripts/diff-interfaces.sh --against v1.0
#   ./scripts/diff-interfaces.sh --framework Speech --examples 20
#   ./scripts/diff-interfaces.sh --baseline 26.5 --framework Speech

set -euo pipefail

SCRIPT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH='' cd -- "$SCRIPT_DIR/.." && pwd)"
CAPTURE_SCRIPT="$SCRIPT_DIR/dump-sdk-interfaces.sh"
TRACKED_DIR="$REPO_ROOT/notes/sdk-interfaces"

AGAINST='HEAD'
BASELINE=''
FRAMEWORK=''
EXAMPLES=8

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

need_value() {
  [ "$#" -ge 2 ] && [ -n "$2" ] || die "$1 needs a value"
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --against)
      need_value "$@"
      AGAINST="$2"
      shift 2
      ;;
    --baseline)
      need_value "$@"
      BASELINE="$2"
      shift 2
      ;;
    --framework)
      need_value "$@"
      FRAMEWORK="$2"
      shift 2
      ;;
    --examples)
      need_value "$@"
      EXAMPLES="$2"
      shift 2
      ;;
    -h|--help)
      sed -n '2,9p' "$0"
      exit 0
      ;;
    *)
      die "unknown argument: $1"
      ;;
  esac
done

case "$EXAMPLES" in
  ''|*[!0-9]*) die '--examples must be a non-negative integer' ;;
esac

# Unified-diff filter for public surface changes. The raw-line count is also
# reported so changes below this intentionally narrow filter remain visible.
DRIFT_RE='^[+-][[:space:]]*(public |open |@available|case )'

report_drift() { # $1=label, $2=unified-diff file
  local label="$1"
  local diff_file="$2"
  local added removed raw
  added="$(grep -E "$DRIFT_RE" "$diff_file" | grep -c '^+' || true)"
  removed="$(grep -E "$DRIFT_RE" "$diff_file" | grep -c '^-' || true)"
  raw="$(grep -E -c '^[+-]' "$diff_file" || true)"
  if [ ! -s "$diff_file" ]; then
    printf '  %-32s clean — no drift\n' "$label"
  elif [ "$((added + removed))" -eq 0 ]; then
    printf '  %-32s no declaration drift (%s raw +/- lines)\n' "$label" "$raw"
  else
    printf '  %-32s +%s / -%s declaration lines (%s raw +/- lines); first %s:\n' \
      "$label" "$added" "$removed" "$raw" "$EXAMPLES"
    if [ "$EXAMPLES" -gt 0 ]; then
      grep -E "$DRIFT_RE" "$diff_file" | head -n "$EXAMPLES" | sed 's/^/      /' || true
    fi
  fi
}

TMP="$(mktemp -d "${TMPDIR:-/tmp}/sdk-interface-diff.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT HUP INT TERM

# ---- Cross-major mode: compare two tracked snapshots; no Xcode required. ------
if [ -n "$BASELINE" ]; then
  [ -n "$FRAMEWORK" ] || \
    die '--baseline requires --framework (cross-major diffs are intentionally per-framework)'
  base="$TRACKED_DIR/${FRAMEWORK}-${BASELINE}-macos.swiftinterface"
  [ -f "$base" ] || die "no tracked capture for $FRAMEWORK at SDK $BASELINE"
  newest="$(find "$TRACKED_DIR" -maxdepth 1 -type f \
    -name "${FRAMEWORK}-*-macos.swiftinterface" -print | \
    grep -v -- "-${BASELINE}-macos.swiftinterface$" | LC_ALL=C sort -V | tail -n 1 || true)"
  [ -n "$newest" ] || die "no non-$BASELINE capture of $FRAMEWORK is tracked"
  printf '=== %s: %s -> %s ===\n' "$FRAMEWORK" "$(basename "$base")" "$(basename "$newest")"
  diff -u "$base" "$newest" > "$TMP/diff" || true
  report_drift "$FRAMEWORK" "$TMP/diff"
  exit 0
fi

# ---- Normal mode: capture elsewhere, then compare bytes to a git object. ------
git -C "$REPO_ROOT" rev-parse --verify "$AGAINST^{commit}" >/dev/null 2>&1 || \
  die "unknown git revision: $AGAINST"

FRESH_DIR="$TMP/fresh"
"$CAPTURE_SCRIPT" --dest "$FRESH_DIR"

read -r SDK_VERSION XCODE_BUILD <<EOF
$(python3 - "$FRESH_DIR/capture-manifest.json" <<'PY'
import json
import pathlib
import sys
manifest = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
capture = manifest["captures"][-1]
print(capture["sdks"]["macosx"]["version"], capture["xcode"]["build"])
PY
)
EOF

printf '\n=== temporary Xcode %s / SDK %s capture vs %s ===\n' \
  "$XCODE_BUILD" "$SDK_VERSION" "$AGAINST"
found=0
for fresh in "$FRESH_DIR"/*-"$SDK_VERSION"-macos.swiftinterface; do
  [ -f "$fresh" ] || continue
  framework="$(basename "$fresh" | sed "s/-${SDK_VERSION}-macos\.swiftinterface$//")"
  if [ -n "$FRAMEWORK" ] && [ "$framework" != "$FRAMEWORK" ]; then
    continue
  fi
  found=1
  name="$(basename "$fresh")"
  tracked_path="notes/sdk-interfaces/$name"
  if ! git -C "$REPO_ROOT" cat-file -e "$AGAINST:$tracked_path" 2>/dev/null; then
    printf '  %-32s NEW capture: %s lines, %s public declarations\n' \
      "$framework" "$(wc -l < "$fresh" | tr -d ' ')" \
      "$(grep -E -c '^[[:space:]]*(public |open )' "$fresh" || true)"
    continue
  fi
  git -C "$REPO_ROOT" show "$AGAINST:$tracked_path" > "$TMP/baseline"
  diff -u "$TMP/baseline" "$fresh" > "$TMP/diff" || true
  report_drift "$framework" "$TMP/diff"
done

[ "$found" -eq 1 ] || die "no matching SDK $SDK_VERSION interface captures were produced"

printf '\nTracked evidence was not modified. To retain this candidate, run:\n'
printf '  ./scripts/dump-sdk-interfaces.sh --dest <empty-candidate-directory>\n'
printf 'Promotion is a reviewed file-and-manifest change; see notes/sdk-interfaces/README.md.\n'
