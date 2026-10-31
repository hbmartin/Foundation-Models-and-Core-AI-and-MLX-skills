#!/usr/bin/env python3
"""Shared repository mutation boundaries for automation tooling."""

import pathlib
import subprocess


def primary_checkout(repository: pathlib.Path) -> pathlib.Path:
    """Resolve a linked worktree to its repository's stable primary checkout."""
    result = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "--path-format=absolute", "--git-common-dir"],
        text=True, capture_output=True, check=False,
    )
    if result.returncode == 0:
        common = pathlib.Path(result.stdout.strip()).resolve()
        if common.name == ".git":
            return common.parent
    return repository.resolve()

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
