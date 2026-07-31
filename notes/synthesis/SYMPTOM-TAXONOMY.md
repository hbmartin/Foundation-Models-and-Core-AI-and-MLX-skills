# Symptom taxonomy for the silent-failure index

Classify every ⚠️ callout row by WHAT THE READER OBSERVES (or would observe too late),
not by which API caused it. Pick exactly one primary symptom id. When two fit, pick the
one the developer would notice first in production.

| id | symptom | definition |
|---|---|---|
| garbage-output | Wrong output | Runs and returns output that is wrong: wrong numbers, garbled/wrong-language text, wrong transcription, corrupted tensors. |
| empty-output | Empty/no-op | Runs and returns nothing where content is expected: nil, empty string/array, zero events, an operation that quietly does nothing. |
| ignored-input | Input ignored | A parameter, flag, option, file, annotation, or config is silently ignored, dropped, or overridden. Includes "valid pack the runtime ignores". |
| perf-cliff | Performance cliff | Silent slowdown: CPU/GPU fallback, ANE ineligibility, cache miss, respecialization, recompilation, sync stalls, thermal throttling. |
| resource-growth | Resource growth | Silent memory/disk growth or leak, quota consumption, battery drain. |
| stale-state | Stale state | Stale or cached data served; invalidation that didn't happen (or happened unexpectedly); state carried over when the reader expects a reset. |
| runtime-unavailable | Compiles-but-unavailable | Compiles/links on the dev machine but fails or degrades at runtime for some users: OS floor, device eligibility, missing asset/model, entitlement, region/locale gate, link failure on older OS. |
| silent-truncation | Truncation/limit | Input or output silently truncated or capped: context window, response size, token budgets, sample limits. |
| misleading-signal | Misleading signal | An error/log/metric that names the wrong cause; errors swallowed; observation APIs that emit nothing; success codes for failed work. |
| precision-loss | Precision loss | Silent numeric precision/dtype change: TF32, quantization side-effects, fp16 accumulation, rounding regime differences. |
| data-loss | Data/artifact loss | Silent loss or overwrite of data or build artifacts: purged assets, dead bookmarks, clobbered files, unarchivable builds. |
| version-drift | Version drift | Same code/artifact behaves differently across OS/SDK/tool/package versions with no signal; deprecations that change behavior. |
| docs-vs-reality | Docs vs reality | Documented behavior differs from what ships: doc-only claims, samples that don't compile, wrong signatures in docs, marketing-vs-SDK naming. |
| footgun-api | API footgun | The API shape invites silent misuse: surprising defaults, order-dependence, name collisions, overload traps, types that look interchangeable but aren't. |
| caution-note | Caution note | A general warning/consideration that is not a silent failure: "read this first", scope notes, historical asides, safety reminders. |

## Blurb rules
- ≤120 chars, plain prose, concrete: what you observe + the cause or trigger. No emoji, no markdown.
- Good: "Adapter loads but generations quietly use the base model when the pack targets a GPU-pipelined bundle"
- Bad: "Silent failure with adapters" (no observable), "See guide" (no content).

## Output format (TSV, one row per input row, same order)
file<TAB>line<TAB>anchor<TAB>kind<TAB>symptom-id<TAB>blurb
Keep file/line/anchor/kind exactly as in the input row.
