# Snippet compile-verification — results and the marker grammar

`scripts/verify-snippets.py` (driver: `scripts/verify-snippets.sh`) extracts every
```` ```swift ```` fence in `guides/`, classifies it, wraps fragments in a minimal
harness, and runs `swiftc -typecheck` per requested SDK. This directory holds the
committed latest results:

- `results.tsv` — one row per fence: `file line anchor info status wrap v26 v27
  vsim27 v27on26 vsim27on26 err_line first_error` (strict tabs,
  whitespace-flattened fields).
- `report.md` — the human report: toolchain identities (every verdict is "against
  `<sdk build>`", never "against iOS 27" in the abstract), per-guide rollup, failures
  with guide-line-mapped first errors, wrongness-candidates, and the UNCLASSIFIED
  backlog headline. History lives in git history.

## The marker grammar (canonical)

Space-separated tokens after the language word in the fence info string — invisible in
rendered markdown. Unknown keys are a hard MARKER-ERROR.

```
```swift [compile:<t>[,<t>…]] [xfail:<t>[,<t>…]] [imports:M1,M2] [defines:C1,C2] [wrap:none|body|mixed] [lang:5] [isolation:mainactor] [illustrative] [prelude:<name>]
```

| marker | meaning |
|---|---|
| `compile:<t>` | must type-check on each listed target. Targets are **names**, not versions: `26` → `/Applications/Xcode.app` (macOS SDK), `27` → `/Applications/Xcode-beta.app` (macOS SDK), and `sim27` → the beta's iPhoneSimulator SDK. Those three use the resolved SDK version as the deployment floor for compatibility. `27-on-26` and `sim27-on-26` use the SDK-27 macOS/simulator SDK with an explicit 26.0 deployment floor. A new beta changes the resolved SDK identity, never the marker. |
| `xfail:<t>` | must **fail** to type-check on each listed target. A fence with only expected failures reports `XFAIL-PROVEN`; `xfail:26 compile:27` reports `MIGRATION-PROVEN` and proves the before/after boundary. A target may not appear in both lists. |
| `imports:A,B` | modules the wrapper adds beyond those hoisted from the snippet body. Marked fences compile with **only** hoisted + declared imports — guess-mode heuristics never apply to marked fences. |
| `defines:A,B` | custom Swift compilation conditions. Each name is validated as a Swift identifier and passed to `swiftc` with `-D`. A compile/xfail fence using a custom `#if` must declare every condition; a selection that statically compiles the entire body out is a marker error. |
| `wrap:none` | complete file; compile verbatim (no import hoisting). Because this mode is verbatim, combining it with injected `imports:` is a marker error. |
| `wrap:body` | force the `func __verify_snippet() async throws { … }` body wrap. Default (no `wrap:`) is auto: decl-shaped fences compile at file scope, statement-shaped ones get the body wrap, and the alternate is retried on failure. |
| `wrap:mixed` | keep a declaration prefix at file scope and wrap the executable suffix. Auto mode tries this after the all-top and all-body shapes, which makes `@Generable struct …` plus its usage verifiable without moving the macro type into a local scope. |
| `lang:5` | pin `-swift-version 5` for this fence (default is 6). |
| `isolation:mainactor` | pass `-default-isolation MainActor`, matching Swift 6 app targets that opt into MainActor-by-default. Guess mode retries isolation diagnostics this way and records the marker only when it makes the fence compile. |
| `illustrative` | never compiled — pseudocode, `.swiftinterface`-style stubs, elided bodies. Excludes all other markers. |
| `prelude:<name>` | reserved (inert in v1): parser accepts it and reports PRELUDE-NEEDED without compiling — the parking place for fences that reference guide-local types, until per-part prelude files exist. |

Constraint: a 26-generation target on a fence importing `CoreAI` or `Evaluations` is a
hard MARKER-ERROR — those modules are structurally absent from the 26-generation SDKs,
so an xfail there would be trivially true and dishonest. `Evaluations` on SDK-27 targets
resolves via `-F` into the Xcode-bundled developer frameworks automatically. Empty
`imports:`/`prelude:` values, comment/import/directive-only compile bodies, and inactive
custom-condition bodies are also hard marker errors.

An **unmarked** fence is UNCLASSIFIED — never counted as verified. `--guess` attempts
it against the guess target (default 27) with a default wrapper plus a small
keyword-triggered import table; `--write-markers` then records `compile:27`
(+ the actually-needed `imports:`) on clean passers and `illustrative` on detected
stubs/elided fences, editing only opening-fence lines.

`--write-triage-markers` is the conservative second pass. It implies
`--write-markers`, turns declaration/interface syntax into `illustrative`, and
parks missing app symbols, third-party modules, or wrong-platform excerpts behind
an explicit `prelude:` marker. It deliberately leaves ambiguity, type-conversion,
mutability, and Swift 6 isolation diagnostics unmarked for human review. A dirty
guide tree still stops marker writes unless the caller explicitly supplies
`--allow-dirty-guides`; marker writes continue to hash every fence body before and
afterward and refuse any non-info-string change.

`--sdk` is repeatable and additive: it asks Python to resolve and report those
toolchains in addition to every target requested by the selected fences. It is not a
fence filter and does not change a fence's markers. `--guess-target` independently
selects the target for unmarked-fence guessing.

Bare `--changed` compares the merge point with `GITHUB_BASE_REF` when CI provides it,
otherwise with the remote default branch. An explicit `--changed REF` uses that ref.
Both modes union committed branch changes with staged, unstaged, renamed, and untracked
guide files. Git paths are read NUL-delimited relative to the repository root, so names
with spaces, renames, and invocation below the repository root remain correct. Parse
errors are filtered to the same file set; an invalid ref/Git error fails, while a real
zero-guide-change selection succeeds with an explicit message.

The verifier fails closed before changed-file filtering when the guide root is missing
or the full corpus contains no Swift fences. Per-row results include `VERIFIED`,
`XFAIL-PROVEN`, `MIGRATION-PROVEN`, `ILLUSTRATIVE`, `PRELUDE-NEEDED`, and the explicit
failure/error states documented in the report; unselected target columns use `-`.

## Rhythm

- Per beta: `./scripts/verify-snippets.sh --sdk 27` (see `notes/NEXT-BETA-CHECKLIST.md`
  §0) — any green→red row is the beta's snippet-level API drift, symbol named by the
  compiler.
- Per PR touching guides: `./scripts/verify-snippets.sh --changed`.
- CI runs only the pure-Python unit tests (`scripts/tests/test_verify_snippets.py`,
  via the stub compiler); the swiftc runs are local-only, like the SDK-capture tests.
