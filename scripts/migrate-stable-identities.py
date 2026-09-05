#!/usr/bin/env python3
"""One-time migration of line-keyed callout and snippet TSVs to semantic IDs."""

from __future__ import annotations

import argparse
import csv
import os
import pathlib
import subprocess
import sys
import tempfile


ROOT = pathlib.Path(__file__).resolve().parents[1]


def atomic_write(path: pathlib.Path, text: str) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            output.write(text)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def command_rows(command: list[str]) -> list[list[str]]:
    process = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    if process.returncode not in (0, 1):
        raise SystemExit(process.stderr.strip() or f"command failed: {' '.join(command)}")
    # Repository TSVs deliberately use literal quotes rather than CSV quoting.
    return [line.split("\t") for line in process.stdout.splitlines()]


def migrate_callouts(classified_dir: pathlib.Path, write: bool) -> int:
    extracted = command_rows([sys.executable, str(ROOT / "scripts/extract-callouts.py"),
                              str(ROOT / "guides")])
    by_legacy = {
        (row[0], row[1], row[2], row[3]): (row[6], row[7])
        for row in extracted if len(row) == 8
    }
    changed = 0
    for path in sorted(classified_dir.glob("*.tsv")):
        text = path.read_text(encoding="utf-8")
        if "# schema-version: 2" in text.splitlines()[:3]:
            continue
        output = ["# schema-version: 2"]
        for number, line in enumerate(text.splitlines(), 1):
            if not line or line.startswith("#"):
                continue
            row = line.split("\t")
            if len(row) != 6:
                raise SystemExit(f"{path}:{number}: expected 6 columns")
            key = tuple(row[:4])
            identity = by_legacy.get(key)
            if identity is None:
                raise SystemExit(
                    f"{path}:{number}: exact legacy callout no longer exists for {key!r}; "
                    "restore the pre-edit corpus before migrating"
                )
            callout_id, digest = identity
            output.append("\t".join((row[0], callout_id, digest, row[2], row[3], row[4], row[5])))
        rendered = "\n".join(output) + "\n"
        if write:
            atomic_write(path, rendered)
        else:
            print(f"would migrate {path.relative_to(ROOT)}")
        changed += 1
    return changed


def migrate_snippets(results: pathlib.Path, write: bool) -> int:
    rows = command_rows([
        sys.executable, str(ROOT / "scripts/verify-snippets.py"),
        "--guides", str(ROOT / "guides"), "--stub-compiler", "pass",
    ])
    if not rows:
        raise SystemExit("snippet extractor produced no rows")
    current = {
        (row[0], row[1], row[2]): (row[-2], row[-1])
        for row in rows[1:] if len(row) == 15
    }
    with results.open(encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source, delimiter="\t")
        if reader.fieldnames is None:
            raise SystemExit(f"{results}: missing header")
        if {"snippet_id", "content_hash"}.issubset(reader.fieldnames):
            return 0
        old_fields = list(reader.fieldnames)
        migrated = []
        for number, row in enumerate(reader, 2):
            key = (row["file"], row["line"], row["anchor"])
            identity = current.get(key)
            if identity is None:
                raise SystemExit(
                    f"{results}:{number}: exact legacy fence no longer exists for {key!r}; "
                    "restore the pre-edit corpus before migrating"
                )
            row["snippet_id"], row["content_hash"] = identity
            migrated.append(row)
    fields = old_fields + ["snippet_id", "content_hash"]
    lines = ["\t".join(fields)]
    for row in migrated:
        lines.append("\t".join(row.get(field, "-") or "-" for field in fields))
    rendered = "\n".join(lines) + "\n"
    if write:
        atomic_write(results, rendered)
    else:
        print(f"would migrate {results.relative_to(ROOT)}")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("callouts", "snippets", "all"))
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--classified-dir", type=pathlib.Path,
                        default=ROOT / "notes/synthesis/callout-classifications")
    parser.add_argument("--results", type=pathlib.Path,
                        default=ROOT / "notes/snippet-verification/results.tsv")
    args = parser.parse_args()
    changed = 0
    if args.mode in ("callouts", "all"):
        changed += migrate_callouts(args.classified_dir, args.write)
    if args.mode in ("snippets", "all"):
        changed += migrate_snippets(args.results, args.write)
    print(f"{'migrated' if args.write else 'planned'} {changed} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
