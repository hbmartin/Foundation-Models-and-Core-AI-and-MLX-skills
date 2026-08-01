# Apple on-device AI: Foundation Models, Core AI, and MLX

An independent, evidence-backed guide and research corpus for Apple's 2026 on-device AI stack:
Foundation Models, Core AI, MLX, Evaluations, Speech, and Metal. The guides cover the iOS 27,
iPadOS 27, macOS 27, watchOS 27, visionOS 27, tvOS 27, and Xcode 27 generation, including migration
from the preceding platform generation.

The Markdown under [`guides/`](guides/) is the canonical published corpus. Generated indexes and
the MkDocs site are derived from it; edit the guide sources, not generated documentation output.

## Using the guides with a coding agent

The corpus ships as ten installable [Agent Skills](https://agentskills.io), generated from
`guides/` into [`skills/`](skills/). They give Claude Code — or any agent that reads `SKILL.md` —
the series' routing power inside a project, without pulling 11 MB into a context window.

```bash
npx skills add hbmartin/Foundation-Models-and-Core-AI-and-MLX-skills --all
```

Install one instead of all ten with `--skill apple-mlx`, and add `-g` to install for every project
rather than the current one. The available skills are `apple-on-device-ai` (start here: which stack
to use, and platform gating), `apple-foundation-models`, `apple-core-ai`, `apple-mlx`,
`apple-ai-evaluations`, `apple-metal-tensorops`, `apple-ai-shipping`, `apple-speech`,
`apple-app-intents`, and `apple-ai-migration`. See [`skills/README.md`](skills/README.md) for what
each one covers.

Each skill's `SKILL.md` is a router, not a copy of a guide: it carries the evidence-marker
conventions, the version floors, a triage table, and a lookup protocol. The material sits in
`references/`, which costs nothing until read — the part READMEs, a symbol index and a
silent-failure index both sliced to that skill, and section maps addressing the deep reference
guides that stay in this repository.

`skills/` is generated and committed; edit the guides and run `./scripts/build-skills.sh`. A
[test](scripts/tests/test_skills.py) byte-compares the committed tree against a clean regeneration,
so skills cannot drift from the corpus.

## Maintaining the corpus

Start with the [freshness runbook](notes/FRESHNESS-RUNBOOK.md). It separates the small daily sweep
from weekly checks and the heavier workflow triggered by a new Xcode beta, SDK, simulator runtime,
or OS release. For a toolchain change, follow the
[next-beta checklist](notes/NEXT-BETA-CHECKLIST.md) in order.

### Evidence conventions

Every non-obvious API claim in the guides uses an explicit evidence state:

- **✅ VERIFIED** — confirmed by an SDK interface, header, shipping source file, or Apple
  documentation.
- **🟡 RECONSTRUCTED** — the behavior or concept is attested, but an exact spelling or shape is
  inferred.
- **🔴 GAP** — the evidence is not yet sufficient; the guide states what is unknown and what would
  resolve it.
- **⚠️ SILENT FAILURE** — a failure mode that can produce wrong output, empty output, or a performance
  cliff without throwing an error.

Do not turn a reconstruction into a verified claim without adding the supporting evidence. Keep
version floors, measurement attribution, and open-gap ledgers current when editing a guide. The
full house rules are in the guide series' [editorial conventions](guides/README.md#editorial-conventions).

### Portable checks

The repository's pure-Python checks use the standard library and run on Linux and macOS:

```bash
python3 -m unittest discover -s scripts/tests -p 'test_*.py' -q
```

This exercises the index tooling, committed-index consistency, snippet-verifier logic, and MkDocs
publishing hook. It does not compile guide snippets against Apple SDKs or execute runtime probes.

When guide headings, API references, or silent-failure callouts change, regenerate the committed
indexes:

```bash
./scripts/build-indexes.sh
```

New silent-failure callouts require classification before regeneration; see the
[symptom taxonomy](notes/synthesis/SYMPTOM-TAXONOMY.md). Review changes to
[`guides/API-INDEX.md`](guides/API-INDEX.md) and
[`guides/SILENT-FAILURES.md`](guides/SILENT-FAILURES.md) rather than editing either index by hand.

Then refresh the installable skills, which derive from the same guides:

```bash
./scripts/build-skills.sh
```

This refuses to run if a part README grew a heading the router generator does not recognize, so a
structural guide edit fails here rather than quietly dropping a section from a published skill.
Ownership of parts and the hand-tuned skill descriptions live in
[`notes/synthesis/skill-manifest.json`](notes/synthesis/skill-manifest.json).

### macOS and Xcode checks

These workflows require Apple toolchains and are intentionally not part of Linux CI:

```bash
# Type-check changed Swift snippets against the configured SDK targets.
./scripts/verify-snippets.sh --changed

# Verify the selected Xcode, SDKs, Metal Toolchain, manifest, and captured hashes without writing.
DEVELOPER_DIR=/Applications/Xcode-beta.app/Contents/Developer \
  ./scripts/dump-sdk-interfaces.sh --check-only

# Run executable evidence probes on the current macOS host.
cd probes && swift test
```

The snippet driver expects the stable and beta Xcode locations documented in the
[snippet-verification guide](notes/snippet-verification/README.md). SDK captures are managed by a
hashed provenance manifest; read the [SDK interface evidence guide](notes/sdk-interfaces/README.md)
before capturing or promoting a new seed. Runtime destinations, environment knobs, expected skips,
and the `PROBE-RESULT` contract are documented in [`probes/README.md`](probes/README.md).

### MkDocs publishing

The [documentation Pages workflow](.github/workflows/pages.yml) is the publishing source of truth.
It tests the render-only Markdown hook, builds the site with warnings as errors, verifies the main
routes and search index, and checks that the source guides were not modified. The generated site is
disposable and is not committed.

To preview the same site locally:

```bash
python3 -m venv .build/docs-venv
.build/docs-venv/bin/python -m pip install -r requirements-docs.txt
.build/docs-venv/bin/mkdocs serve
```

Run `.build/docs-venv/bin/mkdocs build --strict --clean` for the production check. The publishing
stack uses Python only; it does not install Swift or fetch a separate renderer.

### Freshness and research mirrors

GitHub issue and pull-request states cited by the guides can be checked with:

```bash
./scripts/refresh-defect-statuses.sh --changed-only
```

This command queries GitHub and requires `gh` access. Third-party repositories used during research
are also excluded from Git; recreate the exact pinned snapshots with
`./scripts/clone-research-repos.sh`. Treat both commands as evidence refreshes, then update guide
claims deliberately under the conventions above.

## Repository map

| Path | Purpose |
|---|---|
| [`guides/`](guides/) | Canonical 17-part guide series, reference guides, and generated cross-cutting indexes. |
| [`skills/`](skills/) | Generated, installable agent skills derived from `guides/`. Edit the guides, not these. |
| [`notes/`](notes/) | Research synthesis, maintenance runbooks, captured SDK interfaces, and verification results. |
| [`probes/`](probes/) | SwiftPM runtime probes that turn documented behavioral gaps into executable evidence. |
| [`scripts/`](scripts/) | Indexing, verification, SDK capture, MkDocs, freshness, and research-mirror tooling. |
| [`docs/`](docs/) | Captured Apple documentation used as source material. |
| [`forums/`](forums/) | Developer Forum source corpus. |
| [`transcripts/`](transcripts/) | WWDC and technical-session transcripts used by the research corpus. |
| `repos/` | Ignored, reproducible checkouts of pinned upstream research repositories. |

## Reading the guides

The [guide-series overview](guides/README.md) is the reader entry point and owns the complete
17-part table of contents. Start with [Part 1: Orientation and gating](guides/part-01-orientation-and-gating/)
for the stack map and platform gates. Use the [API and symbol index](guides/API-INDEX.md) to find
coverage by identifier, or the [silent-failure index](guides/SILENT-FAILURES.md) to troubleshoot by
observed symptom.
