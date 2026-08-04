# Freshness runbook — daily sweeps and the slower rhythms

**Written 2026-07-31.** How to keep this corpus current with bounded effort. The core principle:
**evidence only decays when its source moves**, so each check runs at the cadence of the thing it
watches — most of the corpus needs *no* daily attention. The daily sweep is deliberately small
(~5–10 minutes when nothing happened); the heavy rituals fire on events, not days.

Everything here uses tools that already exist in the repo. Nothing below edits a guide
automatically — scripts report, humans (or a supervised agent session) fold results in under the
house evidence conventions (✅/🟡/🔴, dated claims, "not present in the … beta" phrasing).

> **Current trigger, checked 2026-08-03:** the host is now on macOS 26.6 build `25G72`, and the §3
> event ritual ran the same day — interface diff clean for every framework, host probes 46/34/0
> with no PROBE-RESULT drift, defect sweep folded in. Xcode 27 beta 4 (`27A5228h`) and the iOS 27
> beta 4 runtime (`24A5390f`) still match the local baseline; `xcrun --no-cache --find fm` still
> exits 72. Next expected event: Xcode 27 beta 5.

---

## 1. The daily sweep (~5–10 min quiet-day, run in the morning)

### Step 1 — GitHub defect states (the only evidence class that moves daily)

```bash
./scripts/refresh-defect-statuses.sh --changed-only
```

This currently extracts 957 sightings of 322 distinct mapped issue/PR refs from the guides. After
a few minutes of `gh` calls it prints only rows whose live state appears to disagree with the
guide's claim. Triage each row:

| Verdict | What to do |
|---|---|
| **STATE-CHANGED** | **Human-review the cited sentence first.** If that specific reference really claims the old state, edit the hedge the same day: state + date, keep the incident narrative, close/narrow any 🔴 GAP that hinged on it, and update the in-file gap ledger. Do not edit from the verdict alone: nearby state words can leak between references. |
| **STALE-DATE-ONLY** | Do **not** churn dates daily — refresh "as of" dates only when you touch the file for another reason, or in the weekly batch (§2). A correct claim with an old date is still correct. |
| **AMBIGUOUS** | The ref couldn't be mapped to a repo. When you're in that file anyway, tighten the citation to the full `owner/repo#N` form so the script can track it forever after. |
| **UNREACHABLE** | Usually a miscitation (wrong repo for the number) — the 2026-07-31 run caught three this way. Verify by hand, fix the citation. |

Precedent for pace: the very first scripted run caught `mlx-swift-lm#448` merging **the day
before**. Most quiet-day changed lists should be empty or short.

**Known parser limitation, 2026-08-01.** `--changed-only` produced five false `STATE-CHANGED`
rows where the cited guide text already matched live state: `apple/coreai-models#62`, `#74`, and
`#89` (merged); `apple/coreai-torch#7` (closed unmerged); and `ml-explore/mlx#3893` (merged).
The failure mode is state-language leakage from another reference in the same paragraph or nearby
OPEN wording. Until claim-context parsing and mixed-state tests are tightened, treat every
`STATE-CHANGED` row as a review lead, not an edit instruction — and triage **per sighting**, not
per ref: the 2026-08-03 pass found a genuinely stale sentence ("Open PR `coreai-torch#7`", part-08
ref 01) hiding behind this same known-false-positive list. A ref on this list can still contain
one sighting that really does claim the old state.

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

## 2. The weekly batch (~30 min, pick a fixed day)

1. **Full defect report, not just changed:** `./scripts/refresh-defect-statuses.sh > /tmp/defects.md`
   — skim STALE-DATE-ONLY and batch-refresh dates in files with several stale hedges; burn down a
   few AMBIGUOUS citations.
2. **Re-run the probe suite** (cheap, catches silent runtime drift if a sim runtime or host
   framework updated underneath you):
   ```bash
   cd probes && swift test   # host: 46 tests, 34 skipped is the 2026-08-03 baseline (macOS 26.6)
   DEVELOPER_DIR=/Applications/Xcode-beta.app/Contents/Developer \
     xcodebuild test -scheme Probes-Package \
       -destination 'platform=iOS Simulator,OS=27.0,name=iPhone 17 Pro'
   ```
   The simulator baseline is 36 tests, 2 intentional skips, 0 failures.
   Any probe whose `PROBE-RESULT` differs from the value recorded in `probes/README.md` is a
   *behavioral drift discovery* — fold it into the owning guide with both values and dates.
3. **Refresh the research mirrors** (`./scripts/clone-research-repos.sh`) so corpus greps against
   `repos/` reflect current upstream HEADs.
4. **Skim the watched-contradiction pages** listed in `notes/NEXT-BETA-CHECKLIST.md` §4–8 (the
   `resolve(in:)`/`resolved(in:)` docs conflict, the Evaluations distribution story, etc.) — these
   are doc-side and can flip without a beta.

---

## 3. The per-event ritual (new Xcode beta, new simulator runtime, or OS update)

This is `notes/NEXT-BETA-CHECKLIST.md` — follow it top to bottom; summary of the spine:

```bash
export DEVELOPER_DIR=/Applications/Xcode-beta.app/Contents/Developer
./scripts/dump-sdk-interfaces.sh --check-only       # Xcode + SDK + Metal component identity
./scripts/diff-interfaces.sh                        # temp capture + one-screen drift vs HEAD
# managed capture includes coreai-build top-level + all subcommand help surfaces
./scripts/verify-snippets.sh --sdk 27 --out notes/snippet-verification   # snippet-level drift
cd probes && swift test && cd ..                    # re-run probes on the new runtime
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

## 4. Automating the daily sweep (optional)

The daily sweep is deliberately script-shaped. Two ways to take yourself out of the loop:

- **launchd/cron**: run `./scripts/refresh-defect-statuses.sh --changed-only` every morning,
  mail/notify yourself only when the changed list is non-empty. Zero-output days cost nothing.
- **A scheduled Claude Code agent** (`/schedule` in a session): have it run the sweep, and when
  rows appear, draft the guide edits *as a report or branch for your review* — keeping the rule
  that nothing lands in guides without the evidence conventions applied deliberately.

Whichever route: keep the human in the fold-in step. The scripts are trustworthy about *state*;
deciding what a state change means for a guide's narrative (close the gap? keep the workaround
advice? re-scope the hazard?) is the part that made this corpus worth reading.

---

## 5. Cadence summary

| Cadence | Trigger | Action | Cost |
|---|---|---|---|
| Daily | morning | defect sweep `--changed-only` + 3 ground checks | 5–10 min |
| Weekly | fixed day | full defect report, probe suite, mirror refresh, doc-watch skim | ~30 min |
| Per-event | new beta / runtime / OS | NEXT-BETA-CHECKLIST ritual, interface diff, index rebuild if needed | 1–3 h |
| Upgrade day | this machine gets macOS 27 | probes MAC-27 run, `fm` capture, GUI lane-name recording | ~1 h |
| Per-edit | any guide change | conventions + ledger updates; index rebuild only on heading/⚠️ changes | in-line |
