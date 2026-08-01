#!/usr/bin/env bash
# verify-snippets.sh — compile-verify the fenced Swift snippets in guides/.
#
# Usage: ./scripts/verify-snippets.sh [--sdk 26|27|27-on-26|sim27|sim27-on-26]... [--guess]
#            [--changed[=REF]] [--guides PATH] [--jobs N] [--write-markers]
#            [--out DIR]
#
# Thin driver over scripts/verify-snippets.py. Python resolves exactly the
# marker-requested plus explicitly added targets and records their identities;
# the shell does not duplicate marker parsing or preflight unrelated Xcodes.
set -euo pipefail

usage() { sed -n '2,6p' "$0"; }

SCRIPT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH='' cd -- "$SCRIPT_DIR/.." && pwd)"

die() { printf 'error: %s\n' "$*" >&2; exit 1; }

command -v python3 >/dev/null 2>&1 || die 'python3 is required'

for arg in "$@"; do
    case "$arg" in
        -h|--help) usage; exit 0 ;;
    esac
done

cd -- "$REPO_ROOT"
exec python3 scripts/verify-snippets.py "$@"
