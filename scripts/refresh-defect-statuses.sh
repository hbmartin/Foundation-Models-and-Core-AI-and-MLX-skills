#!/usr/bin/env bash
# Report the LIVE GitHub state of every defect the guides hedge on ("#N", "repo#N",
# "owner/repo#N", issue/PR URLs, with their "as of 20YY-MM-DD" dates). This is a
# REPORTING tool: it never edits guides/ — a human (or an agent) reads the report
# and decides which hedges to rewrite. Safe to run repeatedly; read-only via `gh`.
#
#   ./scripts/refresh-defect-statuses.sh                      # full markdown report to stdout
#   ./scripts/refresh-defect-statuses.sh --changed-only       # only STATE-CHANGED rows in the table
#   ./scripts/refresh-defect-statuses.sh --repo ml-explore/mlx
#   ./scripts/refresh-defect-statuses.sh --extract-only       # extraction TSV to stdout, no network
#   ./scripts/refresh-defect-statuses.sh --tsv refs.tsv       # also dump the extraction TSV to a file
#
# Verdicts, sorted STATE-CHANGED first:
#   STATE-CHANGED    a guide sighting claims a state (OPEN/CLOSED/MERGED) the ref no
#                    longer has — or no state was claimed but the ref was closed AFTER
#                    the guide's "as of" date. These need a human pass over the guide.
#   UNCHANGED        every claimed state still matches live (the "as of" date is still
#                    literally true, so bumping it is optional).
#   STALE-DATE-ONLY  a hedge date but no parseable state claim, and nothing has closed
#                    since that date — only the date itself decays.
#   AMBIGUOUS        a bare #N with no repo name in the same paragraph — fix the guide
#                    to name the repo, or map it by hand.
#   UNREACHABLE      gh could not answer (offline, deleted, private, bad mapping).
#                    Offline runs degrade to all-UNREACHABLE and still exit 0.
#
# Bare #N → repo mapping: nearest repo-name mention in the same paragraph (markdown
# blank-line block). Anchor-link noise like "(#13-section-title)" is excluded by
# requiring the digits to not be followed by a word char or hyphen, and a bare #N is
# only kept when its paragraph reads defect-ish (issue/PR/bug/open/merged/... nearby).
#
# Dependency-light on purpose: bash + python3 + gh. Queries are deduped (each
# distinct owner/repo#N hit once — the corpus cites ~190 mappable refs across
# ~950 sightings, some cited 20+ times) and
# spaced with a small sleep to stay polite. One `gh api repos/{R}/issues/{N}` call
# answers for BOTH issues and PRs (the REST issues endpoint carries
# pull_request.merged_at, which `gh issue view` cannot report); `gh issue view` /
# `gh pr view` remain as fallbacks. Always exits 0 unless the arguments are wrong.

set -uo pipefail
cd "$(dirname "$0")/.."

exec python3 - "$@" <<'PY'
import json, re, subprocess, sys, time
from pathlib import Path

# ---- the nine repos the guides cite, short name -> owner/repo -----------------
ALIASES = {
    "coreai-torch":        "apple/coreai-torch",
    "coreai-models":       "apple/coreai-models",
    "coreai-optimization": "apple/coreai-optimization",
    "python-apple-fm-sdk": "apple/python-apple-fm-sdk",
    "mlx":                 "ml-explore/mlx",
    "mlx-lm":              "ml-explore/mlx-lm",
    "mlx-swift":           "ml-explore/mlx-swift",
    "mlx-swift-lm":        "ml-explore/mlx-swift-lm",
    "mlx-swift-examples":  "ml-explore/mlx-swift-examples",
}
# Longest first so mlx-swift-lm never half-matches as mlx / mlx-swift.
ALIAS_ALT = "|".join(sorted((re.escape(a) for a in ALIASES), key=len, reverse=True))

RE_URL   = re.compile(r"https?://github\.com/([\w.-]+/[\w.-]+)/(?:issues|pull|discussions)/(\d+)")
RE_OWNER = re.compile(r"(?<![\w.-])([\w-]+/[\w.-]+?)#(\d{1,6})(?![\w-])")
# repo name, optional "issue"/"PR"-ish filler (allowing ` * ** bold/backtick), then #N
RE_ADJ   = re.compile(
    r"(?<![\w-])(" + ALIAS_ALT + r")(?:[`'\"*\s]{0,4}(?:issues?|PRs?|pulls?|bugs?)?[`'\"*\s]{0,4})#(\d{1,6})(?![\w-])")
RE_BARE  = re.compile(r"(?<![\w/.#&-])#(\d{1,6})(?![\w#-])")  # &: skip HTML entities like &#124;
RE_MENTION = re.compile(r"(?<![\w-])(?:(?:apple|ml-explore)/)?(" + ALIAS_ALT + r")(?![\w-])")
RE_ASOF  = re.compile(r"as of\s*\*{0,2}(20\d{2}-\d{2}-\d{2})", re.I)
RE_DEFECTISH = re.compile(r"\b(issues?|PRs?|pull|bug|open(?:ed)?|closed|merged|landed|fix(?:ed)?|regression)\b", re.I)
# Claimed state words. No "fixed": guides write "fixed at HEAD" / "fixed on main"
# about the CODE while the tracker stays open — reading it as CLOSED misfires.
CLAIM_PATTERNS = [(re.compile(r"\b(?:merged|landed)\b", re.I), "MERGED"),
                  (re.compile(r"\bclosed\b", re.I), "CLOSED"),
                  (re.compile(r"\bopen(?:ed)?\b", re.I), "OPEN")]
RE_NEGATED = re.compile(r"\b(?:not|never|no)[\s`'\"*]*$|n't[\s`'\"*]*$", re.I)

def parse_args(argv):
    opts = {"repo": None, "changed_only": False, "extract_only": False, "tsv": None}
    it = iter(argv)
    for a in it:
        if a == "--repo":
            opts["repo"] = next(it, None) or sys.exit("--repo needs an owner/repo argument")
        elif a == "--changed-only":
            opts["changed_only"] = True
        elif a == "--extract-only":
            opts["extract_only"] = True
        elif a == "--tsv":
            opts["tsv"] = next(it, None) or sys.exit("--tsv needs a file argument")
        elif a in ("-h", "--help"):
            print(__doc__ or "see the shell header for usage"); sys.exit(0)
        else:
            sys.exit(f"unknown argument: {a} (see header of scripts/refresh-defect-statuses.sh)")
    return opts

# ---- extraction ---------------------------------------------------------------
def paragraphs(path):
    """Yield (start_lineno, text) per blank-line-delimited block — except table
    rows, which each yield alone: a markdown table is one blank-line block, so
    row-scoping stops a repo named in row 3 from capturing the bare #N in row 9."""
    block, start = [], None
    def flush():
        nonlocal block, start
        if block:
            yield_val = (start, "\n".join(block))
            block, start = [], None
            return yield_val
        return None
    for i, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("|"):
            v = flush()
            if v:
                yield v
            if line.lstrip().startswith("|"):
                yield i, line
        else:
            if start is None:
                start = i
            block.append(line)
    v = flush()
    if v:
        yield v

def nearest(matches, off):
    """matches: [(offset, value)] -> value nearest to off, or None."""
    return min(matches, key=lambda m: abs(m[0] - off))[1] if matches else None

def nearest_mention(mentions, start, end, text):
    """Map a bare #N to a repo mention in the same paragraph.

    Prefer the nearest mention BEFORE the ref: prose and enumerations name the
    repo first ("mlx #3777, #3830 … and mlx-lm #1425" — every number belongs to
    the name on its left). Two exceptions learned from the corpus:
      - "#1585 (mlx-lm, …)": a parenthesized repo tight after the number beats a
        farther preceding one.
      - "across mlx, mlx-lm and mlx-swift-lm: issues #217, #259 …": when the
        nearest preceding mention just ends a LIST of repo names (another repo
        within a few chars, no # between), any pick is a coin flip -> ambiguous.
    """
    after = [m for m in mentions if m[0] >= end]
    if after:
        first = min(after)
        gap = text[end:first[0]]
        if len(gap) <= 12 and "(" in gap and "#" not in gap:
            return first[1]
    before = sorted(m for m in mentions if m[0] <= start)
    if not before:
        return nearest(mentions, start)
    m1 = before[-1]
    for m0 in before[:-1]:
        if m0[1] != m1[1] and 0 < m1[0] - m0[0] < 40 and "#" not in text[m0[0]:m1[0]]:
            return None
    return m1[1]

def claim_near(text, start, end):
    """Parse the guide's claimed state for the ref at [start:end).

    Prose states a ref's status AFTER it ("#420 (OPEN as of …)", "PRs #7 through
    #18 were merged") or tightly before it ("merged PRs #62"). A distant
    preceding word usually belongs to a different list ("merged PRs #62, #74 …
    and issues #5" must not claim MERGED for #5) — hence 80 chars after but only
    40 before. Negated words ("have not landed") claim nothing."""
    def scan(seg, dist):
        found = []
        for pat, state in CLAIM_PATTERNS:
            found += [(dist(m), state) for m in pat.finditer(seg)
                      if not RE_NEGATED.search(seg[max(0, m.start() - 12):m.start()])]
        return found
    after = scan(text[end:end + 80], lambda m: m.start())
    if after:
        return min(after)[1]
    seg = text[max(0, start - 40):start]
    before = scan(seg, lambda m: len(seg) - m.end())
    return min(before)[1] if before else None

# Generated indexes (rebuilt by scripts/build-indexes.sh): their rows mirror the
# per-part guide text this scan already covers, and their "Failure #N" labels are
# not GitHub refs — scanning them would only add duplicate and phantom rows.
GENERATED = {Path("guides/SILENT-FAILURES.md"), Path("guides/API-INDEX.md")}

def extract():
    """-> list of sightings: dict(file,line,repo,num,form,claim,date,context)"""
    sightings = []
    for path in sorted(Path("guides").rglob("*.md")):
        if path in GENERATED:
            continue
        for start, text in paragraphs(path):
            mentions = [(m.start(), ALIASES[m.group(1)]) for m in RE_MENTION.finditer(text)]
            mentions += [(m.start(), m.group(1)) for m in RE_URL.finditer(text)]
            dates = [(m.start(), m.group(1)) for m in RE_ASOF.finditer(text)]
            spans, refs = [], []
            def take(m, repo, num, form):
                if any(m.start() < e and m.end() > s for s, e in spans):
                    return
                spans.append((m.start(), m.end()))
                refs.append((m.start(), m.end(), repo, num, form))
            for m in RE_URL.finditer(text):
                take(m, m.group(1), int(m.group(2)), "url")
            for m in RE_OWNER.finditer(text):
                take(m, m.group(1), int(m.group(2)), "owner-repo")
            for m in RE_ADJ.finditer(text):
                take(m, ALIASES[m.group(1)], int(m.group(2)), "repo-adjacent")
            if RE_DEFECTISH.search(text):  # bare #N only in defect-ish paragraphs
                for m in RE_BARE.finditer(text):
                    take(m, nearest_mention(mentions, m.start(), m.end(), text),
                         int(m.group(1)), "bare")
            for off, end, repo, num, form in refs:
                line = start + text.count("\n", 0, off)
                snippet = " ".join(text[max(0, off - 60):off + 60].split())
                sightings.append(dict(file=str(path), line=line, repo=repo, num=num,
                                      form=form, claim=claim_near(text, off, end),
                                      date=nearest(dates, off), context=snippet))
    return sightings

# ---- live lookup --------------------------------------------------------------
def gh(*args):
    try:
        p = subprocess.run(["gh", *args], capture_output=True, text=True, timeout=30)
    except (subprocess.TimeoutExpired, OSError) as e:
        return None, str(e)
    if p.returncode != 0:
        return None, (p.stderr or p.stdout).strip().splitlines()[0][:120] if (p.stderr or p.stdout).strip() else "gh failed"
    try:
        return json.loads(p.stdout), None
    except json.JSONDecodeError:
        return None, "unparseable gh output"

def lookup(repo, num):
    """-> dict(kind,state,closed_at,title) or dict(error=...). One REST call answers
    for both issues and PRs; view-command fallbacks in case /issues/N is denied."""
    data, err = gh("api", f"repos/{repo}/issues/{num}")
    if data:
        pr = data.get("pull_request") or {}
        state = ("MERGED" if pr.get("merged_at")
                 else "CLOSED" if data.get("state") == "closed" else "OPEN")
        reason = data.get("state_reason")
        return dict(kind="PR" if pr else "issue", state=state,
                    closed_at=(data.get("closed_at") or "")[:10],
                    reason=reason if reason not in (None, "", "completed") else None,
                    title=data.get("title") or "")
    data, _ = gh("issue", "view", str(num), "--repo", repo,
                 "--json", "state,stateReason,closedAt,title")
    if data:
        return dict(kind="issue", state=data["state"], closed_at=(data.get("closedAt") or "")[:10],
                    reason=(data.get("stateReason") or None), title=data.get("title") or "")
    data, _ = gh("pr", "view", str(num), "--repo", repo,
                 "--json", "state,closedAt,mergedAt,title")
    if data:
        return dict(kind="PR", state=data["state"], closed_at=(data.get("closedAt") or "")[:10],
                    reason=None, title=data.get("title") or "")
    return dict(error=err or "unreachable")

# ---- verdicts and report ------------------------------------------------------
def verdict(live, claims, date):
    if live is None:
        return "AMBIGUOUS"
    if "error" in live:
        return "UNREACHABLE"
    # Compatibility, not equality: a MERGED pr satisfies a "closed" claim, and a
    # CLOSED issue satisfies a "merged" claim (the word belonged to its fix-PR:
    # "issue #17 …, fixed by PR #18 (merged …)"). A closed-UNMERGED PR claimed
    # merged stays a mismatch — that one matters.
    ok = {"OPEN": {"OPEN"}, "MERGED": {"MERGED", "CLOSED"},
          "CLOSED": {"CLOSED"} if live["kind"] == "PR" else {"CLOSED", "MERGED"}}[live["state"]]
    if claims:
        return "UNCHANGED" if all(c in ok for c in claims) else "STATE-CHANGED"
    if live["state"] != "OPEN" and date and live.get("closed_at") and live["closed_at"] > date:
        return "STATE-CHANGED"          # closed after the guide's hedge date
    return "STALE-DATE-ONLY" if date else "UNCHANGED"

def main():
    opts = parse_args(sys.argv[1:])
    sightings = extract()
    if opts["repo"]:
        sightings = [s for s in sightings if s["repo"] == opts["repo"]]
    tsv_lines = ["file\tline\trepo\tnumber\tform\tclaimed_state\tclaim_date\tcontext"]
    tsv_lines += ["\t".join(str(s[k]) if s[k] is not None else "?"
                            for k in ("file", "line", "repo", "num", "form", "claim", "date", "context"))
                  for s in sightings]
    if opts["tsv"]:
        Path(opts["tsv"]).write_text("\n".join(tsv_lines) + "\n")
        print(f"<!-- extraction TSV written to {opts['tsv']} -->", file=sys.stderr)
    if opts["extract_only"]:
        print("\n".join(tsv_lines)); return

    # Dedupe -> one live query per distinct ref. Ambiguous refs (repo unknown)
    # key on the file too: a bare #7 in two different guides is two different
    # defects, and collapsing them would hide one.
    distinct = {}
    for s in sightings:
        key = (s["repo"], s["num"]) if s["repo"] else (s["file"], s["num"])
        distinct.setdefault(key, []).append(s)
    rows = []
    for (_, num), group in sorted(distinct.items(), key=lambda kv: (kv[0][0] or "~", kv[0][1])):
        repo, live = group[0]["repo"], None
        if repo is not None:
            live = lookup(repo, num)
            time.sleep(0.15)            # be polite; ~190 distinct queries
        claims = sorted({s["claim"] for s in group if s["claim"]})
        date = max((s["date"] for s in group if s["date"]), default=None)
        rows.append(dict(repo=repo, num=num, live=live, claims=claims, date=date,
                         n=len(group), first=f'{group[0]["file"]}:{group[0]["line"]}',
                         verdict=verdict(live, claims, date)))

    order = {"STATE-CHANGED": 0, "STALE-DATE-ONLY": 1, "AMBIGUOUS": 2, "UNREACHABLE": 3, "UNCHANGED": 4}
    rows.sort(key=lambda r: (order[r["verdict"]], r["repo"] or "~", r["num"]))
    counts = {}
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1

    print(f"# Defect-status report — {time.strftime('%Y-%m-%d')}\n")
    print("| ref | kind | title | guide claim | live | sightings | verdict |")
    print("|---|---|---|---|---|---|---|")
    for r in rows:
        if opts["changed_only"] and r["verdict"] != "STATE-CHANGED":
            continue
        live = r["live"]
        if live is None:
            kind, livecol, title = "?", "?", ""
        elif "error" in live:
            kind, livecol, title = "?", f"error: {live['error']}", ""
        else:
            kind = live["kind"]
            livecol = live["state"] + (f" ({live['reason']})" if live.get("reason") else "") \
                      + (f" {live['closed_at']}" if live["closed_at"] else "")
            title = live["title"][:46].replace("|", "\\|")
        ref = f'{r["repo"] or "?"}#{r["num"]}'
        claim = ("/".join(r["claims"]) or "—") + (f' as of {r["date"]}' if r["date"] else "")
        print(f'| {ref} | {kind} | {title} | {claim} | {livecol} | {r["n"]}× {r["first"]} | **{r["verdict"]}** |')

    total = len(rows)
    parts = ", ".join(f"{counts.get(v, 0)} {v}" for v in order)
    print(f"\n**Summary.** {total} distinct refs across {len(sightings)} sightings in guides/: "
          f"{parts}. STATE-CHANGED rows are where a guide's hedge no longer matches GitHub "
          f"and need a human edit; STALE-DATE-ONLY rows only need their 'as of' date bumped "
          f"(or nothing); AMBIGUOUS rows are bare #N mentions whose paragraph names no repo — "
          f"consider naming the repo inline; UNREACHABLE rows could not be queried (offline, "
          f"deleted, or a wrong repo mapping) and should be retried. This report never edits "
          f"guides/ — apply changes by hand from the rows above.")

main()
PY
