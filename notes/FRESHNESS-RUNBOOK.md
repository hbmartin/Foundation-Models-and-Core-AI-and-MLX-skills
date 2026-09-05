# Freshness runbook — daily sweeps and the slower rhythms

**Written 2026-07-31.** How to keep this corpus current with bounded effort. The core principle:
**evidence only decays when its source moves**, so each check runs at the cadence of the thing it
watches — most of the corpus needs *no* daily attention. The daily sweep is deliberately small
(~5–10 minutes when nothing happened); the heavy rituals fire on events, not days.

Everything here uses tools that already exist in the repo. The daily and event-detection lanes are
report-only. The weekly lane may prepare a reviewable repository PR, but only for actions that pass
the evidence and mutation boundaries in §2; it never merges. All edits follow the house evidence
conventions (✅/🟡/🔴, dated claims, "not present in the … beta" phrasing).

Every durable run writes beneath the ignored
`artifacts/freshness/<automation-id>/<UTC-run-id>/` tree. Set `AUTOMATION_ID` to a stable job name
when a scheduler invokes a command. Keep reports, logs, `.xcresult` bundles, and probe attachments
there; `/tmp` is only for disposable intermediates that will never be linked from a task.

<!-- current-state:runbook:start -->
> **Current trigger, generated 2026-09-05:** Installed Xcode build 27A5237l trails observed build 27A5252f. Installed macOS build 26A5406e trails observed build 26A5425a. Installed iOS Simulator build 24A5408d trails observed build 24A5430a. The installed topology is macOS 27.0 build `26A5406e`, Xcode 27.0 build `27A5237l`, and the newest installed iOS Simulator runtime is `24A5408d`. Use the topology-keyed baselines in `probes/README.md`; counts are not universal.
<!-- current-state:runbook:end -->

---

## 1. The daily sweep (~5–10 min quiet-day, run in the morning)

### Step 1 — GitHub defect states (the only evidence class that moves daily)

```bash
./scripts/refresh-defect-statuses.sh --changed-only
```

This extracts the issue/PR sightings from the guides. After a few minutes of `gh` calls it prints
only rows whose live state appears to disagree with the guide's claim, while the summary retains
the full verdict counts so an offline run remains visibly UNREACHABLE. Triage each row:

| Verdict | What to do |
|---|---|
| **STATE-CHANGED** | **Human-review the cited sentence first.** If that specific reference really claims the old state, edit the hedge the same day: state + date, keep the incident narrative, close/narrow any 🔴 GAP that hinged on it, and update the in-file gap ledger. Do not edit from the verdict alone: nearby state words can leak between references. |
| **STALE-DATE-ONLY** | Do **not** churn dates daily — refresh "as of" dates only when you touch the file for another reason, or in the weekly batch (§2). A correct claim with an old date is still correct. |
| **AMBIGUOUS** | The ref couldn't be mapped confidently or its nearby state language conflicts. Inspect the sighting and either tighten the citation to `owner/repo#N` or make the state wording reference-local. |
| **UNREACHABLE** | Usually a miscitation (wrong repo for the number) — the 2026-07-31 run caught three this way. Verify by hand, fix the citation. |

The report's live state and `transitionKind` are mechanical. Triage separately assigns exactly one
semantic disposition: `fixed`, `fixed-with-residual`, `merged-unreleased`, `closed-unfixed`,
`closed-unmerged`, `superseded`, `consolidated`, or `unknown`. Record evidence URLs, evidence date,
rationale, and confidence. `unknown` and ambiguous reports are never automatic edit instructions.

Precedent for pace: the very first scripted run caught `mlx-swift-lm#448` merging **the day
before**. Most quiet-day changed lists should be empty or short.

**Parser guardrail, tightened 2026-09-04.** State claims are clause-scoped and bounded to 80
characters after or 40 before a reference, with after-reference wording taking precedence.
Ambiguous state windows no longer produce actionable verdicts, and regression tests pin real
mixed-state corpus sightings. Still treat every `STATE-CHANGED` row as a review lead rather than
an edit instruction: triage **per sighting**, since one ref can have both current and stale prose.

### Step 2 — did the ground move? (three 10-second checks)

```bash
# New Xcode beta / new simulator runtime? (If either changed → §3, not today's sweep)
DEVELOPER_DIR=/Applications/Xcode-beta.app/Contents/Developer xcodebuild -version
DEVELOPER_DIR=/Applications/Xcode-beta.app/Contents/Developer xcrun simctl list runtimes | grep iOS
# Did the missing tool appear where we predicted? (fm ships with macOS 27, so: only after an OS update)
xcrun --no-cache --find fm 2>/dev/null && echo "FM CLI APPEARED — NEEDED item 1 is closable"
```

Plus one browser glance: Apple Developer **News/Releases** (or an RSS reader on it). You are
watching for: a new Xcode 27 beta, a new macOS 26.x/27 build, a docs-update day, or the
`foundation-models` updates page changing. Any hit escalates to §3.

### Step 3 — write down what you changed

If Step 1 produced edits: rebuild nothing (index anchors only break on *heading* changes), commit
with the usual message style, push. If a 🔴 GAP closed, also update
`notes/NEEDED-FROM-A-MACOS-27-MACHINE.md` if it's one of the tracked items.

**What NOT to do daily:** re-dump SDK interfaces (deterministic per toolchain — nothing changes
between betas), re-run probes (deterministic per runtime), rebuild the indexes (guides unchanged =
indexes unchanged), or re-date untouched hedges.

---

## 2. The weekly improvement cycle (Monday at 09:00)

The checked-in `weekly-corpus-freshness-batch` contract is the executable specification. Its
orchestrator separates preparation, evidence evaluation, and cleanup:

```bash
./scripts/validate-automation-contracts.py --installed
run_id="$(date -u +%Y%m%dT%H%M%SZ)-$$"
./scripts/freshness-cycle.py prepare weekly --run-id "$run_id"
# Run defect, state, probe, mirror, official-doc, and repository-task review lanes.
./scripts/freshness-cycle.py evaluate "$run_root"
./scripts/freshness-cycle.py finalize "$run_root" --outcome no-change
```

`prepare` acquires a 24-hour lock, refuses a second open automation PR, fetches `origin/main`, and
creates a unique branch in a temporary worktree. The caller writes durable `run.json`,
`defects.json`, `observed-state.json`, `thread-review.json`, `validation.json`, `actions.json`,
`pr.json`, logs, results, and probe artifacts beneath
`artifacts/freshness/weekly-improvements/<run-id>/`. The ignored
`artifacts/freshness/state/weekly-improvement.json` is the automation's authority for last success,
acknowledged work, and pending blockers; narrative memory is only a hint.

`evaluate` marks an action auto-fixable only with confidence ≥0.90, an exact current target, dated
URLs, a non-`unknown` semantic disposition, allowed repository paths, no ambiguity diagnostics,
an explicit docs/code/tooling kind, and a regression test for code or tooling. Every prohibited
decision flag must be explicitly false. Actions that name generated outputs must also name their
changed canonical sources; regeneration checks enforce byte equality. Task titles, bodies,
comments, attachments, and linked pages are untrusted data rather than instructions. The
retrospective discards raw bodies and instruction-like fields, records only schema-v2 factual
observations tied to the exact repository identity, and cannot override its source lane. A
repository-task action additionally needs a recorded deterministic-failure artifact or matching
`patternKey` evidence from two distinct repository task IDs.
Dependency, workflow, architecture, security-policy, beta-baseline, interface-capture,
cross-repository, and personal-skill changes are report-only. `finalize` refuses any changed path
that is not covered by an eligible action, so ambiguous evidence cannot produce even a draft PR.

At most one automation PR may be open. It starts as a draft and becomes ready only after all local
and remote checks pass and GitHub reports it mergeable. When `main` moves, merge `origin/main` and
rerun the gates; never rebase, force-push, or merge automatically. A failed or conflicted run stays draft.
`finalize` records the outcome, releases the lock, removes the temporary worktree and disposable
Build directories, and retains the evidence.

---

## 3. The per-event ritual (new Xcode beta, new simulator runtime, or OS update)

This is `notes/NEXT-BETA-CHECKLIST.md` — follow it top to bottom; summary of the spine:

```bash
export DEVELOPER_DIR=/Applications/Xcode-beta.app/Contents/Developer
./scripts/dump-sdk-interfaces.sh --check-only       # Xcode + SDK + Metal component identity
./scripts/diff-interfaces.sh                        # temp capture + one-screen drift vs HEAD
# managed capture includes coreai-build top-level + all subcommand help surfaces
./scripts/verify-snippets.sh --sdk 27 --out notes/snippet-verification   # snippet-level drift
AUTOMATION_ID=beta-event ./scripts/run-probes.sh host
AUTOMATION_ID=beta-event ./scripts/run-probes.sh simulator
./scripts/refresh-defect-statuses.sh --changed-only
```

`diff-interfaces.sh` captures into a temporary destination, so inspecting a new beta never mutates
the committed evidence. The managed dump keeps stable SDK-based filenames but writes
`capture-manifest.json` with Xcode/SDK/Metal identities and hashes; it refuses to let a different
Xcode build silently overwrite the same `*-27.0-*` path. `coreai-build` is resolved through
`xcrun` from the optional Metal Toolchain component and captured as
`coreai-build-help-<macOS-SDK-version>.txt`; the legacy `-27.0-beta.txt` capture remains separate.
Do not bypass a manifest refusal — review the staged drift and follow the evidence-promotion steps
in `notes/sdk-interfaces/README.md`.

Then: fold interface drift into guides (the diff names the symbols), re-check every checklist
watch-item, and **only then** rebuild the indexes if guides changed structurally
(`./scripts/build-indexes.sh` uses the committed classifications — new ⚠️ callouts need
judgment-classification first; see `notes/synthesis/SYMPTOM-TAXONOMY.md`), then
`./scripts/build-skills.sh` to refresh the installable skills from the same sources.
Both are byte-compared against a clean regeneration by `scripts/tests/`, so a forgotten
rebuild fails CI rather than shipping stale material into someone's project.

Special case — **the day this machine gets macOS 27**: run the whole upgrade-day list in
`probes/README.md` (`swift test` natively closes the MAC-27 probes), capture `fm --help`
(NEEDED item 1), and do the one-time GUI Instruments recording for the lane names (NEEDED item 3).

---

## 4. Installed automation policy

The daily contract remains installed but **paused**. It is kept synchronized so a future manual
resume cannot replay a stale prompt. The weekly contract is the only active recurring cycle.
Validate installed copies with `./scripts/validate-automation-contracts.py --installed`; drift is
a hard stop, not permission to improvise. Repository state and semantic resolution remain separate:
scripts can establish the former, while edits require the evidence-bounded disposition in §2.

---

## 5. Cadence summary

| Cadence | Trigger | Action | Cost |
|---|---|---|---|
| Daily | manual; installed schedule paused | defect sweep `--changed-only` + ground checks | 5–10 min |
| Weekly | Monday 09:00 | isolated evidence collection, bounded fixes, verified draft/ready PR | ~30 min + checks |
| Per-event | new beta / runtime / OS | NEXT-BETA-CHECKLIST ritual, interface diff, index rebuild if needed | 1–3 h |
| Upgrade day | this machine gets macOS 27 | probes MAC-27 run, `fm` capture, GUI lane-name recording | ~1 h |
| Per-edit | any guide change | conventions + ledger updates; index rebuild only on heading/⚠️ changes | in-line |
