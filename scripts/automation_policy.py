#!/usr/bin/env python3
"""Shared repository mutation boundaries for automation tooling."""

ALLOWED_ROOTS = ("guides/", "notes/", "probes/", "scripts/", "skills/", "automations/")
FORBIDDEN_PREFIXES = (".github/", ".git/", "repos/", "captures/", "/")
GENERATED_OUTPUTS = (
    "skills/",
    "guides/API-INDEX.md",
    "guides/SILENT-FAILURES.md",
    "notes/README.md",
    "notes/FRESHNESS-RUNBOOK.md",
    "notes/NEXT-BETA-CHECKLIST.md",
    "probes/README.md",
)
