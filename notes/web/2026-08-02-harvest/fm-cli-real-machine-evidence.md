# The `fm` CLI — first real-macOS-27 evidence (harvested 2026-08-02)

**Why this file exists.** `notes/NEEDED-FROM-A-MACOS-27-MACHINE.md` item 1 and
`guides/part-05-prototyping-profiling-non-swift/references/02-fm-cli-and-python-sdk.md`
(23 🔴 GAPs, the joint-highest in the repo) both rest on the same hole: **nobody on this project
has run `fm --help` on a macOS 27 machine.** This session found third parties who have.

> ⚠️ **Evidence tier.** The machine output here is **third-party attestation**, not a capture by
> this project. It is *stronger* than a narration-only reconstruction (a pasted `--help` block from
> a named build is a primary artifact), but it is *weaker* than running the binary ourselves, so
> those claims remain **🟠 Suggestive**. The exception is `fm serve`'s existence and Chat
> Completions purpose, which an Apple member states in writing in `apple/python-apple-fm-sdk` issue
> #13; S1's help paste independently corroborates that spelling. Behavioral details stay 🔴.

---

## Source inventory

| # | Source | Date | Claimed test platform | Fetch result |
|---|--------|------|----------------------|--------------|
| S1 | Shobhit Agarwal, "Apple's Foundation Models CLI: Running Apple Intelligence From Your Terminal" — `https://iamshobhitagarwal.medium.com/apples-foundation-models-cli-running-apple-intelligence-from-your-terminal-c0ee287c5eb2` | 2026-07-16 | **macOS 27.0, build `26A5378n`** | ✅ partial — paywall/truncation cut the body; the `fm --help` block came through |
| S2 | Varun Nuthalapati, "Local AI in Your Terminal: Scripting with Apple's New fm CLI and MLX" — `https://nuthalapativarun.github.io/mlx-whisper-article/terminal-fm-mlx.html` (GitHub-Pages mirror of a Medium post) | 2026-06 | "macOS 27 developer beta" | ✅ full (mirror is not paywalled) |
| S3 | Hack-Log (note.com), "Local AI becomes standard with the fm command in macOS 27" — `https://note.com/hacklog_stealth/n/ne3c55b94af3f` | 2026-06-09 | "macOS 27" | ✅ full (Japanese; commands verbatim) |
| S4 | Blake Crosley, "Foundation Models from Python: the fm CLI" — `https://blakecrosley.com/blog/foundation-models-python-fm-cli` | 2026-06-09 | **none — WWDC-transcript derived** | ✅ full, but adds no attested output |
| S5 | ChatForest builders-log — `https://chatforest.com/builders-log/apple-fm-cli-python-sdk-fm-serve-openai-compatible-psotu-wwdc-2026/` | ~2026-06 | none | ✅ full — **contradicted by S1, see §4** |
| S6 | `manjunathshiva/fmx` — `https://github.com/manjunathshiva/fmx` | — | macOS 26 (a *substitute*, not `fm`) | ✅ full — **do not cite as `fm` grammar**, see §5 |
| S7 | `brianwestphal/apple-fm` — `https://github.com/brianwestphal/apple-fm` | — | third-party CLI | not fetched |

The corroboration that matters: **S1, S2 and S3 are independent** (different authors, different
months, two languages) and their command grammars agree wherever they overlap.

---

## 1. Installed path — closes the "installed path" GAP (guide §, line ~189)

S1 reports the binary as a **system binary at `/usr/bin/fm`**, preinstalled with macOS 27 (no
download, no Xcode component), and attaches a build number. S4 repeats the path but is explicitly
WWDC-transcript-derived, so it is secondary corroboration rather than a second machine run.

The guide currently asks "`/usr/bin/fm`? `/usr/local/bin`? inside Xcode?" — S1/S4 answer
`/usr/bin/fm`, i.e. the *first* of the guide's three guesses, and consistent with the repo's
own negative finding that an exhaustive `find` of Xcode-beta.app returns nothing.

## 2. The subcommand list — closes the `"and more"` GAP (guide line ~214, ~3434)

S1 pasted the top-level help. Reproduced as a short quotation for identification:

```text
% fm --help

USAGE
    % fm <command> [options]

COMMANDS
    available     Check model availability
    chat          Start an interactive chat session
    quota-usage   Check model quota usage
    respond       Generate a response to a prompt
    schema        Generate a structured output generation schema
    serve         Start a Chat Completions API server
    token-count   Count tokens in a…          ← S1's page truncates here
```

**Seven subcommands.** The guide already had `respond`, `chat`, and `schema` from session 334 plus
an Apple member's written statement that `serve` exists as a Chat Completions endpoint. S1's help
paste independently corroborates `serve`; **three subcommands are new to this corpus:**

| Subcommand | One-line help (per S1) | Corpus status before today |
|---|---|---|
| `available` | Check model availability | **never mentioned** — maps to `SystemLanguageModel.Availability` |
| `quota-usage` | Check model quota usage | **never mentioned** — maps to `QuotaUsage` / PCC quota (Part 4) |
| `token-count` | Count tokens in a… *(truncated)* | **never mentioned** — maps to the five `tokenCount(for:)` overloads |
| `serve` | Start a Chat Completions API server | already verified by an Apple member's written statement; S1 corroborates the spelling |

Note how cleanly the four undocumented ones mirror the Swift API surface the guides already
document. That is corroborating structure, not proof.

> 🔴 **Still open after this harvest:** the *ordering* suggests the list is alphabetical and
> therefore complete at seven, but S1's paste is cut mid-line on `token-count`, so a subcommand
> sorting after `token-count` (e.g. `transcript`, `version`) cannot be excluded. Get the full
> paste, or run it.

## 3. Attested flags

From S2 (full-text mirror) and S3 (independent, Japanese), the demonstrated grammar is:

```bash
# one-shot
fm respond "prompt text"
fm respond "prompt" --schema schema.json
fm respond "prompt" --model pcc
fm respond "prompt" --image screenshot.png --model pcc

# S3's fuller multimodal + structured example
fm respond "このスクリーンショットで使われているアプリは？" \
  --model pcc --image Screenshot.png

# schema construction — the guide's "biggest hole" (line ~3436)
fm schema object --name AppsIdentified --string app_names --array > schema.json
fm schema object --name ActionItems   --string items      --array > schema.json

# then feed it back
fm respond "この画像で使われているアプリを列挙して" \
  --image Screenshot.png --model pcc --schema schema.json

# interactive
fm chat
```

Resolving the guide's option table (lines 257–261) — **all five were 🔴 UNKNOWN spellings**:

| Guide's narrated option | Attested spelling | Attested value | Source |
|---|---|---|---|
| "the **model** option" | `--model` | **`pcc`** selects Private Cloud Compute | S2, S3 |
| "the **image** option" | `--image` | a file path; S2 says repeatable is *not* shown for `fm` (that is `fmx`) | S2, S3 |
| "the **schema** option" | `--schema` | a path to a JSON file produced by `fm schema object` | S2, S3 |
| "the **help** option" | `--help` | — | S1 |
| "(instructions)" | `--instructions` | S2 lists it as existing but does not establish its grammar or value form → keep 🔴 **UNKNOWN** | S2 |

**`fm schema object` grammar** (the guide's self-declared "biggest hole"): the observed form is
a flag-per-property builder, not a DSL —
`fm schema object --name <TypeName> --<type> <propertyName> [--array]`. Two independent one-property
examples place `--array` after the property; that **suggests**, but does not prove, that it modifies
the immediately preceding property because neither source shows multiple properties. Only
`--string` is attested; `--int/--float/--bool` are *presumed* by symmetry and are **not** attested —
mark both inferences 🟡.

## 4. ⚠️ Direct source conflict — does `fm serve` exist?

- **S1 says yes**, in a pasted `--help` from a named build: `serve   Start a Chat Completions API server`.
- **S5 says no**, and prints a correction notice: *"some WWDC coverage (including an earlier
  draft of this article) described an `fm serve` subcommand … That claim does not appear in
  Apple's own WWDC26 session"*, adding that `fm-proxy` / `apple-to-openai` are community
  wrappers filling the gap.

**Adjudication.** S5's argument is an argument from *absence in the session transcript* — which
is exactly the reasoning the house style forbids ("absence from a beta SDK = not present in the
… interface, never does not exist"). S1 offers a positive artifact from a build number. S5 is
also self-admittedly a corrected post, i.e. it has already been wrong once on this exact point.

**Recommended guide treatment:** treat `serve` and its Chat Completions endpoint as **verified** by
the Apple member's written statement, with S1's shipped-help paste on macOS 27.0 `26A5378n` as
independent spelling corroboration. Keep the guide's existing 🔴 box for *port, bind address,
authentication, supported fields, streaming, and quota behavior*, since no source attests those.

## 5. ⚠️ `fmx` is a look-alike, not evidence

`manjunathshiva/fmx` (S6) is a **third-party macOS 26 CLI** that deliberately imitates the
not-yet-shipped `fm`, and its README says it "will eventually defer to the native `fm` command
coming in macOS 27". Its slash commands (`/help`, `/save <path>`, `/load <path>`, `/clear`,
`/system <text>`, `/model`, `/exit`) and flags (`-i`, `--stream`, `--image` repeatable, `-t`,
`--max-tokens`) are **its own design**. The README explicitly does **not** document Apple's
grammar.

This is a live contamination risk for the guide: `/save` and `/model` appear in **both** `fmx`
and in S4's description of real `fm` chat, so a careless reader will treat the whole `fmx`
slash-command set as attested `fm` surface. It is not.

**Attested `fm chat` slash commands: `/model` (switch to PCC) and `/save` (persist a session to
resume later) — S4 only, derived from session-334 narration, so still 🟡.** `/help`, `/load`,
`/clear`, `/system`, `/exit` remain 🔴 for `fm`.

## 6. Python SDK

- S3: `pip install apple_fm_sdk` — an attested *package name* (the guide's PyPI-wheel gap at
  line ~905 asks whether PyPI serves it at all; a working `pip install` on a beta OS is
  suggestive but not proof of a prebuilt wheel vs. a source build).
- S5, citing `apple.github.io/python-apple-fm-sdk` (published 2026-06-10): streaming,
  tool calling via an `fm.Tool` base class, guided generation via an **`@fm.generable`
  decorator**, and classes `SystemLanguageModel()`, `LanguageModelSession()`, with
  `GenerationError` variants `exceededContextWindowSize`, `guardrailViolation`,
  `assetsUnavailable`. Cross-check against the already-cloned `repos/apple__python-apple-fm-sdk`
  before citing — the local clone outranks S5.

---

## What to do with this file

1. **Do not** flip any 🔴 to ✅. Add a 🟠 Suggestive tier entry (the taxonomy already documents
   🟠 as of PR #8) with the S1/S2/S3 citations.
2. The four unknown subcommands (`available`, `quota-usage`, `token-count`, and the disputed
   `serve`) are the highest-value addition — the guide currently tells readers the list is
   unknowable.
3. Re-run `notes/NEEDED-FROM-A-MACOS-27-MACHINE.md` item 1 unchanged: it is still the only thing
   that settles §2's truncation, §3's `--instructions`, §4's `serve`, and every exit code.
