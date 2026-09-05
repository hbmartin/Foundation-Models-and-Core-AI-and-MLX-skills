#!/usr/bin/env python3
"""Shared repository mutation boundaries for automation tooling."""

ALLOWED_ROOTS = ("guides/", "notes/", "probes/", "skills/")
FORBIDDEN_PREFIXES = (
    ".github/", ".git/", "repos/", "captures/", "personal-skills/",
    "dependencies/", "/",
)
FORBIDDEN_COMPONENTS = frozenset(
    prefix.rstrip("/") for prefix in FORBIDDEN_PREFIXES if prefix != "/"
)
PROTECTED_PATHS = (
    "automations/",
    "scripts/",
)
GENERATED_OUTPUTS = (
    "skills/",
    "guides/API-INDEX.md",
    "guides/SILENT-FAILURES.md",
    "notes/README.md",
    "notes/FRESHNESS-RUNBOOK.md",
    "notes/NEXT-BETA-CHECKLIST.md",
    "probes/README.md",
)
