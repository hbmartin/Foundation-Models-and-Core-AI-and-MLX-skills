# Apple Foundation Models runtime-performance evidence — 2026-09-22

**Capture date:** 2026-09-22

**Method:** Direct Apple documentation `.md` responses, fetched from the URLs below as Markdown.
This note preserves the provenance and the small excerpts used by the guides; it intentionally does
not copy either full page.

## Captures

| Apple page | Direct Markdown URL | SHA-256 |
|---|---|---|
| *Analyzing the runtime performance of your Foundation Models app* | `https://developer.apple.com/documentation/foundationmodels/analyzing-the-runtime-performance-of-your-foundation-models-app.md` | `1dca2e84e0da356d5b61f04a9b720776e4df26610c3e7493b6e18fec14d73110` |
| *Optimizing key-value caching in language model sessions* | `https://developer.apple.com/documentation/foundationmodels/optimizing-key-value-caching-in-language-model-sessions.md` | `3ce642e4e431912b276a1f4b7c9536d7d6d5b03ed8b9398f0301d601ca3bbde4` |

The runtime-performance response was 10,204 bytes / 189 lines; the KV-caching response was 15,328
bytes / 296 lines. Hash the response bytes, without rewriting line endings, to reproduce the values
above.

### Relationship to the July capture

`notes/transcripts/fm-advanced.md` preserves excerpts and analysis from the July 2026 Noema/mirror
copies of both pages. That older material remains historical evidence for what the project read then,
but its runtime-performance summary names a different token-metric set. The direct Apple responses
captured here supersede it for claims about the **current** lane names, inspector fields, and token
metrics. They do not erase the older capture or its more detailed KV-caching research notes.

## Runtime-performance page: targeted evidence

The launch sequence is Product > Profile, select the Foundation Models template, then click Choose.
Recording begins with the **Record Trace** button or File > Record Trace. The page says that the
timeline width of each component indicates its latency and enumerates these six lanes:

1. **Session** — the interval in which a session is active.
2. **Request** — the time to perform a request in a session.
3. **Instructions** — the instructions associated with the request.
4. **Model Inference** — input processing and response computation.
5. **Tool** — when the tool call occurs and how long its work takes.
6. **Model Loading** — loading model data from storage before a request.

The page says the inspector contains the request's instructions, prompt, response, duration, and token
metrics. For custom tools, the instrument shows where and how the model invokes them, how long each tool
takes, and its output. It does **not** say that tool-call arguments are necessarily shown.

The four documented token metrics are:

- **Total Tokens** — consumed input plus generated output tokens.
- **Consumed Tokens** — prompt, instructions, transcript, and other prompt metadata such as tool
  definitions.
- **Generated Tokens** — model output tokens.
- **Cached Tokens** — input tokens reused from a previous request.

The page describes cache hit rate as the percentage of input tokens served from the prefix cache. It
does not list reasoning tokens as one of the instrument's four token metrics.

The schema-saving statement used in Part 2 and Part 5 is preserved verbatim:

> Excluding the schema removes redundant schema information and can save hundreds of tokens per
> request.

## KV-caching page: targeted evidence

The page's Instruments procedure says to compute cache hit rate by dividing **cached input tokens by
total input tokens**. A low rate between turns signals cache invalidation and reprocessing of the full
prefix. In the current runtime-performance page's inspector labels, the numerator is **Cached Tokens**
and the total-input denominator is **Consumed Tokens**; **Total Tokens** also includes generated output
and is not the denominator.

It also documents the dependency order — instructions, then tool definitions, then transcript entries
— and explains that changing instructions invalidates the cached tool definitions and transcript,
whereas a change deep in the transcript invalidates only the values that follow it.

## Evidence boundary

These captures establish the launch, recording, six-lane, timeline-width, inspector, tool-duration and
output, token-metric, cache-hit, and schema-exclusion claims above. They do not establish a dedicated
prewarm-completion indicator, a reasoning-token instrument metric, or visibility of tool-call arguments.
Those claims require separate evidence or must remain marked for re-verification.
