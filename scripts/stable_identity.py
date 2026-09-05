#!/usr/bin/env python3
"""Stable semantic identifiers shared by corpus maintenance tools."""

from __future__ import annotations

import hashlib
import re
import unicodedata


SAFE_EXPLICIT_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{0,79}$")


def normalize(value: str) -> str:
    """Normalize human-authored Markdown without changing its meaning."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", value)).strip()


def content_hash(*parts: str) -> str:
    """Hash normalized prose or identity metadata."""
    payload = "\x1f".join(normalize(part) for part in parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def source_content_hash(*parts: str) -> str:
    """Hash source text losslessly so whitespace-only code edits require review."""
    payload = "\x1f".join(parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def semantic_id(prefix: str, *parts: str, explicit: str | None = None) -> str:
    if explicit is not None:
        value = normalize(explicit).lower()
        if not SAFE_EXPLICIT_ID.fullmatch(value):
            raise ValueError(
                "explicit identity must be 1-80 lowercase letters, numbers, dots, "
                "underscores, or hyphens"
            )
        return value
    return f"{prefix}-{content_hash(*parts)[:16]}"
