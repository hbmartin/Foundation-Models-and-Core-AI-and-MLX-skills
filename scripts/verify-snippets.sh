#!/usr/bin/env bash
# verify-snippets.sh — compile-verify the fenced Swift snippets in guides/.
#
# Usage: ./scripts/verify-snippets.sh [--sdk 26|27|sim27]... [--guess]
#            [--changed[=REF]] [--guides PATH] [--jobs N] [--write-markers]
#            [--out DIR]
#
# Thin driver over scripts/verify-snippets.py: preflights the toolchains the
# run needs, echoes their identities (the "against 27A5228h" honesty line),
# then execs the Python. Never touches global xcode-select state — each SDK is
# resolved with a per-process DEVELOPER_DIR, per scripts/dump-sdk-interfaces.sh.
set -euo pipefail

usage() { sed -n '2,9p' "$0"; }

SCRIPT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH='' cd -- "$SCRIPT_DIR/.." && pwd)"

die() { printf 'error: %s\n' "$*" >&2; exit 1; }

command -v python3 >/dev/null 2>&1 || die 'python3 is required'
command -v xcrun >/dev/null 2>&1 || die 'xcrun is required'

for arg in "$@"; do
    case "$arg" in
        -h|--help) usage; exit 0 ;;
    esac
done

preflight() {
    local name="$1" dev_dir="$2" sdk="$3"
    [ -d "$dev_dir" ] || die "target $name: developer dir missing: $dev_dir"
    local ver build sdkver sdkbuild
    ver="$(DEVELOPER_DIR="$dev_dir" xcodebuild -version | sed -n '1s/^Xcode[[:space:]]*//p')" \
        || die "target $name: xcodebuild -version failed under $dev_dir"
    build="$(DEVELOPER_DIR="$dev_dir" xcodebuild -version | sed -n '2s/^Build version[[:space:]]*//p')"
    sdkver="$(DEVELOPER_DIR="$dev_dir" xcrun --sdk "$sdk" --show-sdk-version)" \
        || die "target $name: no $sdk SDK under $dev_dir"
    sdkbuild="$(DEVELOPER_DIR="$dev_dir" xcrun --sdk "$sdk" --show-sdk-build-version)"
    printf '# target %-6s Xcode %s (%s), %s SDK %s (%s)\n' \
        "$name" "$ver" "$build" "$sdk" "$sdkver" "$sdkbuild" >&2
}

preflight 26 /Applications/Xcode.app/Contents/Developer macosx
preflight 27 /Applications/Xcode-beta.app/Contents/Developer macosx
preflight sim27 /Applications/Xcode-beta.app/Contents/Developer iphonesimulator

cd -- "$REPO_ROOT"
exec python3 scripts/verify-snippets.py "$@"
