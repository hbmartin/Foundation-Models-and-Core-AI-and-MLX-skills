#!/usr/bin/env python3
"""Extract and report the live state of defect references in guides/.

The reporter never edits the corpus. Network failures are represented as
UNREACHABLE references and do not make the command fail.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
import stat
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterable, Sequence
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
ALIASES = {
    "coreai-torch": "apple/coreai-torch",
    "coreai-models": "apple/coreai-models",
    "coreai-optimization": "apple/coreai-optimization",
    "python-apple-fm-sdk": "apple/python-apple-fm-sdk",
    "mlx": "ml-explore/mlx",
    "mlx-lm": "ml-explore/mlx-lm",
    "mlx-swift": "ml-explore/mlx-swift",
    "mlx-swift-lm": "ml-explore/mlx-swift-lm",
    "mlx-swift-examples": "ml-explore/mlx-swift-examples",
}
ALIAS_ALT = "|".join(sorted((re.escape(alias) for alias in ALIASES), key=len, reverse=True))

RE_URL = re.compile(
    r"https?://github\.com/([\w.-]+/[\w.-]+)/(?:issues|pull|discussions)/(\d+)"
)
RE_OWNER = re.compile(r"(?<![\w.-])([\w-]+/[\w.-]+?)#(\d{1,6})(?![\w-])")
RE_ADJACENT = re.compile(
    r"(?<![\w-])(" + ALIAS_ALT
    + r")(?:[`'\"*\s]{0,4}(?:issues?|PRs?|pulls?|bugs?)?[`'\"*\s]{0,4})#(\d{1,6})(?![\w-])"
)
RE_BARE = re.compile(r"(?<![\w/.#&-])#(\d{1,6})(?![\w#-])")
RE_MENTION = re.compile(r"(?<![\w-])(?:(?:apple|ml-explore)/)?(" + ALIAS_ALT + r")(?![\w-])")
RE_AS_OF = re.compile(r"as of\s*\*{0,2}(20\d{2}-\d{2}-\d{2})", re.IGNORECASE)
RE_DEFECTISH = re.compile(
    r"\b(issues?|PRs?|pull|bug|open(?:ed)?|closed|merged|landed|fix(?:ed)?|regression)\b",
    re.IGNORECASE,
)
CLAIM_PATTERNS = (
    (re.compile(r"\b(?:merged|landed)\b", re.IGNORECASE), "MERGED"),
    (re.compile(r"\bclosed\b", re.IGNORECASE), "CLOSED"),
    (re.compile(r"\bopen(?:ed)?\b", re.IGNORECASE), "OPEN"),
)
RE_NEGATED = re.compile(r"\b(?:not|never|no)[\s`'\"*]*$|n't[\s`'\"*]*$", re.IGNORECASE)
RE_CLAUSE_BOUNDARY = re.compile(
    r"(?:[.;](?:\s+|$)|,\s*(?=(?:while|whereas|but)\b)|"
    r"\b(?:while|whereas|but)\b|,\s+and\s+(?=(?:issues?|PRs?|pull requests?|bugs?)\b))",
    re.IGNORECASE,
)
GENERATED = {
    pathlib.Path("guides/SILENT-FAILURES.md"),
    pathlib.Path("guides/API-INDEX.md"),
}
VERDICT_ORDER = {
    "STATE-CHANGED": 0,
    "STALE-DATE-ONLY": 1,
    "AMBIGUOUS": 2,
    "UNREACHABLE": 3,
    "UNCHANGED": 4,
}
RESOLUTION_DISPOSITIONS = (
    "fixed",
    "fixed-with-residual",
    "merged-unreleased",
    "closed-unfixed",
    "closed-unmerged",
    "superseded",
    "consolidated",
    "unknown",
)


def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--repo", help="limit output to one owner/repository")
    parser.add_argument("--changed-only", action="store_true", help="show only STATE-CHANGED rows")
    parser.add_argument("--extract-only", action="store_true", help="extract references without GitHub queries")
    parser.add_argument("--format", choices=("markdown", "json", "tsv"), default="markdown")
    parser.add_argument("--output", type=pathlib.Path, help="atomically write the primary report to this path")
    parser.add_argument("--tsv", type=pathlib.Path, help="also write the legacy sighting TSV")
    parser.add_argument("--source-root", type=pathlib.Path, default=ROOT, help=argparse.SUPPRESS)
    parser.add_argument("--sleep-seconds", type=float, default=0.15, help=argparse.SUPPRESS)
    arguments = parser.parse_args(argv)
    if arguments.sleep_seconds < 0:
        parser.error("--sleep-seconds must not be negative")
    return arguments


def generated_at() -> str:
    raw_epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if raw_epoch is not None:
        try:
            value = dt.datetime.fromtimestamp(int(raw_epoch), tz=dt.timezone.utc)
        except (ValueError, OverflowError, OSError) as error:
            raise ValueError("SOURCE_DATE_EPOCH must be a valid Unix timestamp") from error
    else:
        value = dt.datetime.now(dt.timezone.utc)
    return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def atomic_text(path: pathlib.Path, contents: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        publish_mode = stat.S_IMODE(path.stat().st_mode)
    except FileNotFoundError:
        current_umask = os.umask(0)
        os.umask(current_umask)
        publish_mode = 0o666 & ~current_umask
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(descriptor, publish_mode)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(contents)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def paragraphs(path: pathlib.Path) -> Iterable[tuple[int, str]]:
    """Yield blank-line paragraphs, while treating each Markdown table row separately."""
    block: list[str] = []
    start: int | None = None

    def flush() -> tuple[int, str] | None:
        nonlocal block, start
        if not block or start is None:
            return None
        value = (start, "\n".join(block))
        block = []
        start = None
        return value

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for line_number, line in enumerate(lines, 1):
        if not line.strip() or line.lstrip().startswith("|"):
            value = flush()
            if value:
                yield value
            if line.lstrip().startswith("|"):
                yield line_number, line
        else:
            if start is None:
                start = line_number
            block.append(line)
    value = flush()
    if value:
        yield value


def nearest(matches: Sequence[tuple[int, str]], offset: int) -> str | None:
    return min(matches, key=lambda match: abs(match[0] - offset))[1] if matches else None


def nearest_mention(
    mentions: Sequence[tuple[int, str]], start: int, end: int, text: str
) -> tuple[str | None, float, list[dict[str, str]]]:
    after = [mention for mention in mentions if mention[0] >= end]
    if after:
        first = min(after)
        gap = text[end : first[0]]
        if len(gap) <= 12 and "(" in gap and "#" not in gap:
            return first[1], 0.8, []
    before = sorted(mention for mention in mentions if mention[0] <= start)
    if not before:
        mapped = nearest(mentions, start)
        if mapped:
            return mapped, 0.65, []
        return None, 0.0, [
            {
                "code": "ambiguous-repository",
                "message": "Bare reference has no unambiguous repository mention in its paragraph.",
            }
        ]
    closest = before[-1]
    for previous in before[:-1]:
        if (
            previous[1] != closest[1]
            and 0 < closest[0] - previous[0] < 40
            and "#" not in text[previous[0] : closest[0]]
        ):
            return None, 0.0, [
                {
                    "code": "ambiguous-repository",
                    "message": "Bare reference follows a list containing multiple repositories.",
                }
            ]
    return closest[1], 0.75, []


def clause_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    start = 0
    for match in RE_CLAUSE_BOUNDARY.finditer(text):
        if match.start() > start:
            spans.append((start, match.start()))
        start = match.end()
    if start < len(text):
        spans.append((start, len(text)))
    return spans or [(0, len(text))]


def clause_for_offset(text: str, offset: int) -> tuple[int, int]:
    for start, end in clause_spans(text):
        if start <= offset <= end:
            return start, end
    return 0, len(text)


def claim_in_clause(
    text: str, reference_start: int, reference_end: int
) -> tuple[str | None, float, list[dict[str, str]]]:
    clause_start, clause_end = clause_for_offset(text, reference_start)

    def scan(segment: str, distance_from_match: Any) -> list[tuple[int, str]]:
        found: list[tuple[int, str]] = []
        for pattern, state in CLAIM_PATTERNS:
            for match in pattern.finditer(segment):
                prefix = segment[max(0, match.start() - 12) : match.start()]
                if not RE_NEGATED.search(prefix):
                    found.append((distance_from_match(match), state))
        return found

    # Guide prose overwhelmingly states a reference's state after it. Preserve
    # that precedence, but keep both directions bounded inside the same clause
    # so a status attached to a neighbouring reference cannot leak arbitrarily.
    after_segment = text[reference_end : min(clause_end, reference_end + 80)]
    candidates = scan(after_segment, lambda match: match.start())
    direction = "after"
    if not candidates:
        before_segment = text[max(clause_start, reference_start - 40) : reference_start]
        candidates = scan(before_segment, lambda match: len(before_segment) - match.end())
        direction = "before"
    if not candidates:
        return None, 1.0, []
    states = {state for _, state in candidates}
    chosen = min(candidates, key=lambda item: item[0])[1]
    if len(states) == 1:
        return chosen, 0.9, []
    return chosen, 0.6, [
        {
            "code": "multiple-state-words",
            "message": (
                f"Bounded {direction}-reference window contains multiple state words; "
                f"selected nearest state {chosen}."
            ),
        }
    ]


def extract(source_root: pathlib.Path) -> list[dict[str, Any]]:
    sightings: list[dict[str, Any]] = []
    guides = source_root / "guides"
    for path in sorted(guides.rglob("*.md")):
        relative_path = path.relative_to(source_root)
        if relative_path in GENERATED:
            continue
        for paragraph_start, text in paragraphs(path):
            mentions = [(match.start(), ALIASES[match.group(1)]) for match in RE_MENTION.finditer(text)]
            mentions.extend((match.start(), match.group(1)) for match in RE_URL.finditer(text))
            dates = [(match.start(), match.group(1)) for match in RE_AS_OF.finditer(text)]
            occupied: list[tuple[int, int]] = []
            references: list[tuple[int, int, str | None, int, str, float, list[dict[str, str]]]] = []

            def take(
                match: re.Match[str],
                repository: str | None,
                number: int,
                form: str,
                confidence: float,
                diagnostics: list[dict[str, str]] | None = None,
            ) -> None:
                if any(match.start() < end and match.end() > start for start, end in occupied):
                    return
                occupied.append((match.start(), match.end()))
                references.append(
                    (
                        match.start(),
                        match.end(),
                        repository,
                        number,
                        form,
                        confidence,
                        diagnostics or [],
                    )
                )

            for match in RE_URL.finditer(text):
                take(match, match.group(1), int(match.group(2)), "url", 1.0)
            for match in RE_OWNER.finditer(text):
                take(match, match.group(1), int(match.group(2)), "owner-repo", 1.0)
            for match in RE_ADJACENT.finditer(text):
                take(match, ALIASES[match.group(1)], int(match.group(2)), "repo-adjacent", 0.95)
            if RE_DEFECTISH.search(text):
                for match in RE_BARE.finditer(text):
                    repository, confidence, diagnostics = nearest_mention(
                        mentions, match.start(), match.end(), text
                    )
                    take(
                        match,
                        repository,
                        int(match.group(1)),
                        "bare",
                        confidence,
                        diagnostics,
                    )

            # Keep the legacy extraction order: URLs, owner/repo refs, adjacent
            # repo refs, then bare refs, each in regex encounter order.
            for offset, end, repository, number, form, map_confidence, diagnostics in references:
                claimed_state, claim_confidence, claim_diagnostics = claim_in_clause(
                    text, offset, end
                )
                clause_start, clause_end = clause_for_offset(text, offset)
                clause_dates = [date for date in dates if clause_start <= date[0] <= clause_end]
                claim_date = nearest(clause_dates, offset)
                context_width = 240
                reference_width = end - offset
                left_budget = max(0, (context_width - reference_width) // 2)
                context_start = max(0, offset - left_budget)
                context_end = min(len(text), context_start + context_width)
                context_start = max(0, context_end - context_width)
                sightings.append(
                    {
                        "id": f"s{len(sightings) + 1:04d}",
                        "file": relative_path.as_posix(),
                        "line": paragraph_start + text.count("\n", 0, offset),
                        "repository": repository,
                        "number": number,
                        "form": form,
                        "claimedState": claimed_state,
                        "claimDate": claim_date,
                        "context": " ".join(text[context_start:context_end].split()),
                        "confidence": round(min(map_confidence, claim_confidence), 2),
                        "diagnostics": diagnostics + claim_diagnostics,
                    }
                )
    return sightings


def gh_json(*arguments: str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        process = subprocess.run(
            ["gh", *arguments], capture_output=True, text=True, timeout=30, check=False
        )
    except (subprocess.TimeoutExpired, OSError) as error:
        return None, str(error)
    if process.returncode != 0:
        message = (process.stderr or process.stdout).strip()
        return None, message.splitlines()[0][:120] if message else "gh failed"
    try:
        value = json.loads(process.stdout)
    except json.JSONDecodeError:
        return None, "unparseable gh output"
    return value, None


def lookup(repository: str, number: int) -> dict[str, Any]:
    data, error = gh_json("api", f"repos/{repository}/issues/{number}")
    if data:
        pull_request = data.get("pull_request") or {}
        state = (
            "MERGED"
            if pull_request.get("merged_at")
            else "CLOSED"
            if data.get("state") == "closed"
            else "OPEN"
        )
        reason = data.get("state_reason")
        return {
            "kind": "PR" if pull_request else "issue",
            "state": state,
            "url": data.get("html_url") or f"https://github.com/{repository}/issues/{number}",
            "closedAt": data.get("closed_at") or None,
            "mergedAt": pull_request.get("merged_at") or None,
            "stateReason": reason or None,
            "reason": reason if reason not in (None, "", "completed") else None,
            "title": data.get("title") or "",
        }
    data, _ = gh_json(
        "issue",
        "view",
        str(number),
        "--repo",
        repository,
        "--json",
        "state,stateReason,closedAt,title",
    )
    if data:
        return {
            "kind": "issue",
            "state": data["state"],
            "url": f"https://github.com/{repository}/issues/{number}",
            "closedAt": data.get("closedAt") or None,
            "mergedAt": None,
            "stateReason": data.get("stateReason") or None,
            "reason": data.get("stateReason") or None,
            "title": data.get("title") or "",
        }
    data, _ = gh_json(
        "pr",
        "view",
        str(number),
        "--repo",
        repository,
        "--json",
        "state,closedAt,mergedAt,title",
    )
    if data:
        return {
            "kind": "PR",
            "state": "MERGED" if data.get("mergedAt") else data["state"],
            "url": f"https://github.com/{repository}/pull/{number}",
            "closedAt": data.get("closedAt") or None,
            "mergedAt": data.get("mergedAt") or None,
            "stateReason": None,
            "reason": None,
            "title": data.get("title") or "",
        }
    return {"error": error or "unreachable"}


def transition_kind(live: dict[str, Any] | None, claims: Sequence[str]) -> str:
    if live is None or "error" in live:
        return "UNKNOWN"
    if not claims:
        return f"UNCLAIMED_TO_{live['state']}"
    if len(claims) != 1:
        return "CONFLICTING_CLAIMS"
    return f"{claims[0]}_TO_{live['state']}" if claims[0] != live["state"] else "UNCHANGED"


def verdict(
    live: dict[str, Any] | None,
    claims: Sequence[str],
    claim_date: str | None,
    confidence: float = 1.0,
    diagnostics: Sequence[dict[str, str]] = (),
) -> str:
    if live is None:
        return "AMBIGUOUS"
    if "error" in live:
        return "UNREACHABLE"
    ambiguous_codes = {
        "ambiguous-repository",
        "multiple-state-words",
        "conflicting-guide-claims",
    }
    if confidence < 0.75 or any(
        diagnostic.get("code") in ambiguous_codes for diagnostic in diagnostics
    ):
        return "AMBIGUOUS"
    compatible = {
        "OPEN": {"OPEN"},
        "MERGED": {"MERGED", "CLOSED"},
        "CLOSED": {"CLOSED"} if live["kind"] == "PR" else {"CLOSED", "MERGED"},
    }[live["state"]]
    if claims:
        return "UNCHANGED" if all(claim in compatible for claim in claims) else "STATE-CHANGED"
    if (
        live["state"] != "OPEN"
        and claim_date
        and live.get("closedAt")
        and live["closedAt"] > claim_date
    ):
        return "STATE-CHANGED"
    return "STALE-DATE-ONLY" if claim_date else "UNCHANGED"


def group_references(
    sightings: Sequence[dict[str, Any]], perform_lookup: bool, sleep_seconds: float
) -> list[dict[str, Any]]:
    distinct: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for sighting in sightings:
        repository = sighting["repository"] or f"?@{sighting['file']}"
        distinct.setdefault((repository, sighting["number"]), []).append(sighting)

    references: list[dict[str, Any]] = []
    for (_, number), group in sorted(distinct.items()):
        repository = group[0]["repository"]
        live: dict[str, Any] | None = None
        diagnostics = [diagnostic for sighting in group for diagnostic in sighting["diagnostics"]]
        if perform_lookup and repository:
            live = lookup(repository, number)
            if "error" in live:
                diagnostics.append({"code": "github-unreachable", "message": live["error"]})
            time.sleep(sleep_seconds)
        claims = sorted(
            {sighting["claimedState"] for sighting in group if sighting["claimedState"]}
        )
        if len(claims) > 1:
            diagnostics.append(
                {
                    "code": "conflicting-guide-claims",
                    "message": f"Sightings claim multiple states: {', '.join(claims)}.",
                }
            )
        claim_date = max(
            (sighting["claimDate"] for sighting in group if sighting["claimDate"]),
            default=None,
        )
        reference: dict[str, Any] = {
            "ref": f"{repository or '?'}#{number}",
            "repository": repository,
            "number": number,
            "claims": claims,
            "latestClaimDate": claim_date,
            "sightingCount": len(group),
            "sightingIds": [sighting["id"] for sighting in group],
            "confidence": min(sighting["confidence"] for sighting in group),
            "diagnostics": diagnostics,
            "liveState": live.get("state") if live and "error" not in live else None,
            "liveUrl": live.get("url") if live and "error" not in live else None,
            "closureReason": live.get("stateReason") if live and "error" not in live else None,
            "closedAt": live.get("closedAt") if live and "error" not in live else None,
            "mergeTimestamp": live.get("mergedAt") if live and "error" not in live else None,
            "transitionKind": transition_kind(live, claims),
            "resolutionDisposition": "unknown",
            "automaticFixEligible": False,
        }
        if perform_lookup:
            reference["live"] = live
            reference["verdict"] = verdict(
                live,
                claims,
                claim_date,
                reference["confidence"],
                diagnostics,
            )
        references.append(reference)
    if perform_lookup:
        references.sort(
            key=lambda item: (
                VERDICT_ORDER[item["verdict"]],
                item["repository"] or "~",
                item["number"],
            )
        )
    return references


def structured_payload(
    sightings: Sequence[dict[str, Any]],
    references: Sequence[dict[str, Any]],
    timestamp: str,
    repository_filter: str | None,
    extraction_only: bool,
    summary_references: Sequence[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    summarized = references if summary_references is None else summary_references
    verdict_counts = {
        verdict_name: sum(reference.get("verdict") == verdict_name for reference in summarized)
        for verdict_name in VERDICT_ORDER
    }
    return {
        "schemaVersion": 2,
        "resolutionDispositions": list(RESOLUTION_DISPOSITIONS),
        "generatedAt": timestamp,
        "mode": "extraction" if extraction_only else "live-report",
        "repositoryFilter": repository_filter,
        "summary": {
            "references": len(summarized),
            "sightings": len(sightings),
            "ambiguousSightings": sum(sighting["repository"] is None for sighting in sightings),
            "verdicts": verdict_counts if not extraction_only else None,
        },
        "references": list(references),
        "sightings": list(sightings),
    }


def sighting_tsv(sightings: Sequence[dict[str, Any]]) -> str:
    fields = (
        "file",
        "line",
        "repository",
        "number",
        "form",
        "claimedState",
        "claimDate",
        "context",
    )
    legacy_names = {
        "repository": "repo",
        "claimedState": "claimed_state",
        "claimDate": "claim_date",
    }
    lines = ["\t".join(legacy_names.get(field, field) for field in fields)]
    for sighting in sightings:
        values = []
        for field in fields:
            value = sighting[field]
            rendered = "?" if value is None else str(value)
            values.append(rendered.replace("\t", " ").replace("\n", " "))
        lines.append("\t".join(values))
    return "\n".join(lines) + "\n"


def reference_tsv(references: Sequence[dict[str, Any]]) -> str:
    lines = ["ref\tclaims\tlive_state\tverdict\tsightings\tconfidence\tdiagnostics"]
    for reference in references:
        live = reference.get("live") or {}
        lines.append(
            "\t".join(
                (
                    reference["ref"],
                    "/".join(reference["claims"]) or "—",
                    live.get("state") or ("UNREACHABLE" if live.get("error") else "?"),
                    reference.get("verdict") or "—",
                    str(reference["sightingCount"]),
                    str(reference["confidence"]),
                    ",".join(diagnostic["code"] for diagnostic in reference["diagnostics"])
                    or "—",
                )
            )
        )
    return "\n".join(lines) + "\n"


def markdown_report(
    references: Sequence[dict[str, Any]],
    sightings: Sequence[dict[str, Any]],
    timestamp: str,
    summary_references: Sequence[dict[str, Any]] | None = None,
) -> str:
    lines = [
        f"# Defect-status report — {timestamp[:10]}",
        "",
        "| ref | kind | title | guide claim | live | sightings | confidence | verdict |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for reference in references:
        live = reference.get("live")
        if live is None:
            kind, live_column, title = "?", "?", ""
        elif "error" in live:
            kind, live_column, title = "?", f"error: {live['error']}", ""
        else:
            kind = live["kind"]
            live_column = live["state"]
            if live.get("reason"):
                live_column += f" ({live['reason']})"
            if live.get("closedAt"):
                live_column += f" {live['closedAt']}"
            title = live["title"][:46].replace("|", "\\|")
        claim = "/".join(reference["claims"]) or "—"
        if reference["latestClaimDate"]:
            claim += f" as of {reference['latestClaimDate']}"
        first = next(
            sighting for sighting in sightings if sighting["id"] == reference["sightingIds"][0]
        )
        lines.append(
            f"| {reference['ref']} | {kind} | {title} | {claim} | {live_column} | "
            f"{reference['sightingCount']}× {first['file']}:{first['line']} | "
            f"{reference['confidence']:.2f} | **{reference['verdict']}** |"
        )
    summarized = references if summary_references is None else summary_references
    counts = {
        name: sum(reference["verdict"] == name for reference in summarized)
        for name in VERDICT_ORDER
    }
    count_text = ", ".join(f"{counts[name]} {name}" for name in VERDICT_ORDER)
    lines.extend(
        (
            "",
            f"**Summary.** {len(summarized)} distinct refs across {len(sightings)} sightings in guides/: "
            f"{count_text}. STATE-CHANGED rows require a human edit; STALE-DATE-ONLY rows only "
            "need review of the date; AMBIGUOUS rows need citation or parser review; UNREACHABLE rows "
            "should be retried. This report never edits guides/.",
        )
    )
    return "\n".join(lines) + "\n"


def render(arguments: argparse.Namespace) -> str:
    timestamp = generated_at()
    sightings = extract(arguments.source_root.resolve())
    if arguments.repo:
        sightings = [
            sighting for sighting in sightings if sighting["repository"] == arguments.repo
        ]
    extraction_tsv = sighting_tsv(sightings)
    if arguments.tsv:
        atomic_text(arguments.tsv, extraction_tsv)
        print(f"Extraction TSV written to {arguments.tsv}", file=sys.stderr)

    all_references = group_references(
        sightings,
        perform_lookup=not arguments.extract_only,
        sleep_seconds=arguments.sleep_seconds,
    )
    references = all_references
    if arguments.changed_only and not arguments.extract_only:
        references = [
            reference for reference in references if reference["verdict"] == "STATE-CHANGED"
        ]

    if arguments.extract_only and arguments.format in {"markdown", "tsv"}:
        return extraction_tsv
    if arguments.format == "json":
        payload = structured_payload(
            sightings,
            references,
            timestamp,
            arguments.repo,
            arguments.extract_only,
            all_references,
        )
        return json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if arguments.format == "tsv":
        return reference_tsv(references)
    return markdown_report(references, sightings, timestamp, all_references)


def main(argv: Sequence[str] | None = None) -> int:
    try:
        arguments = parse_arguments(argv)
        contents = render(arguments)
    except (OSError, ValueError) as error:
        print(f"defect-status reporter: {error}", file=sys.stderr)
        return 2
    if arguments.output:
        atomic_text(arguments.output, contents)
        print(f"Report written to {arguments.output}")
    else:
        try:
            sys.stdout.write(contents)
        except BrokenPipeError:
            return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
