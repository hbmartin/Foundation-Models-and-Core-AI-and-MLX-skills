#!/usr/bin/env python3
"""One-time migration of line-keyed callout and snippet TSVs to semantic IDs."""

from __future__ import annotations

import argparse
import importlib.util
import os
import pathlib
import subprocess
import sys
import tempfile


ROOT = pathlib.Path(__file__).resolve().parents[1]


def snippet_identities() -> dict[tuple[str, str, str], tuple[str, str]]:
    script = ROOT / "scripts/verify-snippets.py"
    spec = importlib.util.spec_from_file_location("verify_snippets_migration", script)
    if spec is None or spec.loader is None:
        raise SystemExit(f"cannot load snippet extractor: {script}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    fences, parse_errors = module.extract_fences(str(ROOT / "guides"))
    if parse_errors:
        raise SystemExit(f"snippet extraction failed: {parse_errors[0]}")
    module.validate_fence_identities(fences)
    identities = {}
    for fence in fences:
        try:
            identity = module.fence_identity(fence)
        except module.MarkerError as error:
            raise SystemExit(
                f"{fence.rel_path}:{fence.open_line}: invalid snippet marker: {error}"
            ) from error
        identities[(fence.rel_path, str(fence.open_line), fence.anchor)] = identity
    return identities


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
    if process.returncode != 0:
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
    rendered_files = []
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
        rendered_files.append((path, rendered))
    # Validate and render the complete set before replacing any file. A bad
    # later row can therefore never leave a mixed v1/v2 classification tree.
    for path, rendered in rendered_files:
        if write:
            atomic_write(path, rendered)
        else:
            try:
                display = path.relative_to(ROOT)
            except ValueError:
                display = path
            print(f"would migrate {display}")
    return len(rendered_files)


def migrate_snippets(results: pathlib.Path, write: bool) -> int:
    current = snippet_identities()
    with results.open(encoding="utf-8") as source:
        lines = source.read().splitlines()
        if not lines:
            raise SystemExit(f"{results}: missing header")
        old_fields = lines[0].split("\t")
        if {"snippet_id", "content_hash"}.issubset(old_fields):
            return 0
        migrated = []
        for number, line in enumerate(lines[1:], 2):
            fields = line.split("\t")
            if len(fields) != len(old_fields):
                raise SystemExit(
                    f"{results}:{number}: expected {len(old_fields)} TSV columns, "
                    f"got {len(fields)}"
                )
            row = dict(zip(old_fields, fields))
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
        try:
            display = results.relative_to(ROOT)
        except ValueError:
            display = results
        print(f"would migrate {display}")
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
    args.classified_dir = (
        args.classified_dir if args.classified_dir.is_absolute()
        else ROOT / args.classified_dir
    ).resolve()
    args.results = (
        args.results if args.results.is_absolute() else ROOT / args.results
    ).resolve()
    changed = 0
    if args.mode in ("callouts", "all"):
        changed += migrate_callouts(args.classified_dir, args.write)
    if args.mode in ("snippets", "all"):
        changed += migrate_snippets(args.results, args.write)
    print(f"{'migrated' if args.write else 'planned'} {changed} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
