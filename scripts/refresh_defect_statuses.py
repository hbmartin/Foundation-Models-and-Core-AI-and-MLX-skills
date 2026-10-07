#!/usr/bin/env python3
"""Report the live state of explicit current defect records.

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


try:
    from scripts.mdslug import collect_headings
    from scripts.mdlinks import iter_lines
except ModuleNotFoundError:
    from mdslug import collect_headings
    from mdlinks import iter_lines

ROOT = pathlib.Path(__file__).resolve().parents[1]
RE_URL = re.compile(r"https?://github\.com/([\w.-]+/[\w.-]+)/(?P<route>issues|pull|discussions)/(\d+)")
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


def load_registry(source_root: pathlib.Path) -> list[dict[str, Any]]:
    path = source_root / "notes/defects.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read defect registry: {error}") from error
    if not isinstance(payload, dict) or payload.get("schemaVersion") != 1 or not isinstance(payload.get("defects"), list):
        raise ValueError("defect registry must be schema version 1")
    ids, identities = set(), set()
    for record in payload["defects"]:
        if not isinstance(record, dict):
            raise ValueError("defect record must be an object")
        required = {"id", "url", "kind", "affectedVersions", "guideRefs", "claimedState", "asOf", "resolution"}
        if not required.issubset(record):
            raise ValueError("defect record lacks required fields")
        if any(not isinstance(record[key], str) or not record[key].strip() for key in ("id", "url", "kind", "claimedState", "asOf", "affectedVersions")):
            raise ValueError("defect scalar fields must be nonempty strings")
        match = re.fullmatch(r"https://github\.com/([\w.-]+/[\w.-]+)/(issues|pull|discussions)/([1-9][0-9]*)", record["url"] if isinstance(record["url"], str) else "")
        routes = {"issue": "issues", "pull": "pull", "discussion": "discussions"}
        if not match or record["kind"] not in routes or routes[record["kind"]] != match[2]:
            raise ValueError("defect URL and kind must identify the same GitHub reference")
        identity = (match[1], record["kind"], int(match[3]))
        if not isinstance(record["id"], str) or not re.fullmatch(r"[A-Za-z0-9_.:-]+", record["id"]) or record["id"] in ids or identity in identities:
            raise ValueError("duplicate or invalid defect identity")
        ids.add(record["id"]); identities.add(identity)
        allowed = {"OPEN", "CLOSED", "MERGED"} if record["kind"] == "pull" else {"OPEN", "CLOSED"}
        if record["claimedState"] not in allowed:
            raise ValueError("invalid state for defect kind")
        for value in (record["asOf"], record["resolution"].get("evidenceDate") if isinstance(record["resolution"], dict) else None):
            if not isinstance(value, str) or not re.fullmatch(r"20\d{2}-\d{2}-\d{2}", value):
                raise ValueError("defect dates must be ISO dates")
            dt.date.fromisoformat(value)
        resolution = record["resolution"]
        if resolution.get("disposition") not in RESOLUTION_DISPOSITIONS or not isinstance(resolution.get("evidenceUrls"), list) or not resolution["evidenceUrls"] or not all(isinstance(url, str) and url.startswith("https://") for url in resolution["evidenceUrls"]):
            raise ValueError("resolution requires a known disposition and evidence URLs")
        confidence = resolution.get("confidence")
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1 or not isinstance(resolution.get("rationale"), str) or not resolution["rationale"].strip():
            raise ValueError("resolution requires confidence and rationale")
        for key, states in (("releaseAvailability", {"unknown", "released", "not-in-verified-release"}),
                            ("remediation", {"unverified", "demonstrated", "not-remediated"})):
            evidence = resolution.get(key)
            if not isinstance(evidence, dict) or not isinstance(evidence.get("status"), str) or evidence["status"] not in states:
                raise ValueError(f"resolution requires explicit {key} state")
            if evidence.get("version") is not None and (not isinstance(evidence["version"], str) or not evidence["version"].strip()):
                raise ValueError(f"invalid {key} version")
            if evidence["status"] != "unknown" and evidence["status"] != "unverified":
                urls = evidence.get("evidenceUrls")
                if not isinstance(urls, list) or not urls or not all(isinstance(url, str) and url.startswith("https://") for url in urls):
                    raise ValueError(f"{key} claims require evidence URLs")
        if resolution["disposition"] in {"fixed", "fixed-with-residual"} and resolution["remediation"]["status"] != "demonstrated":
            raise ValueError("a fixed disposition requires demonstrated remediation")
        if not isinstance(record["affectedVersions"], str) or not record["affectedVersions"].strip() or not isinstance(record["guideRefs"], list) or not record["guideRefs"]:
            raise ValueError("defect requires affected versions and guide references")
        seen_locations = set()
        for location in record["guideRefs"]:
            if not isinstance(location, dict) or set(location) != {"file", "anchor"} or not all(isinstance(location[k], str) and location[k] for k in location):
                raise ValueError("guide reference requires file and anchor")
            relative = pathlib.PurePosixPath(location["file"])
            target = source_root / relative
            if relative.is_absolute() or ".." in relative.parts or not relative.parts or relative.parts[0] != "guides" or relative.suffix != ".md" or target.is_symlink() or not target.is_file() or source_root.resolve() not in target.resolve().parents:
                raise ValueError(f"missing or unsafe guide target: {location['file']}")
            # Shared heading extraction preserves duplicate-anchor suffixes and ignores fences.
            anchors = {item.anchor for item in collect_headings(target.read_text(encoding="utf-8"))}
            if location["anchor"] not in anchors:
                raise ValueError(f"missing guide anchor: {location['file']}#{location['anchor']}")
            key = (location["file"], location["anchor"])
            if key in seen_locations:
                raise ValueError("duplicate guide reference")
            seen_locations.add(key)
    expected = {
        (location["file"], location["anchor"], record["id"])
        for record in payload["defects"] for location in record["guideRefs"]
    }
    found = set()
    for guide in sorted((source_root / "guides").rglob("*.md")):
        text = guide.read_text(encoding="utf-8")
        headings = iter(collect_headings(text))
        heading = next(headings, None)
        anchor = None
        relative = guide.relative_to(source_root).as_posix()
        for number, (line, _newline, fenced) in enumerate(iter_lines(text), 1):
            if fenced:
                continue
            while heading and heading.line <= number:
                anchor = heading.anchor
                heading = next(headings, None)
            for identifier in re.findall(r"<!--\s*defect-ref:([^\s]+)\s*-->", line):
                key = (relative, anchor, identifier)
                if key not in expected:
                    raise ValueError(f"{relative}:{number}: unknown or misplaced defect ID {identifier}")
                if key in found:
                    raise ValueError(f"{relative}:{number}: duplicate defect marker {identifier}")
                found.add(key)
    missing = expected - found
    if missing:
        raise ValueError("missing defect markers: " + ", ".join(
            f"{file}#{anchor}: {identifier}" for file, anchor, identifier in sorted(missing)
        ))
    return payload["defects"]


def extract(source_root: pathlib.Path) -> list[dict[str, Any]]:
    """Describe explicit current claims, without interpreting prose or bare issue numbers."""
    sightings = []
    for record in load_registry(source_root):
        match = RE_URL.fullmatch(record["url"])
        for location in record["guideRefs"]:
            path = source_root / location["file"]
            headings = collect_headings(path.read_text(encoding="utf-8"))
            heading = next(item for item in headings if item.anchor == location["anchor"])
            sightings.append({
                "id": f"s{len(sightings) + 1:04d}", "file": location["file"], "line": heading.line,
                "repository": match[1], "number": int(match[3]), "form": "registry",
                "referenceKind": "discussion" if record["kind"] == "discussion" else "issue-or-pr",
                "githubKind": record["kind"], "registryId": record["id"],
                "claimedState": record["claimedState"], "claimDate": record["asOf"],
                "claimText": record["affectedVersions"], "context": record["title"] if "title" in record else record["affectedVersions"],
                "confidence": 1.0, "diagnostics": [], "resolution": record["resolution"],
            })
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


def lookup(repository: str, number: int, reference_kind: str = "issue-or-pr") -> dict[str, Any]:
    if reference_kind == "pull":
        data, error = gh_json("api", f"repos/{repository}/pulls/{number}")
        if not data:
            return {"error": error or "pull request not returned"}
        return {"kind": "PR", "state": "MERGED" if data.get("merged_at") else data["state"].upper(),
                "url": data["html_url"], "title": data["title"], "closedAt": data.get("closed_at"),
                "mergedAt": data.get("merged_at"), "stateReason": None, "reason": None}

    if reference_kind == "discussion":
        owner, name = repository.split("/", 1)
        query = ("query($owner:String!,$name:String!,$number:Int!){repository(owner:$owner,name:$name)"
                 "{discussion(number:$number){title url closedAt isAnswered}}}")
        data, error = gh_json("api", "graphql", "-f", "query=" + query,
                              "-f", "owner=" + owner, "-f", "name=" + name,
                              "-F", "number=" + str(number))
        discussion = ((data or {}).get("data", {}).get("repository") or {}).get("discussion")
        if not discussion:
            return {"error": error or "discussion not returned"}
        return {"kind": "discussion", "state": "CLOSED" if discussion.get("closedAt") else "OPEN",
                "url": discussion["url"], "title": discussion["title"],
                "closedAt": discussion.get("closedAt"), "mergedAt": None,
                "stateReason": None, "reason": None, "answered": discussion["isAnswered"]}
    data, error = gh_json("api", f"repos/{repository}/issues/{number}")
    if data:
        if reference_kind == "issue" and data.get("pull_request"):
            return {"error": "registry declares an issue but GitHub returned a pull request"}
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
    if reference_kind == "issue":
        return {"error": error or "issue not returned"}
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
        and live["closedAt"][:10] > claim_date
    ):
        return "STATE-CHANGED"
    return "STALE-DATE-ONLY" if claim_date else "UNCHANGED"


def group_references(
    sightings: Sequence[dict[str, Any]], perform_lookup: bool, sleep_seconds: float
) -> list[dict[str, Any]]:
    distinct: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    for sighting in sightings:
        repository = sighting["repository"] or f"?@{sighting['file']}"
        distinct.setdefault((repository, sighting.get("githubKind", sighting.get("referenceKind", "issue-or-pr")), sighting["number"]), []).append(sighting)

    references: list[dict[str, Any]] = []
    for (_, reference_kind, number), group in sorted(distinct.items()):
        repository = group[0]["repository"]
        live: dict[str, Any] | None = None
        diagnostics = [diagnostic for sighting in group for diagnostic in sighting["diagnostics"]]
        if perform_lookup and repository:
            live = lookup(repository, number, reference_kind)
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
            "referenceKind": "discussion" if reference_kind == "discussion" else "issue-or-pr",
            "githubKind": reference_kind,
            "registryId": group[0].get("registryId"),
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
            "resolutionDisposition": group[0].get("resolution", {}).get("disposition", "unknown"),
            "releaseAvailability": group[0].get("resolution", {}).get("releaseAvailability"),
            "remediation": group[0].get("resolution", {}).get("remediation"),
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
        "unreachableReferences": [reference for reference in summarized if reference.get("verdict") == "UNREACHABLE"],
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
    failures = [r for r in summarized if r.get("verdict") == "UNREACHABLE"]
    if failures:
        lines.extend(["", "## Failed GitHub lookups", ""] + [f"- {r['ref']}: {(r.get('live') or {}).get('error', 'unreachable')}" for r in failures])
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
