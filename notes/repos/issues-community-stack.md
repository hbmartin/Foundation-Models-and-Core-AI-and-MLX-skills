# Community & SDK repo issue/PR mining — Apple 2026 AI stack

**Research date:** 2026-07-27
**Method:** `gh` CLI against GitHub. Every fact below was read this session from an issue body,
issue comment, PR body, PR diff, commit message, release note, or a file fetched via
`gh api repos/<owner>/<repo>/contents/<path>`. Nothing here is from model memory.
Anything I could not verify is explicitly marked **UNVERIFIED**.

Repos in scope:

| Repo | Created | Stars | License | Issues? | PRs? |
|---|---|---|---|---|---|
| `apple/python-apple-fm-sdk` | 2026-02-25 | 1,200 | Apache-2.0 | open (17) | open (18) |
| `apple/dnikit` | 2023-04-29 | 79 | Apache-2.0 | open (3) | open (4) |
| `1amageek/swift-lm` | 2026-03-08 | 9 | none declared | 1 issue | 0 PRs |
| `noemaai-labs/noema-ios` | 2025-09-08 | 27 | MIT | 13 | 14 |
| `lucasnewman/mlx2coreai` | 2026-06-08 | 3 | MIT | **0 issues, 0 PRs** | — |
| `john-rocky/coreai-model-zoo` | 2026-06-10 | 362 | "Other" | 5 | 10 |
| `john-rocky/coreai-models` | 2026-06-13 | 2 | BSD-3 | **issues disabled** | — |

> `gh issue list -R john-rocky/coreai-models` → `the 'john-rocky/coreai-models' repository has
> disabled issues`. Everything about that repo below comes from its README and commit messages.

---

# PART 1 — `apple/python-apple-fm-sdk`

The single most valuable repo in this set. Apple ships this as **Python bindings over the Swift
Foundation Models framework** through a Swift→C shim (`foundation-models-c/`) loaded by `ctypes`.

## 1.1 Repo shape (verified via `gh api .../git/trees/main?recursive=1`)

```
build_backend.py                                   # custom PEP 517 backend: runs `swift build`
foundation-models-c/Package.swift
foundation-models-c/Sources/FoundationModelsCBindings/FoundationModelsCBindings.swift
foundation-models-c/Sources/FoundationModelsCBindings/include/FoundationModels.h
foundation-models-c/Sources/FoundationModelsCDeclarations/FoundationModelsCDeclarations.c
foundation-models-c/Sources/fm-c-example/main.c
foundation-models-c/Tests/FoundationModelsCBindingsTests/BasicSystemModelTests.swift
src/apple_fm_sdk/{__init__,c_helpers,core,errors,generable,generable_utils,
                  generation_guide,generation_options,generation_property,generation_schema,
                  prompt,session,tool,transcript,type_conversion}.py
docs/source/api/{attachment,errors,generable,generation_options,session,systemmodel,tools,transcript}.rst
docs/source/{basic_usage,evaluation,getting_started,guided_generation,index,streaming,tools}.rst
examples/{simple_inference,streaming_example,transcript_processing}.py
tests/…  (test_token_count.py, test_image_prompts.py, test_memory_stress.py, test_composed_prompt_cleanup.py, …)
tests/tester_schemas/{age,cat,hedgehog,newsletter,person,petClub,shelter}.json
tests/tester_schemas/schemas.swift            # Swift-side schema fixtures cross-checked against Python
```

Note `docs/source/evaluation.rst` exists — the SDK is explicitly positioned as an **evaluation /
batch-inference harness for Swift FM app features**, not as a production runtime.

## 1.2 Release timeline (from `gh release list` + `gh release view`)

| Tag | Published | Verbatim note |
|---|---|---|
| `v0.1.0-beta.1` | 2026-02-25 | "Introducing Python bindings for access to the on-device model at the core of Apple Intelligence through the Foundation Models framework." (pre-release) |
| `v0.1.0` | 2026-03-08 | "…updates everything for our new pip install instructions from PyPi: `pip install apple-fm-sdk`." |
| `v0.1.1` | 2026-03-08 | "adds support for GenerationOptions and makes it possible to load a Transcript from a dictionary and start a LanguageModelSession from a prior Transcript. Also adds some improvements to the `@fm.generable` decorator" |
| `v0.2.0` | 2026-06-08 | "**This update for WWDC 2026** adds the new Attachment API from the Foundation Models Swift framework to the Python SDK, so you can now include images along with text in your prompts." |
| `v0.2.1` | 2026-06-29 | "- The SDK now shows a more specific error when image inputs are not supported.<br>- `SystemLanguageModel` now exposes ways to retrieve the context size of the model, and the token count for a given input." |

Commit log (`gh api repos/apple/python-apple-fm-sdk/commits`) — the whole repo is 10 commits:

```
2026-07-07  e868e608  Release composed_prompt pointer in all respond() paths (#18)
2026-06-26  84841bb7  Bump version to 0.2.1
2026-06-22  db7afde2  Add SystemLanguageModel context size and token count (#15)
2026-06-22  da32e982  Clarify the error for image inputs being unsupported (#14)
2026-06-08  3ff9c600  Images in prompts
2026-03-08  8d56a2d9  Make @generable decorator more flexible (#10)
2026-03-08  0f65c9b0  Adding generation options (#9)
2026-03-08  6b6f8338  Adding the ability to load a session from a saved transcript (#8)
2026-03-08  e9a40a51  Updating README.md (#7)
2026-02-25  3204b7ee  Hello apple-fm-sdk
```

**Gotcha:** `src/apple_fm_sdk/__init__.py` still declares `__version__ = "0.1.0"` even at
`v0.2.1`. Don't trust `apple_fm_sdk.__version__`; check the PyPI/dist metadata instead.

## 1.3 THE BIG ONE — issue #13: no Private Cloud Compute in Python. `fm` CLI instead.

**`apple/python-apple-fm-sdk#13` — "Plans for Server models?" — CLOSED (2026-07-12), opened by
@Cactys12 2026-06-09.**

Core problem: user asks whether Private Cloud Compute (server) models will be added to the
Python SDK "to pull the most recent data from the internet… a large step up in quality of output,
and a lowering in the number of hallucinations."

Resolution — **@rxwei (MEMBER, i.e. Apple)**, verbatim:

> "Hi @Cactys12, we do not currently plan to add support for Private Cloud Compute in this
> Python SDK. You can access Private Cloud Compute via the `fm` CLI in macOS Golden Gate, and
> `fm serve` lets you serve it easily as a Chat Completions endpoint."

Follow-up from the reporter (unanswered by Apple in-thread):

> "Does this mean I could just go
> `ai_response = subprocess.check_output(["fm", "respond", query, "--model", "pcc"], text=True)`
> to ask a question to the PCC?"

**Takeaways for a guide:**
- **"macOS Golden Gate"** is Apple's codename for the macOS release that ships the `fm` CLI.
  (Referenced by an Apple member; a guide should cross-reference the actual macOS 27 naming.)
- There is an **`fm` command-line tool** with (at least) a `respond` subcommand and an
  **`fm serve`** subcommand that exposes an **OpenAI Chat-Completions-compatible endpoint**.
- **PCC is CLI-only from Python.** If a Python program needs PCC, the sanctioned path is
  shelling out to `fm` or hitting `fm serve` over HTTP — not `apple_fm_sdk`.
- The `--model pcc` flag in the follow-up is the *reporter's guess*, **UNVERIFIED**.

## 1.4 Issue #6 — `pip install` hard-fails with Command Line Tools only (STILL OPEN)

**`apple/python-apple-fm-sdk#6` — "Build fails with Command Line Tools only — Xcode.app should
not be required" — OPEN since 2026-03-07, @siva-acv.**

Environment: macOS 26.3 (Tahoe), M3 Max, Swift 6.2.3 from CLT, `xcode-select -p` →
`/Library/Developer/CommandLineTools`, Xcode.app not installed.

Exact error text:

```
SwiftToolingError: The active developer directory is set to Command Line Tools
(/Library/Developer/CommandLineTools), but a full Xcode installation is required.
Please install Xcode. Then open Xcode at least once to accept the license agreement
and install the Swift SDKs.
```

I confirmed the root cause by reading `build_backend.py` at `main` today. `_build_c_bindings()`
does, in order:

1. `platform.mac_ver()` — rejects `< 26.0`:
   `"macOS version {macos_version} found, but version 26.0 or higher is required."`
2. `shutil.which("swift")` — rejects if absent.
3. `xcode-select -p` — **raises if the path contains `"CommandLineTools"`**.
4. `shutil.which("xcodebuild")` — rejects if absent.
5. `xcodebuild -version`, regex `r"Xcode\s+(\d+)\.(\d+)"`, rejects `major_version < 26`.
6. `xcrun --sdk macosx --show-sdk-version` → `_macos_sdk_major_version()`.
7. **If SDK major ≥ 27, adds `-Xswiftc -DFM_HAS_MACOS_27_SDK`** — this is the image/Attachment
   feature gate.
8. `subprocess.run(["swift", "build", "-c", swift_build_config, *extra_swift_args], …)` where
   `DEFAULT_SWIFT_BUILD_CONFIGURATION = "release"`.

Verbatim from `build_backend.py`:

```python
    # `Attachment` (image support) only exists in the macOS 27+ SDK
    extra_swift_args = []
    sdk_major = _macos_sdk_major_version()
    if sdk_major is not None and sdk_major >= 27:
        extra_swift_args += ["-Xswiftc", "-DFM_HAS_MACOS_27_SDK"]
```

The reporter's point stands: **the actual compile is `swift build`, never `xcodebuild`.** Their
proposed patch replaces the Xcode checks with a `swift --version` parse requiring `>= 6.2`
("Swift 6.2+ ships with the macOS 26 SDK, which is the real requirement"). They verified the
workaround works end-to-end: "After this change, `pip install -e .` completes successfully and
the SDK works correctly (text generation, streaming, guided generation, tool calling all
verified)."

Second commenter (@Neko-Design):

> "This would also be much appreciated for other lower-powered devices where having Xcode
> installed is either unlikely or unnecessary… Perhaps even distributing a pre-compiled binary
> version like psycopg if appropriate."

**Takeaways:**
- **As of 2026-07-27 this is still OPEN.** `pip install apple-fm-sdk` builds from source and
  requires **full Xcode.app**, not CLT. There is no wheel; every install compiles Swift.
- CI images with only CLT will fail. Fix: install Xcode and
  `sudo xcode-select --switch /Applications/Xcode.app/Contents/Developer`, then open Xcode once.
- The Xcode SDK major version **silently changes the feature set**: images/Attachments compile
  in only when the *build machine's* macOS SDK is ≥ 27.

## 1.5 Issue #16 — a real typo in that same error message (STILL OPEN)

`apple/python-apple-fm-sdk#16` (2026-06-30, @martin0258). `build_backend.py:99-100` emits
`"…open Xcodeat least once…"` (missing space, from Python implicit string concatenation).
Still present in `main` today — I re-read the file and confirmed:

```python
                "but a full Xcode installation is required. Please install Xcode. Then open Xcode"
                "at least once to accept the license agreement and install the Swift SDKs."
```

Cosmetic, but useful as a **fingerprint**: if you see `Xcodeat` in a stack trace, you're on
`apple-fm-sdk` ≤ 0.2.1's build backend.

## 1.6 Issue #17 / PR #18 — native pointer + file-descriptor leak (the deepest bug report here)

**`#17` (2026-07-03, @dmkharlamov) → fixed by `#18` (merged 2026-07-07, @li3zhen1).**

Core problem: `LanguageModelSession._respond_with_schema_from_json()` (and, per the fix, also
`_respond_basic` and `_respond_with_schema`) called
`self._composed_prompt_from_prompt(prompt)` → `lib.FMComposedPromptInitialize()` but its
`finally:` block only did `lib.FMRelease(task)`. The `FMComposedPrompt` native pointer leaked
per call, and because it retains the `ImageAttachment`, **the image's file descriptor leaked with
it**.

Reporter's measured failure mode, verbatim:

> "Under macOS, even though the soft file descriptor limit can be high (e.g., `1,048,575`),
> sequential predictions consistently fail after exactly **240-250 sequential calls with image
> attachments**. The system starts throwing a fatal **`OSError: [Errno 9] Bad file descriptor`**
> on any subsequent file system opens (including standard Python `open()`, `PIL.Image.open()`,
> or system plist reads)."

Two independent leak channels, both must be plugged:

1. the un-released native `FMComposedPrompt`;
2. **"The native `LanguageModelSession` transcript history automatically retains previous prompts
   and attachments. Therefore, in a single persistent session run, previous attachment file
   descriptors are kept open throughout the session's lifetime."**

And a **hard footgun** the reporter documented:

> "attempting to clear these channels by manually forcing the release of the native session
> resources (by calling the internal `session._release()` method in a loop) leads to duplicate
> deallocation and double-free crashes (`EXC_BREAKPOINT / SIGTRAP` in `libswiftCore.dylib`)
> because Python's garbage collector automatically runs the session destructor `__del__` which
> tries to release the raw `_ptr` again."

Their 4-mode reproducer showed only `--patched-recreate` (fix **plus** a fresh session per
iteration) held FDs flat at 7; every other mode grew 7 → 17 over 10 iterations.

The named background daemon in the report: **`/usr/libexec/macOSFoundationModels`** (the XPC
service the Python process talks to). The reporter's three candidate explanations for the ~250
ceiling (launchd/sandbox concurrent-XPC cap of 256, `CFRunLoop` CFSocket registration cap of 256,
internal `select()` worker arrays of 256 slots) are **speculation by the reporter, UNVERIFIED**;
Apple never answered in-thread.

PR #18 (merged) body, verbatim:

> "- `_respond_with_schema_from_json` already released it; extend the same fix to `_respond_basic`
>   and `_respond_with_schema`, which leaked one native `FMComposedPrompt` (and any retained image
>   file descriptors) per call.
> - Add regression tests covering success/error/cancellation paths for all three methods via
>   mocked native bindings, plus an end-to-end file-descriptor leak check with image attachments."

Files: `src/apple_fm_sdk/session.py (+21/-0)`, `tests/test_composed_prompt_cleanup.py (+236/-0)`.

**Takeaways:**
- Fixed in `main` (commit `e868e608`, 2026-07-07) but **not in any tagged release** —
  `v0.2.1` (2026-06-29) predates it. **If you `pip install apple-fm-sdk` today you get the leak.**
  Install from git `main` for batch image workloads.
- **Never call `session._release()` manually** — double-free / SIGTRAP.
- Even with the fix, **recreate the session periodically** in image batch loops; the native
  transcript retains attachments for the session's lifetime.

## 1.7 Issue #11 / PR #15 — token counting & context size (needs macOS **26.4**)

`#11` (2026-05-06, @Korolev-Oleg) asked for precise prompt token counting to avoid
`exceeds the model's context window`. @li3zhen1 (contributor): *"`token_count` has been
implemented in …/pull/15."*

From the **PR #15 diff** (exact, verified):

C header additions (`foundation-models-c/.../include/FoundationModels.h`):

```c
typedef void (*_Nonnull FMSystemLanguageModelTokenCountCallback)(int status, int tokenCount, const char *_Nullable errorDescription, void *_Nullable userInfo) __attribute__((swift_attr("@Sendable")));

// Returns the model's maximum context window size, measured in tokens.
int FMSystemLanguageModelGetContextSize(FMSystemLanguageModelRef _Nonnull model);

// Token counting. Each function dispatches asynchronously and reports the count (or an error)
// via the callback. The returned FMTaskRef can be cancelled with FMTaskCancel and must be
// released with FMRelease.
FMTaskRef FMSystemLanguageModelTokenCountForPrompt(FMSystemLanguageModelRef _Nonnull model, FMComposedPrompt _Nonnull composedPrompt, void *_Nullable userInfo, FMSystemLanguageModelTokenCountCallback callback);
FMTaskRef FMSystemLanguageModelTokenCountForInstructions(FMSystemLanguageModelRef _Nonnull model, const char *_Nonnull instructions, void *_Nullable userInfo, FMSystemLanguageModelTokenCountCallback callback);
FMTaskRef FMSystemLanguageModelTokenCountForTools(FMSystemLanguageModelRef _Nonnull model, FMBridgedToolRef _Nullable *_Nullable tools, int toolCount, void *_Nullable userInfo, FMSystemLanguageModelTokenCountCallback callback);
FMTaskRef FMSystemLanguageModelTokenCountForSchema(FMSystemLanguageModelRef _Nonnull model, FMGenerationSchemaRef _Nonnull schema, void *_Nullable userInfo, FMSystemLanguageModelTokenCountCallback callback);
FMTaskRef FMSystemLanguageModelTokenCountForTranscript(FMSystemLanguageModelRef _Nonnull model, FMLanguageModelSessionRef _Nonnull transcriptSession, void *_Nullable userInfo, FMSystemLanguageModelTokenCountCallback callback);
```

**The OS gate, verbatim from the Swift shim:**

```swift
/// Error thrown when a token-counting API is invoked on an OS older than the version that
/// introduced it (26.4).
private func tokenCountUnsupportedOSError() -> Error {
  NSError(
    domain: "TokenCount",
    code: -1,
    userInfo: [
      NSLocalizedDescriptionKey: "Token counting requires macOS 26.4, iOS 26.4, or visionOS 26.4 or later."
    ]
  )
}
```

Every token-count binding is wrapped in
`guard #available(macOS 26.4, iOS 26.4, visionOS 26.4, *) else { throw tokenCountUnsupportedOSError() }`.

The underlying Swift FM APIs being bridged (from the shim's call sites) are:
`model.contextSize`, `model.tokenCount(for: prompt)`, `model.tokenCount(for: instructions)`,
`model.tokenCount(for: [any Tool])`, `model.tokenCount(for: schema)`,
`model.tokenCount(for: transcript)` on `SystemLanguageModel`.

Python surface added in `src/apple_fm_sdk/core.py` (exact signature from the diff):

```python
    @property
    def context_size(self) -> int:
        """The model's maximum context window size, measured in tokens."""
        return int(lib.FMSystemLanguageModelGetContextSize(self._ptr))

    async def token_count(
        self,
        value: "Optional[Union[Prompt, GenerationSchema, Transcript, list[Tool]]]" = None,
        *,
        instructions: Optional[str] = None,
    ) -> int:
```

Docstring examples (verbatim from the diff):

```python
model = fm.SystemLanguageModel()
budget = model.context_size
used = await model.token_count("Tell me about the history of Swift.")
print(f"Using {used} of {budget} tokens")

count = await model.token_count("Hello, world!")
count = await model.token_count(instructions="You are a helpful assistant.")
count = await model.token_count([CalculatorTool(), WeatherTool()])
count = await model.token_count(Cat.generation_schema())
count = await model.token_count(session.transcript)
```

Dispatch rules implemented in `token_count` (read from the diff):
- `instructions=` and positional `value` are **mutually exclusive** →
  `ValueError("Provide either a value or instructions to token_count(), not both")`
- neither → `ValueError("token_count() requires either a value or instructions")`
- `isinstance(value, GenerationSchema)` → schema path
- `isinstance(value, Transcript)` → uses `value.session_ptr`
- `isinstance(value, list) and all(isinstance(t, Tool) …)` → tools path
- **else** treated as a prompt (str or list of components) via `_composed_prompt_from_prompt`

Tests asserted (from `tests/test_token_count.py` in the diff): `context_size >= 1`; token counts
deterministic for the same prompt; longer prompt ⇒ strictly larger count; list-of-strings prompts
work; unicode/emoji produce tokens.

Also in PR #15: `_composed_prompt_from_prompt` was **moved out of `LanguageModelSession` into
module scope in `prompt.py`** so the model can build prompts without a session. Error text for
bad components, verbatim:

```python
raise PromptError(
    f"Unsupported prompt component type {type(component)}, only str, Image, IdentifiedImage, and Attachment are supported"
)
```

**Takeaways:** `context_size` is a **sync property**; `token_count` is **async** and needs
**macOS/iOS/visionOS 26.4+** at *runtime*. On older OSes you get an `NSError` in domain
`"TokenCount"` surfaced through the SDK's error mapping.

## 1.8 PR #14 — image inputs: two distinct "unsupported" errors

Merged 2026-06-22 (@egourlao). Splits `ComposedPromptError.unsupported` into
`.unsupportedSDK` and `.unsupportedOS`, with matching C enum:

```c
typedef enum {
    FMComposedPromptAddImageErrorNone,
    FMComposedPromptAddImageErrorUnsupportedOS,
    FMComposedPromptAddImageErrorUnsupportedSDK,
    FMComposedPromptAddImageErrorUnknown
} FMComposedPromptAddImageError;
```

Swift comments, verbatim:

```swift
enum ComposedPromptError: Error {
  // Error thrown when the SDK, at build time, does not support attachments
  case unsupportedSDK
  // Error thrown when the runtime OS does not support attachments
  case unsupportedOS
}
```

Python messages you will actually see (`src/apple_fm_sdk/prompt.py`):

```python
if error_reason.value == FMComposedPromptAddImageErrorUnsupportedOS:
    detail = "the current OS does not support attachment prompts"
elif error_reason.value == FMComposedPromptAddImageErrorUnsupportedSDK:
    detail = "the Xcode version used to build this package doesn't include macOS 27 SDKs"
else:
    detail = "an unknown error occurred while adding the attachment"
raise ImagePromptError(f"Failed to add attachment to prompt: {detail}")
```

**Takeaway:** image prompts require **both** a macOS-27-SDK Xcode *at pip-install time* (the
`-DFM_HAS_MACOS_27_SDK` flag) **and** a macOS 27 host at *runtime*. The two failure modes are now
distinguishable by message text — that string is your diagnostic.

## 1.9 Issue #4 / PR #10 — `@fm.generable` pitfalls (three of them)

`#4` (2026-03-01, @Seraphim0916), env: macOS 26.4, M4 Max, Python 3.10.19, SDK commit `3204b7e`.

What **failed** (verbatim):

```python
@fm.generable
@dataclass
class Fruit:
    name: str
    color: str
    price: float

result = await session.respond("List a fruit", response_type=Fruit)
# Error: "decorator is not a Generable type"
```

What **worked**:

```python
@fm.generable("A fruit")
class Fruit:
    name: str
    color: str
    price: float

result = await session.respond("List a fruit", generating=Fruit)
# Works: Name: Apple, Color: red, Price: 1.5 (1.06s)
```

The reporter's three "non-obvious behaviors", verbatim:

> "1. `@generable()` is a factory, not a direct decorator — parentheses with description string required
>  2. `@dataclass` must NOT be applied — `generable()` internally applies it
>  3. Response parameter is `generating=`, not `response_type=`"

**Resolution — PR #10 (merged 2026-03-08, @mkery), verbatim:**

> "adding overload aliases to the `@fm.generable()` decorator so that it can be used with or
> without parentheses, and throws more helpful error messages in failure modes. This update also
> fixes the issue where the decorator would fail if `@dataclass` was also explicitly added."

Post-fix, the current README shows the bare form works:

```python
@fm.generable # This decorator signals this type be generated by a model
class Cat:
    name: str
    age:int = fm.guide("Age in years", range=(0, 20))

cat = await session.respond("Generate an adorable rescue cat", generating=Cat)
```

**Still true after the fix:** the keyword is **`generating=`**, never `response_type=`. Only
pitfalls 1 and 2 were fixed.

## 1.10 Issue #3 / PR #9 — tool calling was already there; `GenerationOptions` was the gap

`#3` (2026-02-27, @ZPVIP) asked (a) how to set output limits, (b) whether tool calling is planned,
(c) how to map to an OpenAI-compatible adapter (their project: `ZPVIP/apple-to-openai`).

@mkery's PR #9 body, verbatim:

> "1. **Tool calling support:** we already support tool calling so there's no additional work to
>    do at the moment
>  2. **Support generation limits like max-token:** this is best served by porting the existing
>    GenerationOptions Swift framework type into Python, since GenerationOptions contains a
>    `maximumResponseTokens` option."

Community answer from @DanieleMorotti in the same thread — a **complete working tool-calling
example** (verbatim, and it documents the exact `fm.Tool` contract):

```python
@fm.generable("Calculator parameters")
class CalculatorParams:
    operation: str = fm.guide("The operation to perform, one between '+', '-', '*' and '/'.")
    a: float = fm.guide("First number")
    b: float = fm.guide("Second number")

class CalculatorTool(fm.Tool):
    name = "calculator"
    description = "Performs basic arithmetic operations"

    @property
    def arguments_schema(self) -> fm.GenerationSchema:
        return CalculatorParams.generation_schema()

    async def call(self, args: fm.GeneratedContent) -> str:
        op = args.value(str, for_property="operation")
        a = args.value(float, for_property="a")
        b = args.value(float, for_property="b")
        ...
        return str(result)

session = fm.LanguageModelSession(
    instructions="You are a helpful assistant for math homeworks.",
    tools=[CalculatorTool()]
)
```

Transcript inspection (also verbatim from that comment) — the **JSON shape of the transcript**:

```python
transcript = await session.transcript.to_dict()
entries = transcript.get("transcript", {}).get("entries", [])
for entry in entries:
    role = entry.get("role")
    if role == "response" and entry.get("toolCalls"):
        for tc in entry["toolCalls"]:
            print(tc.get("name"), tc.get("id"), tc.get("arguments"))
    if role == "tool":
        contents = entry.get("contents", [])
        text_outputs = [c.get("text") for c in contents if c.get("type") == "text"]
        print(entry.get("toolName"), entry.get("toolCallID"), text_outputs)
```

So: transcript JSON = `{"transcript": {"entries": [...]}}`; entries have `role` ∈
{`"response"`, `"tool"`, …}; response entries can carry `toolCalls[]` with
`name`/`id`/`arguments`; tool entries carry `toolName`, `toolCallID`, `contents[]` with
`{"type": "text", "text": …}`.

**Two limitations recorded by that commenter (still relevant):**

> "Currently, it doesn't seem possible to manually handle the tool calls."

and — a **doc bug** — `session.py`'s docstring shows:

```python
model = fm.SystemLanguageModel(
    temperature=0.7,
    top_p=0.9
)
```

> "but it's not possible to pass them."

I confirmed against `generation_options.py`: `temperature`/sampling live on **`GenerationOptions`**,
not on `SystemLanguageModel`. **UNVERIFIED whether that docstring has since been corrected.**

## 1.11 `GenerationOptions` — exact API (from PR #9 diff, `src/apple_fm_sdk/generation_options.py`)

```python
class SamplingModeType(str, Enum):
    GREEDY = "greedy"
    RANDOM = "random"

@dataclass
class SamplingMode:
    mode_type: SamplingModeType
    top: Optional[int] = None
    probability_threshold: Optional[float] = None
    seed: Optional[int] = None

    @classmethod
    def greedy(cls) -> "SamplingMode": ...
    @classmethod
    def random(cls, top: Optional[int] = None,
               probability_threshold: Optional[float] = None,
               seed: Optional[int] = None) -> "SamplingMode": ...

@dataclass
class GenerationOptions:
    sampling: Optional[SamplingMode] = None
    temperature: Optional[float] = None
    maximum_response_tokens: Optional[int] = None
```

Validation rules (all raise `ValueError`, from `__post_init__` / `random()`):
- `top` and `probability_threshold` are mutually exclusive:
  `"Cannot specify both 'top' and 'probability_threshold'. Choose one sampling constraint."`
- `'top' must be a positive integer`
- `'probability_threshold' must be between 0.0 and 1.0`
- `'seed' must be an integer`
- `'temperature' must be a number` / `'temperature' must be non-negative`
- `'maximum_response_tokens' must be an integer` / `must be positive`
- `'sampling' must be a SamplingMode instance`

Wire format (`to_dict()`) — note the **string-typed** sampling sub-values and the
`top` → `top_k`, `probability_threshold` → `top_p` renaming:

```python
# {'temperature': 0.7, 'sampling': {'mode': 'random', 'top_k': 50}, 'maximum_response_tokens': 500}
sampling_dict["top_k"] = str(self.sampling.top)
sampling_dict["top_p"] = str(self.sampling.probability_threshold)
sampling_dict["seed"] = str(self.sampling.seed)
```

Apple's own warnings in the class docstring, verbatim:

> "- Only use `maximum_response_tokens` when you need to protect against unexpectedly verbose
>   responses. Enforcing a strict token response limit can lead to the model producing malformed
>   results or grammatically incorrect responses.
> - All input to the model contributes tokens to the context window, including the Instructions,
>   Prompt, Tool definitions, and Generable types, as well as the model's responses. If your
>   session exceeds the available context size, it throws an ExceededContextWindowSizeError."

## 1.12 Issue #1 / PR #8 — session-from-transcript (requested by Simon Willison)

`#1` (2026-02-26, @simonw): wanted it for the `llm` CLI's `llm -c` "continue conversation" flow
backed by SQLite. He quoted the Swift original:

```swift
let transcript = Transcript(entries: entries)
var session = LanguageModelSession(transcript: transcript)
session.prewarm()
```

@mkery's answer + the shipped Python API, verbatim:

```python
import apple_fm_sdk as fm
import json

with open("transcript.json", "r") as f:
    transcript_dict = json.load(f)

transcript = await fm.Transcript.from_dict(transcript_dict)
session = fm.LanguageModelSession.from_transcript(transcript)
response = await session.respond("Summarize the session so far.")
```

Note **`Transcript.from_dict` is `async`** (it round-trips through the Swift deserializer) while
**`LanguageModelSession.from_transcript` is sync**. PR #8 body:

> "Load transcript from a dictionary to create a `Transcript` object. This assumes the dictionary
> matches the `Transcript` JSON format defined in the Swift framework, and uses the Swift
> framework to de-serialize the JSON into a `Transcript` object."

New C entry point from that PR:
`FMLanguageModelSessionCreateFromTranscript(FMLanguageModelSessionRef transcriptSession, FMSystemLanguageModelRef model, FMBridgedToolRef **tools, int toolCount)`.

**Implementation detail worth knowing:** a Python `Transcript` is backed by a *session pointer*
(`value.session_ptr` is used by the token-count path). Transcripts are not standalone objects.

## 1.13 Issue #2 — the README was wrong at launch (async)

`#2` (2026-02-26, @SaqibAMA): the shipped README example didn't `await`/`asyncio.run`. Two
community members posted the fix; @mkery merged PR #7. Current README is correct. The
**everything-is-async** rule is the #1 thing new users trip on:

```python
import apple_fm_sdk as fm
import asyncio

async def main():
    model = fm.SystemLanguageModel()
    is_available, reason = model.is_available()
    if is_available:
        session = fm.LanguageModelSession()
        response = await session.respond("Hello, how are you?")
        print(f"Model response: {response}")
    else:
        print(f"Foundation Models not available: {reason}")

asyncio.run(main())
```

PR #7 also fixed the dev install: removing the pinned setuptools version from `pyproject.toml`'s
build section made **`uv sync` alone** build the Swift/C backend (previously you also needed
`uv pip install -e .`). Verbatim: *"It turns out `uv sync` was not correctly building our Swift-C
backend, which is why we needed the `uv pip install -e .` previously."*

Note the README's *Development Installation* section **still** lists step 4 as
`uv pip install -e .` + `pytest` after each change.

## 1.14 Issue #5 — `LanguageModelFeedback` / `logFeedbackAttachment` NOT exposed (OPEN)

`#5` (2026-03-03, @andrewgleave), still OPEN. Verbatim:

> "I have a suite of test cases running against FM, many of which are triggering erroneous
> guardrail violations even when configured with `PERMISSIVE_CONTENT_TRANSFORMATIONS`. I'd like
> to submit these to help improve the models, but not having a Python API I can call from the
> notebook means I probably won't, and if I cannot find a workaround, I will need to switch to
> using MLX and a different model."

**Takeaways:**
- `PERMISSIVE_CONTENT_TRANSFORMATIONS` is a real guardrails setting reachable from the Python SDK
  (it maps to `SystemLanguageModelGuardrails`, which `__init__.py` exports) — and a real user
  reports it **still trips false guardrail violations**.
- **Feedback submission (`LanguageModelFeedback`, `logFeedbackAttachment`) is Swift-only.** No
  Python path as of 2026-07-27.

## 1.15 Complete Python public API surface (from `src/apple_fm_sdk/__init__.py`, read today)

```
core:               SystemLanguageModel, SystemLanguageModelUseCase,
                    SystemLanguageModelGuardrails, SystemLanguageModelUnavailableReason
session:            LanguageModelSession
prompt:             ImageAttachment, Attachment, PromptComponent, Prompt,
                    PromptError, ImagePromptError
transcript:         Transcript
errors:             FoundationModelsError, GenerationError, ExceededContextWindowSizeError,
                    AssetsUnavailableError, GuardrailViolationError, UnsupportedGuideError,
                    UnsupportedLanguageOrLocaleError, DecodingFailureError, RateLimitedError,
                    ConcurrentRequestsError, RefusalError, ToolCallError, GenerationErrorCode,
                    InvalidGenerationSchemaError
generable:          GeneratedContent, GenerationID, ConvertibleFromGeneratedContent,
                    ConvertibleToGeneratedContent, Generable
generation_schema:  GenerationSchema
generable_utils:    generable
generation_guide:   GenerationGuide, GuideType, guide
generation_options: GenerationOptions, SamplingMode, SamplingModeType
tool:               Tool
```

### Error code table (`src/apple_fm_sdk/errors.py`, verbatim)

```python
class GenerationErrorCode(IntEnum):
    SUCCESS = 0
    EXCEEDED_CONTEXT_WINDOW_SIZE = 1
    ASSETS_UNAVAILABLE = 2
    GUARDRAIL_VIOLATION = 3
    UNSUPPORTED_GUIDE = 4
    UNSUPPORTED_LANGUAGE_OR_LOCALE = 5
    DECODING_FAILURE = 6
    RATE_LIMITED = 7
    CONCURRENT_REQUESTS = 8
    REFUSAL = 9
    INVALID_SCHEMA = 10
    UNKNOWN_ERROR = 255
```

Mapped messages (exact strings): `"Context window size exceeded"`, `"Required assets are
unavailable"`, `"Guardrail violation occurred"`, `"Unsupported guide used"`, `"Unsupported
language or locale"`, `"Failed to decode response"`, `"Request was rate limited"`, `"Too many
concurrent requests"`, `"Model refused to generate content"`, `"Invalid generation schema
provided"`. Unknown codes → `GenerationError(f"Unknown generation error (status: {status_code}): {debug_description}")`.

`RefusalError` carries an extra `explanation_entries` list.
`ToolCallError(tool_name, underlying_error)` formats as `f"Tool '{tool_name}' failed: {underlying_error}"`.

## 1.16 Python ↔ Swift gap table (what the Python bindings CAN'T do)

| Capability | Python SDK | Notes / source |
|---|---|---|
| On-device `SystemLanguageModel` inference | ✅ | README |
| Streaming | ✅ | `examples/streaming_example.py`, `tests/test_streaming.py` |
| Guided generation (`@generable`, `guide`, `GenerationSchema`) | ✅ | README, PR #10 |
| Raw JSON-Schema guided generation | ✅ | `_respond_with_schema_from_json`, `tests/test_json_guided_generation.py` |
| Tool calling | ✅ | PR #9 comment: "we already support tool calling" |
| **Manual/intercepted tool-call handling** | ❌ | issue #3 comment: "it doesn't seem possible to manually handle the tool calls" |
| `GenerationOptions` (temperature / sampling / max tokens) | ✅ (v0.1.1+) | PR #9 |
| Transcript load + resume session | ✅ (v0.1.1+) | PR #8 |
| Image / `Attachment` prompts | ✅ (v0.2.0+), **SDK 27 + OS 27 gated** | PR #14 |
| `context_size` / `token_count` | ✅ (v0.2.1+), **OS 26.4+ gated** | PR #15 |
| **Private Cloud Compute** | ❌ **"we do not currently plan to add support"** | issue #13, @rxwei |
| **`LanguageModelFeedback` / `logFeedbackAttachment`** | ❌ | issue #5 (OPEN) |
| Adapters / custom-trained adapters | not present in `__init__.py` | **UNVERIFIED** whether planned |
| `prewarm()` | not in `__all__` | **UNVERIFIED** — simonw quoted Swift `session.prewarm()`; no Python equivalent exported |

## 1.17 Contribution status

README, verbatim: **"This project is not yet taking contributions. Stay tuned!"** — yet PRs #7–#18
were merged, several from non-Apple contributors (@li3zhen1, @egourlao, @kiwigitops-style
outsiders). So the README text is stale; PRs *are* being merged.

---

# PART 2 — `john-rocky/coreai-model-zoo` (362★ — the community Core AI hub)

Description (verbatim from repo metadata):

> "Community model zoo for Apple Core AI (iOS/macOS 27): 49 models — LLM, VLM, OCR, ASR, TTS,
> image/video/music gen, forecasting — converted, verified on real devices, downloadable from
> Hugging Face, and runnable in one line of Swift via CoreAIKit. Plus conversion recipes,
> on-device benchmarks, custom Metal kernels, and a knowledge base."

## 2.1 Issue #5 + PR #6 — the first external port (Nanbeige4.2-3B). Read this one.

**`#5` "[request] Nanbeige4.2-3B"** (2026-07-22, @ukint-vs) → **PR #6 merged 2026-07-23.**
This single thread is the most information-dense Core AI porting document I found anywhere.

### The maintainer's authoritative reply (issue #5), key extracts — **quote these**

Bundle layout:

> "For layout, `Nanbeige4.1-3B-CoreAI` is the closest reference: `<runtime-family>/<bundle>/`
> containing `metadata.json`, the `.aimodel` (`main.mlirb` + `main.hash` + `metadata.json`), and
> `tokenizer/` including `chat_template.jinja` — a complete LanguageBundle the engine loads as-is."

Toolchain gate (**critical version gate**):

> "One toolchain check before uploading: the `.aimodel`'s inner `metadata.json` should carry a
> `producer` key reporting `coreai-core` ≥ 1.0.0b2 (bundles from earlier wheels are rejected by
> the Xcode 27 beta 3+ SDK loader; a missing `producer` key is the signature of a pre-b2 export)."

iOS compile acceptance — **exact CLI**:

> "Compile acceptance, runnable on your own Mac with Xcode 27 beta 3+:
> `xcrun coreai-build compile … --platform iOS --preferred-compute gpu --architecture h18p`
> exiting 0 (`h18p` = the iPhone 17 Pro class; **large decode graphs need AOT on iOS — JIT
> specialization does not survive there**)."

Device gate protocol:

> "The device gate itself: greedy token-exact numerics (nat + oracle) plus measured Release tok/s
> on hardware… it is the same protocol every zoo row went through (4.1's record: nat 24/24 ·
> oracle 24/24, decode 16.9 tok/s)."

Revision pinning:

> "At enrollment the CoreAIKit catalog pins the exact revision hash, so apps get the verified
> bytes regardless of where the repo lives."

### PR #6 body — the architecture and the numbers (verbatim extracts)

Published artifact:

```
repository:        https://huggingface.co/ukint-vs/Nanbeige4.2-3B-CoreAI
immutable revision: 5864ec7a5581940958e58354a6b6c46c8f06891e
path:              gpu-pipelined/nanbeige4_2_3b_decode_int8hu_block32_sym_s1
bundle size:       4.59 GiB
producer:          coreai-core 1.0.0b2
```

Validation list (verbatim):

> "- float32 full and cached logits: `rtol=1e-4`, `atol=1e-4`; identical 32-token greedy continuation
> - pinned official checkpoint parity: pass; config SHA-256 `f6cb15b2…`
> - int8 authoring gate: prompt top-1 8/8, greedy 32/32, cosine 0.9997768
> - int8 Core AI gate: token-exact for the factual prompts and `9.11` versus `9.8` reasoning smoke
> - quantization traversal: 111 physical linear modules, without duplicating the recurrent stack
> - M4 Max Release benchmark, prompt 128 / generation 256 / three runs: 47.37 prefill and 46.35 decode tok/s
> - 4,096-token boundary: 29.83 prefill and 32.80 decode tok/s, 9.17 GiB peak RSS, zero swaps
> - Xcode 27 GPU AOT compile for iOS 27 `h18p`: pass"

> "Int4 and mixed int4/int8 variants were evaluated but failed the same quality gates, so neither
> is exposed as a shipping option."

### The maintainer's device-gate result comment — real iPhone 17 Pro numbers

> "Engine ready in **31.7 s** cold (first-ever load, on-device GPU specialization) / **10.8 s**
> warm; free space 22.4 GB; no jetsam."

> "**NUMERICS: nat 24/24 + oracle 24/24 — device greedy tokens are IDENTICAL to the Mac engine
> reference**… So iPhone == Mac == fp32 oracle across both prompts, and it reproduced identically
> on a second full run. Cross-device determinism holds for the recurrent two-pass graph."

> "Throughput (p=128 g=256, S=1 prompt chunking, ×2 trials each; phone GPU clocks swing with
> DVFS/thermals…): first run after cold spec: STATS prefill 6.9 / decode 5.7 tok/s… settled
> rerun (300 s idle first): STATS prefill 8.5 / decode 6.4 tok/s"

> "the two-pass execution reads the 22 shared physical blocks twice per token, so per-token weight
> traffic is ~2× a single-pass model of the same bundle size. A phone GPU is bandwidth-bound,
> hence ~6 tok/s where the (single-pass, same-size) Nanbeige4.1 does ~17 — and where your M4 Max,
> with ~8× the bandwidth, does 46+."

**Takeaways for a guide:**
- **Cold Core AI specialization on iPhone for a 4.59 GiB LLM bundle: ~32 s.** Warm: ~11 s.
  Budget for this in UX.
- **iPhone GPU is bandwidth-bound.** tok/s ≈ f(bundle bytes read per token), not parameter count.
- **Determinism holds** across Mac engine ↔ iPhone ↔ fp32 oracle for greedy decode.
- `S=1` prompt chunking is the working config for these pipelined bundles.

### `conversion/recipes.toml` entry added by PR #6 (verbatim, shows the real recipe schema)

```toml
["nanbeige4.2-3b"]
script = "export_nanbeige41_decode_pipelined.py"
args = [
  "int8hu",
  "--head-sym",
  "--static-ids",
  "--hf-id",
  "Nanbeige/Nanbeige4.2-3B",
  "--revision",
  "5ff54fb7ed86ce8e216d78bff5417ab9981de3d4",
]
card = "../zoo/nanbeige4.2-3b.md"
notes = [
  "Pinned int8 baseline: 22 shared physical layers, two passes, 44 logical KV cache layers.",
  "…",
  "int4hu is a measured no-go: 3.14 GiB and 56.1 warm decode tok/s, but it fails the decisive fp32 continuation gate.",
  "Mixed int4/int8 is also a no-go: the 4.41 GiB three-layer candidate fails the decisive Core AI reasoning gate.",
]
```

Quantization mode names visible: **`int8hu`**, **`int4hu`**, **`int8lin`** (the last from the
neighbouring `holo2-4b` entry). Flags: `--head-sym`, `--static-ids`, `--hf-id`, `--revision`.

### Architecture note from `knowledge/nanbeige4.2-coreai-support.md` (added by PR #6)

```text
embedding
  → physical blocks 0…21 → norm       (cache slots 0…21)
  → physical blocks 0…21 → norm       (cache slots 22…43)
  → untied language-model head
```

> "The Core AI authoring overlay therefore retains: 22 trainable block instances and 111 physical
> linear modules; 44 logical KV-cache layers; one serialized and quantized copy of every physical
> weight; execution order `22 blocks → norm → same 22 blocks → norm`."

## 2.2 `CONTRIBUTING.md` — the contribution/gate protocol (read in full today)

**The toolchain gate, verbatim (this is the single highest-value version fact in the repo):**

> "## Toolchain requirement
>
> Export with **coreai-core ≥ 1.0.0b2**. Bundles exported with earlier wheels are rejected by the
> Xcode 27 beta 3+ SDK loader (`Failed to convert to versioned IR` — tracked as **FB23666783**);
> the zoo's own pre-b2 artifacts are being migrated for the same reason."

Acceptance bars, verbatim:

> "1. **License** — the upstream license must permit redistributing converted weights…
>  2. **Parity** — teacher-forced / oracle top-1 parity against the fp32 reference implementation
>     (HF `transformers` or the official repo), plus a greedy-rollout sanity check…
>  3. **Real hardware** — measured on an Apple silicon Mac at minimum (tok/s for LLMs, RTF for
>     audio); iPhone numbers if you publish an iOS variant. **Debug builds don't count — measure
>     Release.**"

Device gate, verbatim:

> "Everything in a port is reproducible on any Apple silicon Mac except one thing: what the model
> does on a phone. AOT load, thermals, sustained tok/s under DVFS, the memory ceiling — those need
> an iOS 27 device… A maintainer runs it on an **iPhone 17 Pro (iOS 27 beta)**."

Repo tooling named:
- `python3 conversion/zoo_convert.py show <name>` — "must print a complete command"
- `python3 conversion/zoo_verify.py <your-hf-repo>` — "should report no FAIL"
- Per-model files: `models/<model-id>/README.md` + `models/<model-id>/recipe.toml`
- Runbook: `PORTING.md`; knowledge base: `knowledge/README.md`;
  **`knowledge/evaluations-framework.md`** exists (relevant to the Evaluations-framework agent)
- Consumption: **`ChatSession(catalog: "your-model")`** — one-line Swift via
  [`john-rocky/coreai-kit`](https://github.com/john-rocky/coreai-kit)
- Issue templates: `model-request.yml`, `device-gate-request.yml`, `bench-result.yml`, `bug-report.yml`

## 2.3 Issue #3 — a real on-device benchmark blob (schema + numbers)

`[bench] iPhone18,1 · qwen3.5-0.8b`, OPEN, filed by the maintainer. Full JSON in the issue; the
`kind` is `"coreai-community-bench"`, protocol `"pb-random-v1"`. Key values:

```json
"device":  {"model_identifier": "iPhone18,1", "os": "iOS 27.0", "os_build": "24A5355q", "memory_gb": 12.3}
"model":   {"id": "qwen3.5-0.8b",
            "bundle": "qwen3_5_0_8b_decode_int8hu_perchan_sym",
            "bundle_kind": "aimodel",
            "hf_repo": "mlboydaisuke/qwen3.5-0.8B-CoreAI",
            "hf_revision": "34ed8b08946395397c3b01d07d0a532237e71af3"}
"protocol":{"chunk_threshold": 1, "cold_runs": 1, "warm_runs": 3,
            "prompt_tokens": 128, "max_tokens": 256, "temperature": 0, "prompt_seed": 0}
"results": {"load_s": 3.4,
            cold: prefill 31.10 tok/s, decode 70.67 tok/s
            warm: prefill 70.38 / 69.70 / 64.45 tok/s, decode 68.72 / 68.41 / 66.16 tok/s}
```

**Takeaways:** iPhone 18,1 on iOS 27.0 build `24A5355q`, 12.3 GB RAM. A 0.8B int8 Core AI bundle
loads in **3.4 s** and does **~68 tok/s decode**. **Cold prefill is ~2.3× slower than warm**
(31 vs 70 tok/s) — first-run specialization tax is on *prefill*, not decode.
Thermal state stayed `nominal` throughout.

## 2.4 Issue #2 — where the converted models actually live

@enduringstack: "Can you provide your custom CoreAI Model repo?" → @john-rocky (OWNER):

> "All my converted Core AI models are on my Hugging Face: https://huggingface.co/mlboydaisuke"

## 2.5 Issue #4 — you may not need Core AI on Mac at all

`[WebGPU port of TripoSplat]`, OPEN. The filer (@yosun) reported back after building
`yosun/TripoSplatWebGPU`:

> "in the process also discovered that core ai / mac os 27 is not necessary to create a Mac
> version of TripoSplat - just use MPS"

**Takeaway:** for non-LLM generative graphs, PyTorch-MPS remains a viable Mac path; Core AI's value
is the iOS/ANE/AOT story, not "the only way to run on Mac."

## 2.6 PRs #7–#10 (@seanxylin) — all CLOSED unmerged, but #7 is a goldmine

The maintainer closed all four but wrote a substantive review on #7:

> "Maintainer here. This comes after the close, but I read all three PRs plus #10. For this
> document in particular, I cross-checked a number of its claims against the actual repositories —
> the SwiftPM pin revisions, the conversion/overlay/BASE commit, the verbatim quotes from the
> apple/coreai-models README, and the model count. **Everything I checked was accurate**…
>
> One gap to be aware of: this repo hasn't published a Core AI conversion of a **frame-
> interpolation model (RIFE)** yet, so that piece has nothing to download today… Contributions are
> welcome going forward; PRs that build and run standalone are much easier to review."

### PR #7's `knowledge/coreai-models-apple-overview.md` — extracted facts about `apple/coreai-models`

*(Second-hand — from an unmerged PR — but maintainer-spot-checked. Flagging as MEDIUM confidence;
another agent covering `apple/coreai-models` directly should be treated as authoritative over this.)*

**Repo shape:** `models/` (catalog, 22 entries), `python/` (`coreai_models` package),
`swift/` (SwiftPM package), `skills/` (agent-skill plugin), `.claude-plugin/marketplace.json`,
`.github/ISSUE_TEMPLATE/{bug_report,model_request,workflow_feedback}` — **no PR template**.

**SwiftPM products (5):** `CoreAILM` (→ target `CoreAILanguageModels`), `CoreAIDiffusion`
(→ `CoreAIDiffusionPipeline`), `CoreAISegmentation` (→ `CoreAIImageSegmenter`), `CoreAISpeech`,
`CoreAIObjectDetection` (→ `CoreAIObjectDetector`). Plus a `CXGrammar` C++ target linking
**`xgrammar`** for guided generation. Five CLI executables under `Sources/Tools/`:
`llm-runner`, `image-segmenter`, `object-detector`, `diffusion-runner`, `speech-runner`, and a
separate `llm-benchmark` target "based on mlx-lm benchmark".

**22-model catalog:** LLMs `gemma3, gpt_oss, mistral, mixtral, qwen2, qwen3, qwen3_moe`;
diffusion `stable-diffusion, flux2`; VLM `vlm (Qwen3-VL)`; vision `clip, depth-anything, edsr,
efficient-sam, pvt, sam3, yolo`; audio `clap, wav2vec2, whisper`; text `roberta, t5`.

**Compression presets** (per `models/README.md`): macOS default `4bit` (INT4 weight-only,
block 32); iOS default `4bit_weight_palettized_group32`, alternatives
`4bit_weight_palettized_group8` and `none`; **Embedding forced to 8-bit-per-tensor on all iOS
presets**. Custom mixed-precision YAML e.g. `models/qwen3/qwen3_0_6b_mixed_4bit_8bit.yaml`.

**ANE authoring rules** (from `skills/skills/model-authoring/references/neural_engine_rules.md`,
479 lines):
- max tensor rank **5**; dtypes **fp16/int8/int16 only** (fp32 falls back off-ANE); fully static shapes
- **last axis is ANE "width", must be 64-byte aligned**; a singleton last axis pads to 64 bytes =
  **32× memory at fp16, 64× at int8** — never put a size-1 dim last
- **BC1S**: `(B,S,D) → (B,D,1,S)` via `permute(0,2,1).unsqueeze(2)`; multi-head `(B,H,S,D) → (B,H*D,1,S)`
- **`Conv2d` not `Linear`** for projections; convert with `linear.weight.unsqueeze(-1).unsqueeze(-1)`
- **no fp32 literals** — even `x * 1.0` creates an f32 buffer; use `torch.ones(1, dtype=x.dtype)`
- per-head attention only, `einsum("bchq,bkhc->bkhq", …)`
- **causal mask shape `(1, key, 1, query)` — transposed vs GPU — masked value `-40000.0`, never
  `float('-inf')`** (ANE softmax mishandles IEEE −inf)
- RoPE precomputed outside the graph as 4D `(1, head_dim, 1, S)`
- **KV cache readonly functional I/O**: `[n_layers, B, H_kv*D, 1, max_S]`, sequence on **dim 4**;
  model returns new K/V, Python writes the slots. **Must return post-RoPE `key_rope`, not raw
  `new_k` — caching pre-RoPE keys collapses PSNR to ~20 dB.**
- chunked prefill `CHUNK=64`, offset = `chunk_start`; per-token `S_q=1` prefill accumulates fp16
  error past ~50 tokens
- entrypoint naming: `extend_{ctx}_{len}`, `prompt_opt_{ctx}_{len}`, `gather_embeddings_{N}`

**GPU rules** (`gpu_rules.md`, 297 lines):
- fused QKV; fused Q/K-norm+RoPE before splitting
- **compute `up_proj` before `gate_proj`** — "reversed from many reference implementations but
  yields better GPU utilization"
- **KV cache stateful**: `[n_layers, B, H_kv, max_S, D]`, sequence on **dim 3**, via custom op
  **`coreai::mutable_slice_update`**, compiled with `mutable_arg_action="hoistToArg"` in
  `LegalizeToCoreOptions`. **Stateful transform APIs reset state between inference calls — don't
  use them for token generation.**
- MoE: `SwitchLinear` (weights `(num_weight_sets, num_experts, out, in)`) + `SwitchGLU` via
  `coreai_torch.composite_ops.GatherMM`; expert indices cast to `uint16`
- large models: meta-device init + `load_state_dict(..., assign=True)` + layer-at-a-time
  safetensors streaming

**Common issues** (`common_issues.md`, 176 lines) — the debugging lookup table:
- ANE SDPA PSNR 15–30 dB → causal-mask orientation bug
- `"does not match"` dtype error → use `"si32"` not `"i32"` in the descriptor
- import error re input counts → filter `input_specs` to `USER_INPUT`/`BUFFER` kinds
- ANE MLP "3 invalid ops from `mps.swish`" → replace `F.silu(x)` with `gate_pre * torch.sigmoid(gate_pre)`
- M-RoPE PSNR ~18 dB → match `cat([cos,cos],-1)` then `::2`
- wrong logits on ANE → non-contiguous tensors; `.contiguous()` before `NDArray`
- "compiles but runs on CPU" → recompile with `--preferred-compute neural-engine`
- `embed_tokens()` numpy conversion needs `.detach()`
- **`runner(**inputs)` not `runner(inputs_dict)`** — `InferenceFunction.__call__` takes kwargs
- **output dict key order is non-deterministic — identify K vs V by shape/MSE, never by index**

**Verification gates:** re-authored-vs-source >70 dB; ANE-layout-vs-GPU-layout >70 dB;
compiled-vs-torch ≥40 dB; post-4-bit-palettization ≥35 dB. Runtime-level table: fp32 e2e >70 dB
(investigate <60); fp16 on-device >50 dB (investigate <40); 4-bit palettized ~40 dB (investigate <30).

**Platform sizing guidance** (`working-with-coreai/references/guidance.md`): iOS models should stay
**under 2 GB**, foreground-oriented; macOS should leave **≥6 GB RAM headroom**. iOS optimization =
static shapes + int4/int8 linear-quant or 2/4/6/8-bit palettization; macOS = dynamic shapes OK,
int4 per-block. Use `.default` specialization unless forcing a compute unit.

**Skill install (Claude Code):**
```
/plugin marketplace add git@github.com:apple/coreai-models.git
/plugin install coreai-skills@coreai-models
```

**Contribution policy — verbatim from `apple/coreai-models` README as quoted in the PR:**

> "We are not accepting code contributions at this time... We are not accepting pull requests at
> launch while we learn how the community uses this project. **If you open a pull request, it will
> be closed.**"

Issues *are* open. License BSD-3-Clause.

**Three distinct Apple Python packages** — do not confuse them:
| Package | Role |
|---|---|
| `coreai-core` | the runtime/IR core; version gate `≥ 1.0.0b2` |
| `coreai-torch` | the **PyTorch → IR converter** (`TorchConverter`, composite ops). `conversion/export_adcsr.py` pins `coreai-torch==0.4.0` via PEP 723 inline deps |
| `coreai-opt` (`coreai_opt`) | the compression/palettization library driven by the `model-compression-exploration` skill |
| `coreai_models` | the model-authoring primitives + export pipeline package inside `apple/coreai-models` |

## 2.7 PR #8 — a real AVFoundation crash worth knowing

> "Fixes a real runtime crash surfaced by e2e testing: a nil-`outputSettings` (passthrough)
> `AVAssetWriterInput` for the audio track needs a `sourceFormatHint` on this SDK, or
> `writer.add(_:)` throws `NSInvalidArgumentException` ('please provide a format hint... to
> perform passthrough')."

---

# PART 3 — `john-rocky/coreai-models` (the community FORK of `apple/coreai-models`)

Issues are **disabled**. Everything below is from the README and the four commits.

## 3.1 Why the fork exists — verbatim README

> "**Why this fork exists.** The upstream Swift pipelined inference engine validates exactly two
> model states (the KV cache pair) and only `input_ids`/`position_ids` inputs, so it cannot load
> *hybrid-attention* or *state-space* language bundles — e.g. Qwen3.5/3.6 (GatedDeltaNet),
> LFM2.5, and Granite 4 (Mamba2) **fail at load with `Expected 2 states, got 4`**."

**This is the single most actionable error string in the whole Core AI ecosystem.**

## 3.2 What the patch adds — verbatim README

> "- **Hybrid / SSM extra states** — the pipelined engine accepts `≥ 2` states and binds up to two
>   fixed-shape extra states beyond the KV pair (the conv/recurrent states of hybrid models),
>   zeroing them on `reset()`.
> - **Per-token inputs** — an optional `EngineOptions.perTokenInputProvider` to fill model inputs
>   gathered by the step's token id (e.g. **Gemma per-layer-embedding rows**).
> - **Static inputs** — an optional `EngineOptions.staticInputBuffers` to bind a constant host
>   buffer (e.g. an mmap'd embedding table) unchanged on every encode.
> - A **static-shape logits-buffer sizing fix for decode-only `S=1` graphs**, and a one-line SSM
>   state-descriptor shape fix on the Python export side (`primitives/macos/cache.py`).
> - **(`v0.1.1-zoo`) Stop on consumer break.** When the consumer stops the returned token stream —
>   what every executor does at EOS — the pipelined engine now stops within pipeline depth instead
>   of generating on to `maxTokens` in the background. The leftover post-EOS tokens used to be
>   consumed into the KV cache, so the next turn's `reset()`/`drain()` blocked on them (a
>   multi-turn latency tax) and a slow model risked `drain()`'s fatalError. **Measured: a two-turn
>   chat through Apple's own `CoreAILanguageModel` adapter dropped its second-turn latency from
>   2.74 s to 0.40 s, with byte-identical output.**"

Scope: **only** `swift/.../InferenceEngines/{CoreAIPipelinedEngine,EngineFactory}.swift` and
`python/.../primitives/macos/cache.py` differ from upstream. Tags: `v0.1.0-zoo`, `v0.1.1-zoo`.
Branches: `main`, `flux2-in-context-edit`, `zoo-0.1-local`, `zoo-0.2`.
Consumers: `john-rocky/coreai-kit` and `john-rocky/coreai-models-community`.

## 3.3 Commit `0fdf7107` — `trimKVCache` for cross-turn prefix reuse (2026-07-03)

Verbatim commit message:

> "Rewind the KV cache to a given length so a chat loop can keep the cache for the shared
> conversation prefix and prefill only the new tokens, instead of a full re-prefill every turn.
> **Pure-attention KV only; recurrent/SSM engines return a negative value so the caller falls back
> to reset() + full re-prefill.**
>
> - `trimKVCache(to:) -> Int`   (retained prefix length, <0 = unsupported)
> - `prefixReuseFeedsFullSequence`  (sequential feeds full seq / pipelined feeds delta)
> - implemented on `CoreAISequentialEngine` and `CoreAIPipelinedEngine`"

Files touched: `CoreAIPipelinedEngine.swift (+29)`, `CoreAISequentialEngine.swift (+13)`,
`InferenceEngine.swift (+27)`.

**Takeaway:** upstream Core AI's `InferenceEngine` protocol (as of 2026-06) had **no KV-cache
trim / prefix-reuse primitive**. Multi-turn chat re-prefills the whole transcript every turn
unless you patch the engine. Recurrent/SSM models can't do prefix reuse at all.

## 3.4 Upstream README facts confirmed from the fork's copy

- **Requirements: macOS and iOS 27.0+, Xcode 27.0+.**
- Models are `.aimodel` files; multi-asset models ship a resource folder.
- Discovery: `git clone https://github.com/apple/coreai-models.git && cd coreai-models` then
  `uv run coreai.model.registry --list-models` (and `--help`). `uv` install via
  `brew install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`.
- Three agent skills: `working-with-coreai`, `model-authoring`, `model-compression-exploration`.

---

# PART 4 — `lucasnewman/mlx2coreai`

**Zero issues, zero PRs. 11 commits, all 2026-06-08/09. Version 0.1.1. Effectively a spike.**

## 4.1 What it is (README, verbatim)

> "Experimental MLX to CoreAI conversion. `mlx2coreai` captures MLX graphs, lowers supported ops to
> CoreAI MLIR, and writes `.aimodel` assets or coreai-models-style LLM bundles."

## 4.2 CLI + API (verbatim)

```bash
pip install mlx2coreai

mlx2coreai convert-mlx-lm-stateful mlx-community/Qwen3-0.6B-bf16 \
  --output qwen \
  --max-context-length 256
```

> "The exported model has one `main` entrypoint with `input_ids`, `position_ids`, and mutable
> `keyCache` / `valueCache` state."
> "For autoregressive language models, use the stateful converter. It writes a bundle containing
> `metadata.json`, `tokenizer/`, and a nested `.aimodel`."

```bash
python scripts/benchmark_aimodel_sampling.py qwen \
  --contexts 16,32,64,128,256 \
  --steps 16 \
  --decode
```

> "The benchmark accepts either the bundle directory (`qwen`) or the nested asset path
> (`qwen/qwen.aimodel`). It uses the embedded tokenizer when present."

Generic function conversion:

```python
from mlx2coreai import ConversionConfig, convert_mlx_to_coreai

converted = convert_mlx_to_coreai(
    model,
    {"x": np.ones((2, 3), dtype=np.float32), "w": np.ones((3, 4), dtype=np.float32)},
    config=ConversionConfig(optimize=True),
    output_path="model.aimodel",
)
print(converted.asset_path)
```

Runtime:

```python
from mlx2coreai import run_aimodel
result = await run_aimodel("model.aimodel", {"x": np.ones((2, 3), dtype=np.float32)})
print(result.outputs)
```

…gated on: *"When the local CoreAI runtime is available"*.

Console scripts (`pyproject.toml`): `mlx2coreai`, `mlx2coreai-convert-mlx-lm`,
`mlx2coreai-convert-mlx-lm-stateful`.

## 4.3 Dependencies & version pin — a real footgun

```toml
requires-python = ">=3.11"
dependencies = ["coreai-core==1.0.0b1", "ml-dtypes", "mlx", "mlx-lm", "numpy"]
```

**`coreai-core==1.0.0b1` is HARD-PINNED.** Per `coreai-model-zoo/CONTRIBUTING.md`, bundles
produced by pre-`1.0.0b2` wheels are **rejected by the Xcode 27 beta 3+ SDK loader** with
`Failed to convert to versioned IR` (FB23666783). **So mlx2coreai 0.1.1 as published produces
bundles that a current Xcode 27 beta will refuse to load.** That is a concrete, high-value gotcha.

## 4.4 Op coverage — 156 source ops → 121 lowering keys (from `docs/op_coverage.md`)

> "Coverage type: CoreAI asset generation. **This does not imply runtime numerical parity.**"

```
Supported source op names in registry: 156
Distinct lowering keys in registry:    121
Coverage graphs: 26   Coverage graph nodes: 252
Unique source ops exercised: 156   Unique lowering keys exercised: 121
Asset validation: passed
Unexercised Registry Ops: None
```

Notable lowerings present: `scaled_dot_product_attention`, `rope`, `rmsnorm`, `layernorm`,
`softmax`, `silu`, `gelu`, `conv1d/2d/3d` → `conv`, `conv_transpose1d/2d/3d` → `conv_transpose`,
`dynamic_slice_update`, `slice_update`, `read_state`, `write_state`, `state_update_masked`,
`gather`, `gather_along_axis`, `tensordot`, `kron`, `meshgrid`, `divmod`, `nan_to_num`,
`logaddexp`, `reduce_log_sum_exp`, `inverse`, `trace`, `diag`/`diagonal`, `tri`/`tril`/`triu`.

Closing notes, verbatim:

> "- Coverage is asset-generation coverage, not runtime numerical parity.
> - **Runtime parity requires the macOS / iOS 27+ CoreAI execution stack.**
> - **General transposed convolution uses a named composite fallback when the beta CoreAI asset
>   writer rejects native `conv_transpose` IR**; the vendored 1x1 stride-1 case lowers without that
>   fallback."

## 4.5 Commit-log signal

```
2026-06-09  059c9f36  Add a swift runner as python bindings are incomplete as of now.
2026-06-09  d032a950  Cleaner conversion API.
2026-06-08  5e9c7de4  Allow optimization on SDPA for macOS 27.
2026-06-08  dab70964  Fix runtime on macOS 27.
```

**`"Add a swift runner as python bindings are incomplete as of now."`** — as of 2026-06-09 the
**Core AI Python runtime bindings were incomplete**, which is why the repo carries
`scripts/benchmark_aimodel_sampling_coreai.swift` alongside the Python benchmark.
**UNVERIFIED whether that is still true today.**

---

# PART 5 — `1amageek/swift-lm`

Description: "Hugging Face native LLM inference on Apple Silicon via direct Metal." One issue,
zero PRs. But the repo pivoted hard to Core AI in July 2026.

## 5.1 Issue #1 — iOS/Catalyst build failures (CLOSED, authoritative fix)

`#1` (2026-05-13, @Gregor321123). Compiling the README's own example for iOS:

```
'storageModeManaged' is unavailable in iOS
'didModifyRange' is unavailable in iOS
```

For Mac Catalyst:

```
'homeDirectoryForCurrentUser' is unavailable in Mac Catalyst
```

> "The package only works when compiling for macOS yet."

**Owner @1amageek's resolution (2026-07-17), verbatim:**

> "Fixed in e956e56 and verified again on the current main branch with **Xcode 27 beta**.
>
> Validated full package builds:
> - generic iOS destination
> - generic Mac Catalyst destination
>
> The managed Metal storage option is now **guarded to macOS/x86_64**, and non-macOS/Catalyst
> cache resolution uses the **platform caches directory** instead of `homeDirectoryForCurrentUser`."

**Takeaway for anyone writing Metal-backed Swift ML packages:** `MTLResourceOptions.storageModeManaged`
and `MTLBuffer.didModifyRange(_:)` are **macOS/x86_64-only**; on Apple silicon and iOS use shared
storage. And `FileManager.default.homeDirectoryForCurrentUser` is unavailable under Catalyst.

## 5.2 The pivot: Metal → Core AI (commit log, July 2026)

```
2026-07-18  db7a8022  Add Core AI vision language model adapter
2026-07-17  537f24d1  Add Core AI MoE and Qwen3.5 state-space lowering
2026-07-17  b2cf3b4a  Build Core AI-first declarative export pipeline
2026-07-17  e956e56f  Add Core AI bundle validation
2026-07-12  10ac8490  Centralize Hugging Face model routing and config decoding
2026-07-12  2d142d88  Add stateful LFM2 Core AI export
2026-07-12  30bd6655  Complete Core AI model export paths
2026-07-12  97b62940  Add Core AI export and runtime support
2026-06-09  d30e5890  Prepare swift-lm 0.10.0 release
```

README states the strategy verbatim:

> "The direct Metal runtime remains available as the **0.10 compatibility path**. New model support
> and public API work should target **Core AI first**."

## 5.3 Requirements (README, verbatim)

> "- Xcode 27 beta or later
> - **Swift 6.4+**
> - macOS 27.0+ or iOS 27.0+ as declared by `Package.swift`
> - Apple Silicon for local Core AI execution"

SwiftPM: `.package(url: "https://github.com/1amageek/swift-lm.git", from: "0.11.0")`, product
`SwiftLMFoundationModels`.

**`Swift 6.4+` is a notable data point** — that's the Swift version shipping with Xcode 27.

## 5.4 The Core AI export pipeline (README, verbatim)

```text
Hugging Face config.json
        |
        v
ModelDeclarations -> LMIR -> CoreAIExportDocument
                                      |
                                      v
                         coreai-models / coreai-torch
                                      |
                                      v
                                  .aimodel
                                      |
                                      v
                                  Core AI
```

Exact CLI:

```bash
xcrun swift run swiftlm-ir \
    --config /path/to/config.json \
    --output /tmp/model.json \
    --name model \
    --target macos

PYTHONPATH=python/src python3 -m swiftlm_coreai.cli validate /tmp/model.json

python3 -m venv .venv
.venv/bin/pip install -e python
.venv/bin/swiftlm-coreai export /tmp/model.json \
    Qwen/Qwen3-0.6B \
    --output-dir /tmp/coreai-model \
    --overwrite
```

Stateful variant (`--stateful`) — and the **exact state names for LFM2**:

> "For LFM2 this exposes `keyCache`, `valueCache`, and `convCache`; `input_ids` carries one token
> per call and `position_ids` carries the complete prefix position range"

```bash
xcrun swift run swiftlm-ir --config /path/to/lfm2/config.json \
    --output /tmp/lfm2-stateful.json --name lfm2-stateful --target macos --stateful
```

## 5.5 What the generic lowerer supports — and what hard-fails (README, verbatim)

> "The generic lowerer currently implements token embedding, RMSNorm, LayerNorm, LayerScale,
> Linear, dense MLP, baseline RoPE attention, ShortConv, SwiGLU MoE, **Qwen3.5 GatedDeltaNet
> state-space recurrence**, per-head packed sigmoid attention gates, output heads, residual-add,
> parallel-add, repeat, and layer-index conditionals.
> MoE supports softmax Top-K routing and LFM2 sigmoid Top-K routing with optional selection bias,
> normalization, and routed scaling through **Apple's `SwitchGLU`**. Qwen3.5 text hybrids lower
> GatedDeltaNet through **Apple's `GatedDeltaUpdate` composite** with explicit convolution and
> float32 recurrent state. Source tokenizer assets are copied directly from the Hugging Face
> bundle without a model-specific Transformers tokenizer class.
> **Contracts that require vision primitives, other state-space variants, sliding-window attention,
> scaled or multiaxis M-RoPE inputs, other attention gates, unsupported expert MLPs, or
> axis-dependent parallel merges fail before graph construction with an operation path. They never
> fall back to a second model definition.**"

**Named Core AI composites confirmed here: `SwitchGLU`, `GatedDeltaUpdate`.**

## 5.6 Runtime API (README, verbatim)

```swift
let bundle = try CoreAIModelBundle(contentsOf: bundleURL)
let session = try await bundle.makeStatelessSession()
let outputs = try await session.run(
    inputs: ["input_ids": inputIDs, "position_ids": positionIDs],
    outputShapes: ["logits": [1, tokenCount, bundle.document.metadata.vocabSize]]
)

// dynamic-shape asset: resolve states at session creation, outputs at execution
let session = try await bundle.makeStateSession(maxContextLength: 40960)
let outputs = try await session.run(inputs: ["input_ids": inputIDs, "position_ids": positionIDs])
```

VLM three-asset boundary (verbatim):

```text
image -> vision.aimodel ----+
                            v
prompt -> embed.aimodel -> decoder.aimodel -> generated text
```

```swift
let bundle = try SwiftLMFoundationModelBundle(contentsOf: bundleURL)
let model = try await bundle.makeVisionLanguageModel()
let output = try await model.generate(
    from: SwiftLMVisionLanguageInput(imageURL: imageURL, prompt: .text(prompt))
)
```

> "Text prompts must render **exactly one image placeholder** through the bundle's chat template;
> the adapter expands it to the declared visual token count… Missing or ambiguous placeholders fail
> with a typed error rather than using a generic prompt fallback. **The model owns mutable KV
> state, so call `reset()` before starting an unrelated request.**"
> Stop tokens: `SwiftLMVisionLanguageGenerationOptions.additionalStopTokenIDs`.

`CoreAIModelBundle` "verifies the embedded Swift contract against the asset's function names,
tensor types, shapes, and state layout **before specialization**."

## 5.7 Legacy 0.10 Metal API (still shipped)

Types: `ModelBundleLoader`, `LanguageModelContainer`, `LanguageModelContext`, `ModelInput`,
`GenerationParameters`, `PromptSnapshot`, `TextEmbeddingContainer`, `TextEmbeddingContext`,
`TextEmbeddingInput`.

```swift
let container = try await ModelBundleLoader().load(repo: "LiquidAI/LFM2.5-1.2B-Instruct")
let input = ModelInput(chat: [.system("…"), .user("…")],
                       promptOptions: .init(isThinkingEnabled: true))
let stream = try await container.generate(input, parameters: GenerationParameters(
    maxTokens: 128, streamChunkTokenCount: 8, temperature: 0.6, topP: 0.9, reasoning: .separate))
for await event in stream {
    switch event {
    case .text(let text): …
    case .reasoning(let reasoning): …
    case .completed(let info): print(info.tokenCount, info.tokensPerSecond)
    }
}
```

> "`ModelBundleLoader` creates **`model.staf`** next to the source weights when the executable
> cache needs to be generated. The cache can be deleted and rebuilt from `safetensors`."

Embeddings: `ModelBundleLoader().loadTextEmbeddings(repo: "google/embeddinggemma-300m")` →
`embeddings.embed(TextEmbeddingInput("…", promptName: embeddings.defaultPromptName))`.
Supported: `google/embeddinggemma-300m`, `mlx-community/embeddinggemma-300m-bf16`,
`mlx-community/embeddinggemma-300m-4bit`.

Multimodal capability introspection: `configuration.inputCapabilities`,
`configuration.executionCapabilities`, `configuration.vision`. Explicit gap:
**"Gemma4 video execution is not implemented."**

---

# PART 6 — `noemaai-labs/noema-ios` (a shipping app that uses AFM + Core AI + PCC)

The most useful "what a real shipping app actually does" source in this set. 599 Swift files.
PR #14 (merged 2026-07-24) republished the whole thing as "Noema 3.5" (+248,522/−177,669).

## 6.1 Its backend taxonomy (README `ModelFormat` enum, verbatim)

> "- **GGUF** – quantized weights run by the single bundled llama.cpp runtime…
> - **MLX** – Apple's Metal-accelerated format for running models natively on Apple Silicon
>   (integrated via Swift Package Manager).
> - **ExecuTorch (ET)** – PyTorch ExecuTorch models, with XNNPACK / CoreML / MPS backends.
> - **CoreML / ANE (CML)** – CoreML model bundles that run on the Apple Neural Engine.
> - **Apple Foundation Models (AFM)** – Apple's built-in on-device foundation model (Apple
>   Intelligence), available on **OS 26 and later** with Apple Intelligence enabled.
> - **CoreAI** – downloadable Apple on-device foundation-model bundles, available on **OS 27 and
>   later**."

Platform requirements (verbatim): iOS/iPadOS 18+, A12 Bionic+; macOS 26 (Tahoe)+, Apple Silicon;
visionOS 26+. "Apple Foundation Models / CoreAI features require OS 26+ / 27+ respectively."

## 6.2 `Noema/AppleFoundationModelAvailability.swift` — the availability switch, verbatim

```swift
if #available(iOS 26.0, macOS 26.0, visionOS 26.0, *) {
    let model = SystemLanguageModel.default
    switch model.availability {
    case .available: …
    case .unavailable(let reason):
        switch reason {
        case .appleIntelligenceNotEnabled: …
        case .modelNotReady: …
        case .deviceNotEligible: …
        @unknown default: …
        }
    @unknown default: …
    }
}
```

**Confirms the Swift enum:** `SystemLanguageModel.default.availability` ∈
`.available` | `.unavailable(.appleIntelligenceNotEnabled | .modelNotReady | .deviceNotEligible)`.
(Compare the Python SDK's `SystemLanguageModelUnavailableReason`.)

## 6.3 `PrivateCloudComputeLanguageModel` — the iOS/macOS 27 PCC API, verbatim

Gated behind `#if NOEMA_ENABLE_XCODE27_APIS` + `if #available(iOS 27.0, macOS 27.0, visionOS 27.0, *)`:

```swift
let model = PrivateCloudComputeLanguageModel()
switch model.availability {
case .available:
    let quota = model.quotaUsage
    if quota.isLimitReached {
        return .limitReached(resetDate: quota.resetDate)
    }
    if case .belowLimit(let information) = quota.status,
       information.isApproachingLimit {
        return .approachingLimit
    }
    return .available
case .unavailable(.deviceNotEligible): …
case .unavailable(.systemNotReady): …
case .unavailable: …
@unknown default: …
}
```

```swift
PrivateCloudComputeLanguageModel().quotaUsage.limitIncreaseSuggestion   // Optional
suggestion.show()                                                       // presents system UI
```

**This is a very high-value find.** Verified API surface of `FoundationModels`'
`PrivateCloudComputeLanguageModel` (iOS/macOS/visionOS 27+):
- `.availability` → `.available` | `.unavailable(.deviceNotEligible)` | `.unavailable(.systemNotReady)`
  — note the reason cases **differ** from `SystemLanguageModel`'s
- `.quotaUsage` → has `.isLimitReached`, `.resetDate`, `.status` (with case
  `.belowLimit(let information)` where `information.isApproachingLimit`), and
  `.limitIncreaseSuggestion` (optional, with `.show()`)
- Requires network; Noema also gates on its own off-grid / kill-switch / enterprise-policy flags.

## 6.4 `Noema/CoreAILLMClient.swift` (2,193 lines) — production Core AI runtime usage

### Error taxonomy the app surfaces

```swift
enum CoreAILLMClientError: LocalizedError {
    case unsupportedOS            // "Core AI models require iOS 27 / macOS 27 or later."
    case frameworkUnavailable     // "The Core AI framework is unavailable in this build (requires Xcode 27+)."
    case generationUnavailable(String)
}
```

### Specialization options keyed off the *bundle folder name* — verbatim comment + code

```swift
/// Compute-unit preference derived from the bundle's repo folder, following
/// the published Core AI export conventions (coreai-model-zoo): `ios-ane/`
/// bundles are the dynamic graphs proven on the Neural Engine; `ios-gpu/`
/// static monoliths use fp32 SSM intermediates + custom Metal kernels and
/// fail ANE specialization ("ANE cannot handle intermediate tensor type
/// fp32"); `gpu-pipelined/` and `macos/` are GPU graphs. Exact path-component
/// matches only — substring checks mis-fire on names like "gated-deltanet".
@available(iOS 27.0, macOS 27.0, visionOS 27.0, *)
static func specializationOptions(for modelURL: URL) -> SpecializationOptions {
    let components = Set(modelURL.pathComponents.map { $0.lowercased() })
    if components.contains("ios-ane") {
        #if os(macOS)
        var options = SpecializationOptions(preferredComputeUnitKind: .gpu)
        #else
        let preferred: ComputeUnitKind = ComputeUnitKind.availableKinds.contains(.neuralEngine) ? .neuralEngine : .gpu
        var options = SpecializationOptions(preferredComputeUnitKind: preferred)
        #endif
        options.expectFrequentReshapes = true  // dynamic sequence dimension
        return options
    }
    if components.contains("macos") || components.contains("gpu-pipelined") {
        var options = SpecializationOptions(preferredComputeUnitKind: .gpu)
        options.expectFrequentReshapes = true
        return options
    }
    if components.contains("ios-gpu") {
        var options = SpecializationOptions(preferredComputeUnitKind: .gpu)
        options.expectFrequentReshapes = false  // fully static shapes
        return options
    }
    return .default
}
```

**Verified Core AI API names:** `SpecializationOptions(preferredComputeUnitKind:)`,
`SpecializationOptions.expectFrequentReshapes`, `SpecializationOptions.default`,
`ComputeUnitKind.{gpu, neuralEngine}`, **`ComputeUnitKind.availableKinds`**.
Runtime error string worth grepping for: **"ANE cannot handle intermediate tensor type fp32"**.

### The documented load-and-cache flow — verbatim

```swift
/// Documented load flow (Core AI "Managing model specialization and
/// caching"): check `AIModelCache.default`, otherwise
/// `AIModel(contentsOf:options:)` — which specializes **and** stores the
/// result in the default cache automatically. On failure, clear the
/// possibly-stale/evicted cache entry and retry once; if the preferred
/// compute unit still can't be specialized for this model on this device,
/// fall back to `.default` options (compiler picks the units).
private static func loadSpecializedModel(url: URL, options: SpecializationOptions) async throws -> AIModel {
    if let cached = try? AIModelCache.default.model(for: url, options: options) { … }
    do { return try await AIModel(contentsOf: url, options: options) }
    catch {
        // Clear every cached variant of this model: each SpecializationOptions
        // change leaves its own multi-GB entry behind, and stale/evicted
        // entries are the documented way loads get wedged under storage pressure.
        try? AIModelCache.default.deleteEntries(for: url)
        do { return try await AIModel(contentsOf: url, options: options) }
        catch {
            guard options != .default else { throw error }
            if let cached = try? AIModelCache.default.model(for: url, options: .default) { return cached }
            return try await AIModel(contentsOf: url, options: .default)
        }
    }
}
```

**Verified Core AI API:** `AIModel(contentsOf:options:)` (async throwing),
`AIModelCache.default.model(for:options:)`, `AIModelCache.default.deleteEntries(for:)`,
`AIModelAsset.isValid(at:)`, `model.functionNames: [String]`,
`model.functionDescriptor(for:) -> InferenceFunctionDescriptor?`,
`model.loadFunction(named:) throws -> InferenceFunction?`,
`InferenceFunctionDescriptor.{inputNames, outputNames, stateNames}`.

**Documented cost:** *"each `SpecializationOptions` change leaves its own multi-GB entry behind."*
Changing compute-unit preference multiplies on-disk cache.

### Pre-flight validity check

```swift
guard AIModelAsset.isValid(at: resolved.modelURL) else {
    throw CoreAILLMClientError.generationUnavailable(
        String(localized: "The Core AI model bundle is invalid or incomplete. Delete the model and download it again.")
    )
}
```

### Re-specialization footgun — chunked prefill bucket strategy, verbatim comment

```swift
/// Chunk schedule for prompt processing through the decode graph. Static
/// graphs are fixed at their exported query length. Dynamic-query graphs
/// accept any length, but every NEW input shape triggers a device
/// re-specialization — so feed a fixed bucket, then power-of-two remainder
/// chunks: a handful of shapes total, each compiled once and reused across
/// prompts, instead of one fresh compile per prompt length.
private static func prefillChunkSize(remaining: Int, perStep: Int) -> Int {
    guard remaining > 0 else { return 1 }
    guard perStep == Int.max else { return min(max(1, perStep), remaining) }
    let bucket = 32
    if remaining >= bucket { return bucket }
    var size = 1
    while size * 2 <= remaining { size *= 2 }
    return size
}
```

**This is one of the most important practical Core AI facts anywhere: every new input shape on a
dynamic-shape graph triggers a device re-specialization (a compile).** Bucket your shapes.

### LanguageBundle `metadata.json` schema — synthesized by the app, verbatim

```swift
let metadata: [String: Any] = [
    "metadata_version": "0.2",
    "kind": "llm",
    "name": name,
    "assets": ["main": bundleURL.lastPathComponent],
    "language": [
        "tokenizer": Self.exportedTokenizerID(resourceRoot: root) ?? "",
        "vocab_size": tokenizer?.vocabularySize ?? 0,
        "max_context_length": maxContextTokens,
        "embedded_tokenizer": true,
        "function_map": ["main": ["main"]],
    ] as [String: Any],
]
```

Tokenizer files copied into `tokenizer/`:
`tokenizer.json`, `tokenizer_config.json`, `special_tokens_map.json`, `chat_template.jinja`,
`added_tokens.json`, `vocab.json`, `merges.txt`.

`language.max_context_length` from the variant `metadata.json` **caps the user-selected context**.

### Engine eligibility rule + the `ios-ane` carve-out, verbatim

```swift
/// The engine needs the LanguageBundle layout (variant-level metadata.json).
/// On iOS, `ios-ane` bundles stay on the per-token decoder: their k-means
/// int8 LUTs are slow on the GPU delegate the pipelined engine would pick,
/// while the Neural Engine path is the export's proven configuration.
static func engineEligible(resourceRoot: URL, modelPath: String) -> Bool {
    let metadata = resourceRoot.appendingPathComponent("metadata.json")
    guard FileManager.default.fileExists(atPath: metadata.path) else { return false }
    #if !os(macOS)
    if modelPath.lowercased().contains("ios-ane") { return false }
    #endif
    return true
}
```

### Engine creation — and the `COREAI_CHUNK_THRESHOLD` env var, verbatim

```swift
let bundle = try LanguageBundle(at: resolved.resourceRoot)
let modelURL = try bundle.requireModelURL(for: ModelBundle.ComponentKey.main)
let config = ModelConfig(
    name: bundle.name, tokenizer: bundle.tokenizer, vocabSize: bundle.vocabSize,
    maxContextLength: bundle.maxContextLength, serializedModel: [bundle.modelAssetPath],
    function: bundle.language.functionMap?.name(for: "main") ?? "main"
)

// S=1 decode-only exports (the published `gpu-pipelined` bundles) can't
// take block prefill — partially-written SSM conv/rec states poison the
// recurrence — so route prefill through pipelined S=1 steps.
if resolved.modelURL.path.lowercased().contains("pipelined") {
    setenv("COREAI_CHUNK_THRESHOLD", "1", 1)
}

let engine = try await EngineFactory.createEngine(
    config: configData, modelURL: modelURL,
    options: EngineOptions(variant: nil, kvCacheStrategy: .auto)
)
// No warmup(): S=1 graphs reject the default warmup shape; the first
// generate call compiles the kernels instead.
```

**Verified `coreai-models` Swift API:** `LanguageBundle(at:)` with `.name`, `.tokenizer`,
`.vocabSize`, `.maxContextLength`, `.modelAssetPath`, `.language.functionMap?.name(for:)`,
`.loadTokenizer()`; `ModelBundle.ComponentKey.main`; `ModelConfig(name:tokenizer:vocabSize:
maxContextLength:serializedModel:function:)`; `EngineFactory.createEngine(config:modelURL:options:)`;
`EngineOptions(variant:kvCacheStrategy:)` with `.auto`; engine `warmup()` exists but
**"S=1 graphs reject the default warmup shape."**
**Env var `COREAI_CHUNK_THRESHOLD` gates block prefill.**

### Prewarm strategy, verbatim comment

```swift
// Build the decoder real requests will reuse — full context window,
// so the session runs ONE state shape, specialized here at load
// time instead of on the first message — warm it with one step,
// then rewind it in place.
```

…and the skip condition:

```swift
guard CoreAIDecoder.hostCacheCapacity(in: descriptor) == nil else {
    print("[CoreAI] Skipping prewarm for host-cache graph; it would allocate the static KV cache.")
    return
}
```

### Chunked-prefill companion graph, verbatim

```swift
/// Loads the chunked-prefill companion graph next to a host-cache decode
/// bundle. The companion is the fast prefill path: the q=1 decode graph
/// consumes one prompt token per forward pass, while the companion takes
/// fixed-size blocks (16/32 tokens per dispatch) with the same state
/// contract and hands the states to the decode graph for generation.
/// Failure is non-fatal — prefill degrades to one token per pass.
```

> "Only host-cache exports publish companions Noema can drive; **the stateful contract has no
> documented cross-bundle state handoff.**"

### Session-long decoder rationale, verbatim

> "Session-long decoder (per-token paths). Its in-place KV/SSM state and its fed-token log persist
> across requests, so the normal chat case — the resent history plus one new message — prefills only
> the unseen suffix instead of the whole transcript, and the device never has to re-specialize a new
> state shape mid-session."

## 6.5 Noema issue threads

| # | State | Problem | Resolution |
|---|---|---|---|
| **#13** | OPEN | *"`Noema/Info.plist` is missing `NSLocalNetworkUsageDescription`. Without it, connecting an MCP server (or any remote backend) that resolves to a private/RFC1918 IP **fails silently — no permission prompt, no network trace, just a generic transport error**."* | @armin976: "We'll update to fix it as soon as possible." **Real, generalizable iOS gotcha for any local-MCP app.** |
| **#11** | CLOSED | Off-Grid (offline) mode → chat fails with `NSURLErrorDomain error -1009`. Reporter: *"Chat is OK when wifi is on but error-1009 with off-grid mode. This 'local' is a joke."* | @armin976 2026-04-22: "this has been fixed"; reporter confirmed 2026-04-24. **A "fully local" LLM app still had a hard network dependency in its chat path.** |
| **#5** | CLOSED | Import local GGUF/MLX files instead of re-downloading through the in-app HF client | Shipped: "this has been implemented" (2026-02-27) after a beta period |
| **#12** | OPEN | iCloud sync request | "we'll look into it" |
| **#10** | OPEN | No custom system/user prompt per chat session | no reply |

## 6.6 Vendored reference material inside noema-ios (worth knowing exists)

`DocumentationforAPIs&SDKs/AppleFoundationModels/*.md` — 18 files:
`ContentTags, CustomAdapter, DynamicSessions, GeneratingContent, GuidedGeneration,
IntelligentAppFeatures, Language, ManagingContextWindow, MultimodalPrompting, OptimizingKV,
Origami, Overview, Prompting, RuntimePerformance, Safety, ToolCalling, UpdatingPrompts,
UsingPrivateCloudCompute`.

`DocumentationforAPIs&SDKs/CoreAI/*.md` — 6 files: `APIReference, AheadOfTimeCompilation,
DebuggingAndProfiling, GettingStarted, Overview, SpecializationAndCaching`.

Also `External/coreai-models/` is **vendored in-tree** — including
`swift/Sources/CoreAILanguageModels/InferenceEngines/{CoreAIPipelinedEngine, CoreAISequentialEngine,
CoreAIStaticShapeEngine, EngineFactory, InferenceEngine}.swift` and
`DecodingStrategies/{ContinuationEvaluation, DecodingStrategy, VanillaDecodingStrategy}.swift`,
`Bundle/{LanguageBundle, LanguageConfig, ModelBundle+Language}.swift`, `Assets/ModelPaths.swift`.

**Three Core AI engine variants confirmed by filename: `CoreAIPipelinedEngine`,
`CoreAISequentialEngine`, `CoreAIStaticShapeEngine`.**

Note: `Origami.md` under AppleFoundationModels is an interesting unexplained name —
**UNVERIFIED** what "Origami" refers to in the FM framework.

Also present: `External/NoemaLLamaServer/.../src/models/afmoe.cpp` — llama.cpp has an **`afmoe`**
model type (Apple foundation-model MoE architecture), **UNVERIFIED** in detail.

---

# PART 7 — `apple/dnikit` (largely dormant; include for completeness)

- "A Python toolkit for analyzing machine learning models and datasets." Apache-2.0, 79★.
- **Last release: `2.0.0`, 2023-08-09.** Between 2023-09-06 and 2026-07-09 there was exactly
  **one commit**: `2f390563 Handle Keras 3 tensor metadata in TF2 models (#4)`.
- Install: `pip install dnikit` / `pip install "dnikit[notebook]"`. Docs: https://apple.github.io/dnikit/

## Issue #2 → PR #4 — Keras 3 broke the TF2 loader for 2 years

`#2` (2024-06-27, @satishlokkoju): running the official
`notebooks/data_introspection/dataset_report.ipynb` raises

```
AttributeError: 'KerasTensor' object has no attribute 'type_spec'
```

from `dnikit_tensorflow/_tensorflow/_tf2_model.py:103` inside
`_Tensorflow2ModelDetails.get_response_infos()`:

```python
dtype=_convert_tf_dtype(layer.output.type_spec.dtype),
shape=_convert_tf_shape(layer.output.type_spec.shape),
```

Env: Python 3.10.14, tensorflow 2.16.1, **keras 3.4.1**, dnikit 2.0.0, Linux.

Fix (PR #4, @kiwigitops, opened 2026-05-25, merged **2026-07-09**):

> "- read TF2 tensor dtype and shape from `type_spec` when available, with a Keras 3 fallback to
>   `dtype` and `shape`
> - normalize tensor metadata through TensorFlow before building `ResponseInfo`
> - use layer metadata when Keras 3 output names are generic, so Conv2D responses still classify
>   correctly"

Maintainer @davidkoski (COLLABORATOR) on merge:

> "Some test failures -- it looks like libraries and test data have moved forward a bit, but I see
> the same failures on main, so not specific to this PR."

**Takeaways:**
- **dnikit as published on PyPI (2.0.0) is broken with Keras 3.** The fix is on `main` only,
  unreleased as of 2026-07-27. Either pin `keras<3` or install from git.
- The maintainer acknowledges **`main`'s own test suite currently fails** due to dependency drift.
- Issue #3 (2026-02-04, @SalimMessaad1) proposes robustness fixes to `_dict_utils.py`
  (`delete_keys` RuntimeError on live `dict.keys()` views; `seq_of_dict_to_dict_of_seq` KeyError on
  heterogeneous keys; `dict_of_seq_to_seq_of_dict` StopIteration on empty dict; silent data loss in
  `rename_keys` collisions) and asks "Would you be open to a PR?" — **no maintainer reply in
  ~6 months.**
- Practical read: dnikit is **not part of the live 2026 stack**. Treat it as a legacy Apple ML
  introspection library with an effectively unstaffed maintenance queue.

---

# CROSS-CUTTING SYNTHESIS

## Version / OS gate table (every gate I verified this session)

| Thing | Gate | Source |
|---|---|---|
| `apple-fm-sdk` build | macOS ≥ 26.0 **and full Xcode.app ≥ 26.0** (CLT rejected) | `build_backend.py` |
| `apple-fm-sdk` runtime | macOS 26.0+, Python 3.10+, Apple Intelligence on | README |
| FM image/`Attachment` prompts (Python) | build SDK macOS 27+ (`-DFM_HAS_MACOS_27_SDK`) **and** runtime macOS 27 | PR #14, `build_backend.py` |
| FM `tokenCount` / `contextSize` | macOS/iOS/visionOS **26.4+** | PR #15 Swift guard |
| `SystemLanguageModel` (Swift) | iOS/macOS/visionOS **26.0+** | noema `AppleFoundationModelAvailability.swift` |
| `PrivateCloudComputeLanguageModel` | iOS/macOS/visionOS **27.0+** | noema `AppleFoundationModelAvailability.swift` |
| Core AI framework | iOS/macOS/visionOS **27.0+**, Xcode **27.0+** | noema `CoreAILLMClient.swift`, coreai-models README |
| Core AI bundle export | **`coreai-core ≥ 1.0.0b2`** — earlier wheels rejected by Xcode 27 beta 3+ SDK loader (`Failed to convert to versioned IR`, FB23666783) | zoo `CONTRIBUTING.md` |
| `swift-lm` Core AI path | Xcode 27 beta+, **Swift 6.4+**, macOS/iOS 27.0+, Apple Silicon | swift-lm README |
| iOS AOT compile target | `--architecture h18p` = iPhone 17 Pro class; **large decode graphs need AOT on iOS, JIT specialization does not survive there** | zoo issue #5 |
| `mlx2coreai` | Python ≥ 3.11, pins `coreai-core==1.0.0b1` (**below the b2 floor**) | `pyproject.toml` |
| dnikit | broken with keras ≥ 3 on PyPI 2.0.0 | issue #2 / PR #4 |

## Error strings worth grepping for (all verified verbatim)

- `Expected 2 states, got 4` — hybrid/SSM bundle on the stock pipelined engine
- `Failed to convert to versioned IR` — bundle exported with `coreai-core < 1.0.0b2`
- `ANE cannot handle intermediate tensor type fp32` — `ios-gpu` static monolith on the ANE path
- `SwiftToolingError: The active developer directory is set to Command Line Tools …` — `pip install apple-fm-sdk` w/o Xcode.app
- `…open Xcodeat least once…` — fingerprint of `apple-fm-sdk` ≤ 0.2.1 build backend
- `OSError: [Errno 9] Bad file descriptor` after ~240–250 image `respond()` calls — the #17 FD leak
- `EXC_BREAKPOINT / SIGTRAP in libswiftCore.dylib` — calling `session._release()` manually
- `Failed to add attachment to prompt: the current OS does not support attachment prompts`
- `Failed to add attachment to prompt: the Xcode version used to build this package doesn't include macOS 27 SDKs`
- `decorator is not a Generable type` — pre-PR-#10 `@fm.generable` misuse
- `Token counting requires macOS 26.4, iOS 26.4, or visionOS 26.4 or later.`
- `NSInvalidArgumentException` "please provide a format hint… to perform passthrough" — nil-outputSettings `AVAssetWriterInput`
- `NSURLErrorDomain error -1009` — offline path in an app that thought it was local-only
- `AttributeError: 'KerasTensor' object has no attribute 'type_spec'` — dnikit + Keras 3

## Recurring themes across all seven repos

1. **Specialization is the dominant cost on Core AI.** Cold ~32 s for a 4.59 GiB iPhone bundle;
   3.4 s for a 0.8B one. Cold prefill is 2.3× slower than warm. Every new input shape on a
   dynamic-shape graph re-specializes. Bucket your shapes; prewarm at full context; keep one
   session-long decoder.
2. **The stock upstream pipelined engine is limited** — 2 states, `input_ids`/`position_ids` only,
   no KV-trim/prefix-reuse, keeps generating past consumer break. Every serious consumer
   (`john-rocky/coreai-models`, Noema) carries patches or workarounds.
3. **Bundle folder names are load-bearing metadata**: `ios-ane/`, `ios-gpu/`, `gpu-pipelined/`,
   `macos/` each imply a different compute unit and reshape policy.
4. **Python is the second-class citizen everywhere.** apple-fm-sdk has no PCC and no feedback API;
   Core AI's own Python runtime bindings were "incomplete" as of 2026-06-09 (mlx2coreai commit).
5. **Nothing ships as a wheel.** apple-fm-sdk compiles Swift at pip-install time and needs Xcode.
6. **Community porting standards are stricter than Apple's own docs**: fp32-oracle teacher-forced
   top-1 parity + greedy rollout + Release-build measured tok/s + a device gate on real iOS 27
   hardware, with pinned upstream checkpoint revisions AND pinned HF bundle revisions.

---

# Source inventory (everything I actually read this session)

## GitHub API / `gh` reads

**apple/python-apple-fm-sdk**
- `gh repo view`, `gh release list`, `gh release view` × 5 tags, `gh api .../commits`
- `gh api .../git/trees/main?recursive=1` (full file tree)
- Issues (body + comments): #1, #2, #3, #4, #5, #6, #11, #12, #13, #16, #17
- PRs (body + file list): #7, #8, #9, #10, #14, #15, #18
- PR diffs read in full or part: `gh pr diff 9`, `gh pr diff 14`, `gh pr diff 15`
- Files: `README.md`, `build_backend.py`, `src/apple_fm_sdk/__init__.py`, `src/apple_fm_sdk/errors.py`

**apple/dnikit**
- `gh repo view`, `gh release list`, `gh api .../commits`, `README.md`
- Issues #2, #3; PR #4 (body + comments)

**1amageek/swift-lm**
- `gh repo view`, `gh api .../commits`, `gh api .../tags`
- Issue #1 (body + owner comment)
- `gh api .../commits/e956e56` (message + file list)
- `README.md` (read in full, ~400 lines)

**noemaai-labs/noema-ios**
- `gh repo view`, issue list, PR list
- Issues #5, #10, #11, #12, #13 (bodies + comments); PR #14 (body)
- `gh api .../git/trees/main?recursive=1` (filtered)
- Files: `README.md`, `Noema/AppleFoundationModelAvailability.swift` (full),
  `Noema/CoreAILLMClient.swift` (2,193 lines; read lines 1–620 in detail + full symbol index)

**lucasnewman/mlx2coreai**
- `gh repo view` (0 issues, 0 PRs), `gh api .../commits`, `gh api .../git/trees/main?recursive=1`
- Files: `README.md`, `pyproject.toml`, `docs/op_coverage.md` (full)

**john-rocky/coreai-model-zoo**
- `gh repo view`, issue list, PR list
- Issues #1, #2, #3, #4, #5 (bodies + comments)
- PRs #6, #7, #8, #9, #10 (bodies + comments)
- `gh pr diff 6` (partial: `conversion/recipes.toml`, `knowledge/nanbeige4.2-coreai-support.md`)
- `gh pr diff 7` (full: `knowledge/coreai-models-apple-overview.md`, 369 new lines)
- File: `CONTRIBUTING.md` (full)

**john-rocky/coreai-models**
- `gh repo view` (issues disabled), `gh api .../commits`, `gh api .../branches`
- File: `README.md`
- `gh api .../commits/{9e5b605d,627fec75,0fdf7107}` (messages + file lists)

## External URLs referenced *by* those sources (NOT fetched by me)
- https://huggingface.co/mlboydaisuke (maintainer's converted Core AI models)
- https://huggingface.co/ukint-vs/Nanbeige4.2-3B-CoreAI @ `5864ec7a…`
- https://huggingface.co/mlboydaisuke/Nanbeige4.1-3B-CoreAI (bundle-layout reference)
- https://github.com/john-rocky/coreai-kit (CoreAIKit catalog)
- https://github.com/john-rocky/coreai-models-community
- https://github.com/ZPVIP/apple-to-openai, https://github.com/Dennesssy/Apple-Intelligence-CLI
- https://github.com/yosun/TripoSplatWebGPU
- https://devicemark.github.io/

---

# Open questions / UNVERIFIED

1. **`fm` CLI surface.** @rxwei named `fm` and `fm serve` (Chat Completions endpoint). I verified
   nothing about its actual flags. The `fm respond <query> --model pcc` form is a *reporter's
   guess*. **Someone needs to document `fm --help`, `fm respond`, `fm serve` for real.**
2. **"macOS Golden Gate"** — Apple-internal codename used by an Apple engineer in issue #13.
   Maps to macOS 27? Unconfirmed.
3. **Is issue #6 (Xcode.app requirement) still failing on current `main`?** The check is still in
   `build_backend.py` at `main`, so presumably yes — but I did not run `pip install`.
4. **`prewarm()` in the Python SDK** — simonw quoted Swift `session.prewarm()`; nothing named
   `prewarm` appears in `__init__.py`'s `__all__`. Is there an unexported one?
5. **Adapters / `SystemLanguageModel(adapter:)`** — not present in the Python SDK's exports. Is
   Python adapter support planned? No issue asks.
6. **Is `session.py`'s docstring still showing `fm.SystemLanguageModel(temperature=…, top_p=…)`?**
   That was reported as impossible in issue #3; I didn't re-read `session.py`.
7. **`Origami.md`** in noema's vendored FoundationModels docs — what FM feature is "Origami"?
8. **llama.cpp `afmoe.cpp`** — "AFM MoE"? Which Apple model architecture does this implement?
9. **`mlx2coreai` + `coreai-core` b2** — does bumping the pin from `1.0.0b1` to `1.0.0b2` just work,
   or did the IR change? Nobody has filed an issue (the repo has zero).
10. **`COREAI_CHUNK_THRESHOLD`** — is this a documented Apple env var or a `coreai-models`
    (Apple's Swift package) internal? Noema `setenv`s it; I found no doc.
11. **`h18p` architecture-token vocabulary** — what are the other valid
    `xcrun coreai-build compile --architecture` values (h17p? h16?)? Only `h18p` is verified.
12. **`SpecializationOptions` full member list** — I verified `preferredComputeUnitKind`,
    `expectFrequentReshapes`, `.default`, and `Equatable`. There are almost certainly more.
13. **`ComputeUnitKind` full case list** — verified `.gpu`, `.neuralEngine`, and the static
    `availableKinds`. Is there `.cpu`? Presumably, unverified.
14. **`EngineOptions` full member list** — verified `variant:`, `kvCacheStrategy:` (with `.auto`),
    plus the fork's added `perTokenInputProvider` and `staticInputBuffers`.
15. **Whether the FD-leak fix (#18) has been released to PyPI.** As of the commit log, `main` is
    ahead of `v0.2.1` by exactly that commit + a version bump. No `v0.2.2` tag exists.
16. **`knowledge/evaluations-framework.md`** in coreai-model-zoo — cited by `CONTRIBUTING.md` but
    I did not read it. It is likely directly relevant to the Evaluations-framework agent.
17. **PR #7's claims about `apple/coreai-models`** are second-hand (unmerged PR, though
    maintainer-spot-checked). Defer to whichever agent reads `apple/coreai-models` directly.
