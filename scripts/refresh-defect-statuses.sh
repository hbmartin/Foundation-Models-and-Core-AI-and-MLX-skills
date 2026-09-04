#!/usr/bin/env bash
# Compatibility entry point for the importable defect-status reporter.

set -uo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
cd "$root" || exit 1
exec python3 "$root/scripts/refresh_defect_statuses.py" "$@"
