# Review: PR #2 — "Correct guide inaccuracies and restore research evidence"

> **Status (2026-07-31):** must-fix #1 (`[^stride-scope]`) and #5 (RESEARCH-INDEX) were applied in
> commit `2e3959e`. The three leftovers were closed in the 2026-07-31 reconciliation pass:
> #2 (the part-17 adapter-sunset ANE reassertions, plus the part-16 speech repeat), #3 (the
> part-03 README and part-04 PCC passages still presenting the 4096 conflict as open), and
> #4 (part-02's PCC image-input GAP box, aligned with part-04's settled ✅). The should-fix and
> script notes were addressed in `2e3959e` and later commits.

**Reviewed:** 2026-07-29, against head commit `8c0b06a` (`codex/pr-1-review-fixes` → `main`).
**Method:** four parallel review passes (guides parts 1–6, 7–11, 12–17, plus scripted mechanical
validation of links/anchors/footnotes/tables/SHA pins), with every high-severity finding
re-verified directly against the files on disk.

---

## Overview

The PR does four things: (1) corrects factual/API inaccuracies across ~56 guides identified in
the review of PR #1, with version scoping (Xcode 26.x vs 27) and footnoted citations; (2)
restores 20 `notes/repos/*.md` evidence files (~43k of the 48k added lines) that an unanchored
`repos/` gitignore rule had hidden; (3) pins all 16 research repos to full 40-char SHAs and
rewrites `scripts/clone-research-repos.sh` to do verified, detached, shallow checkouts; (4)
repairs anchors, tables, and cross-references.

**Verdict: the corrections themselves are sound and unusually well-evidenced, but the sweep is
incomplete — several corrected claims are still asserted in their old form elsewhere in the
corpus.** Since this PR's entire purpose is accuracy, those leftovers are the main blocker.
Nothing found suggests any correction is wrong in substance.

## What verifies clean

- **Mechanical hygiene is excellent** (scripted validation): 1,046 relative links, ~880 anchor
  links, 807 contents-list entries, and all table row/column counts check out; 193 of 194
  footnote refs pair with definitions.
- **Where claims are locally checkable, they're right**: Speech signatures
  (`cancelAndFinishNow() async` nonthrowing, the `finalize*` family `async throws`), App Intents
  `EntityIdentifier`/`FileEntityIdentifier`, and FM `supportsLocale(_:)` at 26.0 all match the
  `notes/sdk-interfaces/*-26.5*.swiftinterface` dumps line-for-line. The 76-guide count
  (17 + 59) is accurate.
- **The reproducibility work is solid**: `bash -n` clean; all 16 SHAs full-length; all 16 local
  `repos/` checkouts match their pins exactly; the restored notes' recorded HEADs agree with the
  pinned SHAs; the `/repos/` gitignore anchor is correct. The script's origin-URL refusal check
  and post-checkout SHA verification are good defensive touches.
- **Code edits fixed real bugs**: an unbound `model` reference in a part-02 snippet, and a
  genuinely flaky double-draw sampler assertion in part-12; async/throws usage is consistent
  everywhere with the signatures the PR asserts.

## Must fix before merge

1. **Broken footnote** — `[^stride-scope]` is referenced twice in
   `guides/part-10-coreai-hardware-authoring-debugging/references/03-llm-export-end-to-end.md:1076`
   and `:3677` but never defined (siblings using the same marker got definitions; this file was
   missed). Renders as literal text on GitHub. Found independently by two review passes.

2. **Retracted ANE-routing claim reasserted as ✅ VERIFIED** —
   `guides/part-17-migration-from-pre-ios-27/references/02-adapter-sunset.md:1653` still states
   "splitting a model into multiple entry-point functions is what routes it to the Neural
   Engine" as a framework fact, citing the same `ModelStructure.swift` evidence and register
   item (C6) that the PR's rewrites in 17.5 and part-14 rescope to optional `coreai-models`
   loader policy.

3. **The 4,096-token "settled" reversal didn't propagate** — the PR declares the 4K-vs-8K
   conflict settled via TN3193 (part-01 map, part-03 ref-01), yet four passages still present it
   as open: `guides/part-03-context-profiles-agentic/README.md:95` flatly says "**nobody in this
   corpus has read TN3193**"; the same README's rows at :56/:89; the part-01 map's discrepancy
   box at :402–408; and part-04's PCC guide at :450–467 and :2459.

4. **The PCC image-input reversal didn't propagate** — part-04 now says "✅ Image input is
   supported" (README:93, ref-01 §13.1), but
   `guides/part-02-foundation-models-everyday-api/references/05-image-input-and-attachments.md:1480`
   still declares "🔴 GAP — image input on PCC" and argues at length against the exact evidence
   part-04 now accepts, then links to the rewritten section.

5. **RESEARCH-INDEX doesn't match the restored corpus** — 3 of the 20 restored files
   (`coreai-models-nonllm.md`, `john-rocky-models.md`, `mlx-tensorops-kernels.md`) are never
   mentioned in `notes/synthesis/RESEARCH-INDEX.md`, whose heading claims "(20 files)" while its
   tables list 17 and line 18's "16 repos + 3 issue-mining sweeps" sums to 19.

## Should fix

- **Dangling section pointers from the part-11 contents cleanup**: three new "(§2.3)" cites in
  `guides/part-11-metal-and-tensorops/references/01-tensorops-and-quantized-operands.md:51,284,287`
  point at a section that contains none of the cited element-type material (the 13-entry dtype
  list no longer exists anywhere in the file), and `references/02-…md:60` still promises that
  guide 01 covers "the 13-entry dtype enum and ~50 legal operand triples." Also
  `guides/part-11-metal-and-tensorops/README.md:74`: the router row for exactly the reader
  asking about version scope still answers "It is 26.x throughout," contradicting the rewritten
  header two paragraphs up.
- **Part-12 scope-truncation left ~a dozen dangling §11/§12/§13/§15 self-references** across
  refs 01, 02, and 06 — and the PR *deleted* the old honest warning that "cross-references to
  them will not resolve," replacing it with a completeness claim. Either fix the references or
  keep the warning.
- **Two mechanical editing slips in part-12** (both confirmed in raw text):
  `guides/part-12-mlx-python/references/05-serving-and-distributed.md:349` has an orphaned
  sentence fragment from the old text, and
  `guides/part-12-mlx-python/references/03-quantization.md:411` edited an editorial sentence
  *inside* a verbatim-quote block whose opening quote is never closed — the block now misquotes
  its own cited source.
- **Broken pipe-escape markup**:
  `guides/part-01-orientation-and-gating/references/01-apple-ai-stack-2026-map.md:1067` wraps
  `<code>&#124;…</code>` HTML inside a backtick code span, so GitHub renders the entities
  literally instead of `<|reasoning_start|>`. Drop the backticks or use
  `` `<\|reasoning_start\|>` ``.
- **Evidence-provenance inconsistencies**: parts 8/9 claim "Xcode 27 `MTLTensor.h`/MPP headers"
  were read (part-09 even prints specific shader-enum spellings with header-level confidence),
  while part 11 — which owns the header evidence — says 27.0 claims come only from Apple's doc
  pages, and every relevant footnote cites only URLs. Similarly, the `[^pcc-images]` footnote
  attributes a PCC recommendation to the "Analyzing images with multimodal prompting" article
  that the corpus's own capture of that article (`notes/web/apple-docs-fm-evals-speech.md`)
  doesn't contain. These may be right against the live 2026 docs — but by the series' own
  sourcing rules they need re-verification or rewording.
- **Stale micro-leftovers**:
  `guides/part-03-context-profiles-agentic/references/02-dynamic-profiles-and-session-state.md:2946`
  symptom table still says transcript mutation "crashes" (the PR's own §14.4 rewrite says it
  throws `transcriptMutationWhileResponding`);
  `guides/part-02-foundation-models-everyday-api/references/06-availability-errors-and-guardrails.md:2783`
  code comment cites a GAP the PR resolved;
  `guides/part-17-migration-from-pre-ios-27/references/02-adapter-sunset.md:211,2183` says
  "17 cloned repositories" vs the README's corrected "16 pinned."

## Script notes (minor, non-blocking)

- The rewrite trades the old script's warn-and-continue on a failed clone for a hard `exit 1`.
  Failing loudly is right for reproducibility, but one moved/private repo or a force-pushed-away
  SHA now aborts the remaining checkouts mid-list — consider collecting failures and exiting
  nonzero at the end.
- If an existing directory has no `origin` remote, `git remote get-url origin` dies under
  `set -e` with a raw git error instead of the intended `!! REFUSING` message.

## Risks & process

- No security concerns: cloning is HTTPS-from-GitHub with SHA pinning plus origin verification —
  a supply-chain improvement over the old floating-HEAD clones.
- The PR body's validation list (link/anchor/footnote checks) evidently ran, but it missed the
  `[^stride-scope]` orphan and the index drift — worth committing the validation script and
  running it in CI rather than ad hoc.
- Scope caveat on this review: OS 27 API facts postdate what the reviewer can verify externally;
  the review checked internal consistency, markdown mechanics, and agreement with the repo's own
  evidence corpus (SDK interface dumps, pinned checkouts) — everywhere those overlap with the
  PR's claims, the claims held up.

**Bottom line**: strong, careful PR that materially improves the corpus; fix the five must-fix
items (all are exactly the class of inaccuracy this PR exists to eliminate) and it's mergeable.
