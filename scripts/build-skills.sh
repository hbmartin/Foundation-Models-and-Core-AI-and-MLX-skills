#!/usr/bin/env bash
# Regenerate skills/ from guides/.
#
# guides/ is canonical and is never written by this script; scripts/tests/test_skills.py
# asserts that, and asserts the committed tree matches a clean regeneration.
# Run this after ./scripts/build-indexes.sh whenever guide headings, callouts or
# API references change.
#
# Usage: ./scripts/build-skills.sh [skill-manifest.json]
set -euo pipefail

cd "$(dirname "$0")/.."

MANIFEST="${1:-notes/synthesis/skill-manifest.json}"

python3 scripts/build-skills.py \
    --source guides \
    --skills skills \
    --manifest "$MANIFEST" \
    --repository-root .

python3 scripts/verify-skills.py --skills skills
