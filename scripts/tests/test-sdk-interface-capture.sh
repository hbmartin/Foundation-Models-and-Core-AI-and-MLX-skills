#!/usr/bin/env bash
# Focused integration tests for destination safety and idempotence. These tests
# intentionally use the selected real Xcode/Metal Toolchain because the capture
# script's preflight is itself part of the contract under test.

set -euo pipefail

SCRIPT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH='' cd -- "$SCRIPT_DIR/../.." && pwd)"
DUMP="$REPO_ROOT/scripts/dump-sdk-interfaces.sh"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-sdk-capture.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT HUP INT TERM

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  exit 1
}

expect_failure() { # $1=expected fragment; remaining args=command
  local expected="$1"
  shift
  if "$@" > "$TMP/stdout" 2> "$TMP/stderr"; then
    fail "command unexpectedly succeeded: $*"
  fi
  grep -F -q "$expected" "$TMP/stderr" || {
    sed -n '1,80p' "$TMP/stderr" >&2
    fail "failure did not contain: $expected"
  }
}

# PATH shims exercise early preflight branches without changing global Xcode
# selection or requiring a second installation.
SHIM_ROOT="$TMP/shim"
SHIM_BIN="$SHIM_ROOT/bin"
SHIM_COMPONENT_ROOT="$SHIM_ROOT/component"
SHIM_TOOLCHAIN="$SHIM_COMPONENT_ROOT/Metal.xctoolchain"
mkdir -p "$SHIM_BIN" "$SHIM_TOOLCHAIN/usr/bin"

cat > "$SHIM_BIN/xcodebuild" <<'SH'
#!/usr/bin/env bash
set -eu
if [ "${DEVELOPER_DIR-}" = "${SDK_EXPECT_DEVELOPER_DIR-}" ] && [ -n "${SDK_EXPECT_DEVELOPER_DIR-}" ]; then
  printf 'seen\n' > "$SDK_SHIM_ROOT/xcodebuild-developer-dir"
fi
case "${1-}" in
  -version)
    printf 'Xcode %s\nBuild version %s\n' "${SDK_SHIM_XCODE_VERSION:-27.0}" "${SDK_SHIM_XCODE_BUILD:-TEST27A}"
    ;;
  -showComponent)
    printf 'Asset Path: /System/Library/AssetsV2/test\n'
    printf 'Build Version: %s\n' "${SDK_SHIM_COMPONENT_BUILD:-TEST27M}"
    printf 'Status: installed\n'
    printf 'Toolchain Identifier: %s\n' "${SDK_SHIM_COMPONENT_IDENTIFIER:-com.example.Metal}"
    printf 'Toolchain Search Path: %s\n' "$SDK_SHIM_ROOT/component"
    ;;
  *) exit 2 ;;
esac
SH

cat > "$SHIM_BIN/xcrun" <<'SH'
#!/usr/bin/env bash
set -eu
if [ "${DEVELOPER_DIR-}" = "${SDK_EXPECT_DEVELOPER_DIR-}" ] && [ -n "${SDK_EXPECT_DEVELOPER_DIR-}" ]; then
  printf 'seen\n' > "$SDK_SHIM_ROOT/xcrun-developer-dir"
fi
case "$*" in
  '--sdk iphoneos --show-sdk-version') printf '%s\n' "${SDK_SHIM_IPHONE_VERSION:-27.0}" ;;
  '--sdk iphoneos --show-sdk-build-version') printf '%s\n' "${SDK_SHIM_IPHONE_BUILD:-TESTIOS}" ;;
  '--sdk iphoneos --show-sdk-path') printf '%s\n' "$SDK_SHIM_ROOT/iPhoneOS.sdk" ;;
  '--sdk macosx --show-sdk-version') printf '%s\n' "${SDK_SHIM_MACOS_VERSION:-14.0}" ;;
  '--sdk macosx --show-sdk-build-version') printf '%s\n' "${SDK_SHIM_MACOS_BUILD:-TESTMAC}" ;;
  '--sdk macosx --show-sdk-path') printf '%s\n' "$SDK_SHIM_ROOT/MacOSX.sdk" ;;
  '--sdk macosx --show-sdk-platform-path') printf '%s\n' "$SDK_SHIM_ROOT/MacOSX.platform" ;;
  '--no-cache --find coreai-build')
    [ "${SDK_SHIM_MISSING_COREAI:-0}" -eq 0 ] || exit 1
    printf '%s\n' "$SDK_SHIM_ROOT/component/Metal.xctoolchain/usr/bin/coreai-build"
    ;;
  '--no-cache --find metal') printf '%s\n' "$SDK_SHIM_ROOT/component/Metal.xctoolchain/usr/bin/metal" ;;
  '--no-cache --find fm') exit 1 ;;
  *) exit 2 ;;
esac
SH

cat > "$SHIM_TOOLCHAIN/usr/bin/coreai-build" <<'SH'
#!/usr/bin/env bash
[ "${1-}" = '--version' ] && { printf 'coreai-build test\n'; exit 0; }
printf 'test help\n'
SH
cat > "$SHIM_TOOLCHAIN/usr/bin/metal" <<'SH'
#!/usr/bin/env bash
[ "${1-}" = '--version' ] && { printf 'Apple metal test\n'; exit 0; }
exit 2
SH
cat > "$SHIM_TOOLCHAIN/ToolchainInfo.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict><key>Identifier</key><string>com.example.Metal</string></dict></plist>
PLIST
chmod +x "$SHIM_BIN/xcodebuild" "$SHIM_BIN/xcrun" \
  "$SHIM_TOOLCHAIN/usr/bin/coreai-build" "$SHIM_TOOLCHAIN/usr/bin/metal"

SHIM_ENV=(env PATH="$SHIM_BIN:$PATH" SDK_SHIM_ROOT="$SHIM_ROOT")
expect_failure 'Xcode 27 or newer is required' "${SHIM_ENV[@]}" \
  SDK_SHIM_XCODE_VERSION=26.4 "$DUMP" --dest "$TMP/xcode26" --check-only
expect_failure 'iPhoneOS SDK 27 or newer is required' "${SHIM_ENV[@]}" \
  SDK_SHIM_IPHONE_VERSION=26.5 "$DUMP" --dest "$TMP/iphone26" --check-only
expect_failure 'coreai-build is missing' "${SHIM_ENV[@]}" \
  SDK_SHIM_MISSING_COREAI=1 "$DUMP" --dest "$TMP/no-coreai" --check-only
expect_failure 'component identifier does not match ToolchainInfo.plist' "${SHIM_ENV[@]}" \
  SDK_SHIM_COMPONENT_IDENTIFIER=com.example.OldMetal "$DUMP" --dest "$TMP/old-component" --check-only

selected_developer_dir='/Applications/Test-Xcode.app/Contents/Developer'
"${SHIM_ENV[@]}" DEVELOPER_DIR="$selected_developer_dir" \
  SDK_EXPECT_DEVELOPER_DIR="$selected_developer_dir" \
  "$DUMP" --dest "$TMP/shim-check" --check-only >/dev/null
[ -f "$SHIM_ROOT/xcodebuild-developer-dir" ] || fail 'xcodebuild did not receive DEVELOPER_DIR'
[ -f "$SHIM_ROOT/xcrun-developer-dir" ] || fail 'xcrun did not receive DEVELOPER_DIR'

# --check-only must not create its destination.
check_dest="$TMP/check-only-does-not-exist"
"$DUMP" --dest "$check_dest" --check-only >/dev/null
[ ! -e "$check_dest" ] || fail '--check-only created its destination'

# Capture-shaped files without a manifest are rejected.
unmanaged_dest="$TMP/unmanaged"
mkdir -p "$unmanaged_dest"
printf 'unmanaged\n' > "$unmanaged_dest/Fake-27.0-macos.swiftinterface"
expect_failure 'destination contains unmanaged capture artifacts' \
  "$DUMP" --dest "$unmanaged_dest" --check-only

# A managed file whose bytes differ from its digest is rejected.
mismatch_dest="$TMP/hash-mismatch"
mkdir -p "$mismatch_dest"
printf 'changed\n' > "$mismatch_dest/Fake-27.0-macos.swiftinterface"
python3 - "$mismatch_dest/capture-manifest.json" <<'PY'
import json
import pathlib
import sys
path = pathlib.Path(sys.argv[1])
path.write_text(json.dumps({
    "schema_version": 1,
    "captures": [{
        "capture_id": "fixture",
        "xcode": {"version": "27.0", "build": "fixture"},
        "files": [{
            "path": "Fake-27.0-macos.swiftinterface",
            "sha256": "0" * 64,
        }],
    }],
}) + "\n", encoding="utf-8")
PY
expect_failure 'manifest hash mismatch for Fake-27.0-macos.swiftinterface' \
  "$DUMP" --dest "$mismatch_dest" --check-only

# A second capture from the same selected build must be byte-idempotent.
capture_dest="$TMP/capture"
"$DUMP" --dest "$capture_dest" >/dev/null
before="$(shasum -a 256 "$capture_dest/capture-manifest.json" | awk '{print $1}')"
"$DUMP" --dest "$capture_dest" >/dev/null
after="$(shasum -a 256 "$capture_dest/capture-manifest.json" | awk '{print $1}')"
[ "$before" = "$after" ] || fail 'same-build recapture changed the manifest'

# Reassigning those stable paths to another build makes the next capture stop.
python3 - "$capture_dest/capture-manifest.json" <<'PY'
import json
import pathlib
import sys
path = pathlib.Path(sys.argv[1])
manifest = json.loads(path.read_text(encoding="utf-8"))
manifest["captures"][0]["capture_id"] = "fixture-different-build"
manifest["captures"][0]["xcode"]["build"] = "DIFFERENT-BUILD"
path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
PY
expect_failure 'refusing cross-build replacement' "$DUMP" --dest "$capture_dest"

# Scripted evidence must not leak local user or volume roots.
if grep -R -E -q '/Users/|/Volumes/' "$TMP/capture"; then
  fail 'capture contains a machine-specific path'
fi

printf 'PASS: SDK capture safety and idempotence\n'
