# apple/python-apple-fm-sdk — deep dive research notes

> Research session date: 2026-07-27. Everything below was read from the locally cloned repo at
> `/Volumes/ExtStor/FM and MLX and CoreAI/repos/apple__python-apple-fm-sdk` (depth-50 clone of
> `https://github.com/apple/python-apple-fm-sdk`, branch `main`, HEAD = `e868e60`).
> Nothing here is from memory. Line numbers refer to the files at that commit.
> Items I could not execute (no macOS 26 + Apple Intelligence + built bindings in this session) are
> flagged **UNVERIFIED** or **INFERRED**.

---

## 0. TL;DR / what this repo is

Python bindings (`pip install apple-fm-sdk`, import name `apple_fm_sdk`) around Apple's **Swift**
Foundation Models framework. It is a **three-layer sandwich**:

```
Python  (src/apple_fm_sdk/*.py, pure Python + ctypes)
   |
   |  ctypes, via a ctypesgen-generated module src/apple_fm_sdk/_ctypes_bindings.py
   |  (NOT checked into git — generated at build time from the C header)
   v
C ABI   (foundation-models-c/Sources/FoundationModelsCBindings/include/FoundationModels.h)
   |
   |  @_cdecl Swift functions
   v
Swift   (foundation-models-c/Sources/FoundationModelsCBindings/FoundationModelsCBindings.swift)
        -> import FoundationModels  (the real Apple framework)
```

The stated purpose (README.md:12) is **evaluating Swift Foundation Models app features from Python**
— batch inference, transcript analysis, schema parity checks — not shipping production Python apps.

Repo metadata:
- License: Apache-2.0 (`LICENSE.md`; every source file carries `Copyright (C) 2026 Apple Inc.`)
- `CODE_OF_CONDUCT.md` present. README.md:34: **"This project is not yet taking contributions. Stay tuned!"**
- Development Status classifier: `3 - Alpha` (pyproject.toml:17)

---

## 1. Versions, requirements, dependencies

### 1.1 `pyproject.toml` (verbatim, 74 lines)

```toml
[build-system]
requires = ["setuptools"]
build-backend = "build_backend"
backend-path = ["."]

[project]
name = "apple-fm-sdk"
version = "0.2.1"
description = "Python bindings for Apple's Foundation Models Swift framework"
readme = "README.md"
requires-python = ">=3.10"
license = "Apache-2.0"
authors = [{name = "Apple Inc."}]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Operating System :: MacOS",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
]
keywords = ["machine-learning", "artificial-intelligence", "apple", "foundation-models"]

dependencies = [
    "build",
    "setuptools>=75.3.2",
]

[dependency-groups]
dev = [
    "pytest",
    "pytest-asyncio",
    "pytest-timeout",
    "ruff>=0.14.5",
    "ctypesgen>=1.1.1",
    "psutil>=7.2.2",
    "twine>=6.2.0",
]
docs = [
    "sphinx>=7.0.0",
    "sphinx-book-theme>=1.0.0",
    "sphinx-autodoc-typehints>=1.25.0",
    "sphinx-copybutton>=0.5.2",
    "myst-parser>=2.0.0",
]

[tool.setuptools]
packages = ["apple_fm_sdk"]
package-dir = {"" = "src"}

[tool.setuptools.package-data]
apple_fm_sdk = ["lib/*.a", "lib/*.dylib"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
filterwarnings = ["default", "default::UserWarning"]
```

Notes:
- `asyncio_mode = "auto"` → every `async def test_*` runs under pytest-asyncio without a marker
  (though most tests also carry `@pytest.mark.asyncio` redundantly).
- Runtime deps are only `build` + `setuptools` — no numpy/pydantic. Everything else is stdlib
  (`ctypes`, `asyncio`, `threading`, `queue`, `dataclasses`, `json`, `enum`, `typing`, `uuid`).

### 1.2 Version-number mismatch (gotcha)

Three different version strings coexist:

| Location | Value |
|---|---|
| `pyproject.toml:8` | `version = "0.2.1"` |
| `src/apple_fm_sdk/__init__.py:62` | `__version__ = "0.1.0"` |
| `docs/source/conf.py:21` | `release = "1.0.0"` |

So `apple_fm_sdk.__version__` **lies**; use `importlib.metadata.version("apple-fm-sdk")` instead.

### 1.3 Stated platform requirements

README.md:25-30 and `docs/source/index.rst:23-30`:

- **macOS 26.0+**
- **Xcode 26.0+**, and you must open Xcode once to accept
  "the Xcode and Apple SDKs agreement"
- **Python 3.10+**
- **Apple Intelligence turned on** for a compatible Mac (https://support.apple.com/en-us/121115)

`docs/source/getting_started.rst:20` adds a tip: *"Make sure your Xcode version matches your macOS
version to avoid model compatibility issues."* and :110 *"Verify that your Xcode version matches your
macOS version exactly."*

Swift package platform floor (`foundation-models-c/Package.swift:13`):
```swift
platforms: [.macOS(.v26), .iOS(.v26), .visionOS(.v26)],
```
`// swift-tools-version: 6.2`, `cLanguageStandard: .c99`.

Feature-level OS gates discovered in Swift source:
- **Attachments / images**: `#if FM_HAS_MACOS_27_SDK` + `if #available(iOS 27.0, macOS 27.0,
  visionOS 27.0, watchOS 27.0, *)` (FoundationModelsCBindings.swift:33-47). i.e. **image prompts need
  the macOS 27 SDK at build time AND macOS 27 at runtime.**
- **Token counting**: `guard #available(macOS 26.4, iOS 26.4, visionOS 26.4, *)` — otherwise it throws
  an `NSError(domain: "TokenCount", code: -1)` with localized description
  `"Token counting requires macOS 26.4, iOS 26.4, or visionOS 26.4 or later."`
  (FoundationModelsCBindings.swift:177-185, 243, 261, 289, 307, 328).
  `FMSystemLanguageModelGetContextSize` (`model.contextSize`) is **not** gated — it is available on 26.0.

---

## 2. Build pipeline (`build_backend.py`, 320 lines) — a custom PEP 517 backend

`pyproject.toml` sets `build-backend = "build_backend"` with `backend-path = ["."]`, so
`build_backend.py` at repo root **is** the backend. It wraps `setuptools.build_meta`.

### 2.1 Hooks implemented

| Hook | Behaviour |
|---|---|
| `build_wheel(wheel_directory, config_settings, metadata_directory)` | runs `_build_c_bindings(...)` then `setuptools_backend.build_wheel(...)` |
| `build_editable(...)` | same, then `setuptools_backend.build_editable(...)` |
| `build_sdist(sdist_directory, config_settings)` | **explicitly does NOT compile** — "Build source distribution without compiling Swift/C code." |
| `get_requires_for_build_wheel` | `["setuptools>=64", "wheel", "ctypesgen"]` |
| `get_requires_for_build_editable` | `["setuptools>=64", "ctypesgen"]` |
| `get_requires_for_build_sdist` | `["setuptools>=64"]` |
| `prepare_metadata_for_build_editable` | delegates to setuptools |

### 2.2 `config_settings` knobs (undocumented elsewhere)

`build_wheel`/`build_editable` read three keys out of `config_settings`:

- `swift-build-config` — passed to `swift build -c <value>`. Default
  `DEFAULT_SWIFT_BUILD_CONFIGURATION = "release"` (build_backend.py:13).
- `override-library-name` — appended as an extra `-l <name>` to ctypesgen.
- `override-library-search-path` — appended as an extra `-L <path>` to ctypesgen.

Usage (INFERRED syntax from PEP 517 conventions; the repo never shows an invocation):
```bash
pip install . --config-settings swift-build-config=debug
python -m build --wheel -C swift-build-config=debug
```

### 2.3 Preflight checks the backend performs (each raises `SwiftToolingError`)

1. **macOS version** (build_backend.py:65-77): `platform.mac_ver()[0]`, major must be `>= 26`, else
   `"macOS version {v} found, but version 26.0 or higher is required. This package requires macOS 26.0+ to build the Swift bindings."`
2. **`swift` on PATH** (:80): `"No `swift` executable found in PATH. Is `swift` set up on your system?"`
3. **`xcode-select -p` must NOT contain `CommandLineTools`** (:96-101):
   `"The active developer directory is set to Command Line Tools (...), but a full Xcode installation is required. Please install Xcode. Then open Xcode at least once to accept the license agreement and install the Swift SDKs."`
4. **`xcodebuild` on PATH** (:108)
5. **`xcodebuild -version` major >= 26** — parsed with `re.search(r"Xcode\s+(\d+)\.(\d+)", ...)` (:122-134).
   If the error text contains `"command line tools instance"` it emits the fixup hint:
   `sudo xcode-select --switch /Applications/Xcode.app/Contents/Developer`

### 2.4 macOS 27 SDK detection → `-DFM_HAS_MACOS_27_SDK`

```python
def _macos_sdk_major_version() -> Optional[int]:
    """Major version of the active macOS SDK (e.g. 26, 27), or None if undetectable."""
    sdk_version = subprocess.run(
        ["xcrun", "--sdk", "macosx", "--show-sdk-version"], check=True,
        capture_output=True, text=True,
    ).stdout.strip()
    return int(sdk_version.split(".")[0])
```
(build_backend.py:43-54)

```python
    # `Attachment` (image support) only exists in the macOS 27+ SDK
    extra_swift_args = []
    sdk_major = _macos_sdk_major_version()
    if sdk_major is not None and sdk_major >= 27:
        extra_swift_args += ["-Xswiftc", "-DFM_HAS_MACOS_27_SDK"]
```
(build_backend.py:148-152)

**This is the single most important build-time gate: if you build with an Xcode whose macOS SDK is
26.x, image attachments are compiled out and every `ImageAttachment` raises
`ImagePromptError: ... the Xcode version used to build this package doesn't include macOS 27 SDKs`.**

### 2.5 The actual build commands run

```python
swiftPackageDir = Path("foundation-models-c").resolve()

subprocess.run(["swift", "build", "-c", swift_build_config, *extra_swift_args],
               check=True, cwd=str(swiftPackageDir), capture_output=True, text=True)

build_dir_string = subprocess.run(
    ["swift", "build", "-c", swift_build_config, "--show-bin-path"],
    check=True, cwd=str(swiftPackageDir), capture_output=True, text=True).stdout.strip()

libraryDirectory = (Path("src") / "apple_fm_sdk" / "lib").resolve()
if libraryDirectory.exists():
    shutil.rmtree(str(libraryDirectory))
shutil.copytree(build_dir, libraryDirectory)   # copies the WHOLE swift bin dir into the package

subprocess.run([
    "ctypesgen",
    str(swiftPackageDir / "Sources" / "FoundationModelsCBindings" / "include" / "FoundationModels.h"),
    "-L", "lib",                 # relative to the apple_fm_sdk package directory
    "-l", "FoundationModels",
    # + optional -L override-library-search-path, -l override-library-name
    "-o", "./src/apple_fm_sdk/_ctypes_bindings.py",
], check=True)
```
(build_backend.py:146-204)

### 2.6 ctypesgen post-processing (runtime-relative dylib lookup)

After ctypesgen runs, the backend rewrites the generated file so it finds the dylib next to itself:

```python
bindings_content = bindings_file.read_text()
if "import os" not in bindings_content:
    bindings_content = bindings_content.replace("import sys\n", "import sys\nimport os\n")
bindings_content = re.sub(
    r"add_library_search_dirs\(\[(.*?)\]\)",
    lambda m: _fix_library_search_dirs(m.group(1)),
    bindings_content,
)
bindings_file.write_text(bindings_content)
```
and `_fix_library_search_dirs` replaces the literal `'lib'` entry with
`os.path.join(os.path.dirname(__file__), 'lib')` (build_backend.py:20-40, 206-226).

### 2.7 What ships / what is generated

`MANIFEST.in` (21 lines):
```
include build_backend.py
recursive-include foundation-models-c/Sources *.swift *.h *.c
recursive-include foundation-models-c/Tests *.swift
include foundation-models-c/Package.swift
include foundation-models-c/Package.resolved
include foundation-models-c/*.md
recursive-include foundation-models-c *.modulemap
global-exclude _ctypes_bindings.py
global-exclude *.pyc
global-exclude *.pyo
global-exclude __pycache__
prune src/apple_fm_sdk/lib
```

So: the **sdist contains the Swift sources and no binaries**; the wheel contains
`apple_fm_sdk/lib/*.dylib|*.a` plus the generated `_ctypes_bindings.py`.
`.gitignore` ends with `src/apple_fm_sdk/_ctypes_bindings.py` and
`src/apple_fm_sdk/FoundationModelsBindings` — confirming both are build artifacts.

### 2.8 `bin/` scripts

| Script | What it does |
|---|---|
| `bin/build-distribution.sh` | `bash bin/clean-build-files.sh` then `python3 -m build --sdist --outdir dist` |
| `bin/clean-build-files.sh` | rm `foundation-models-c/.build`, `src/apple_fm_sdk/_ctypes_bindings.py`, `src/apple_fm_sdk/lib`, `build/`, `dist/`, `src/apple_fm_sdk.egg-info` |
| `bin/clean.sh` | rm `.venv` then runs `clean-build-files.sh` |
| `bin/install-git-hooks.sh` | symlinks `.git/hooks/pre-commit` -> `bin/git-pre-commit.sh` |
| `bin/git-pre-commit.sh` | `ruff format` then `swift format . --recursive --in-place` |
| `bin/verify-license-header.sh` | (230 lines) license-header linter |
| `bin/publish-docs.sh` | builds sphinx (`uv sync --group docs`, `make clean`, `make html`), copies `docs/build/html` with `cp -rL`, adds `.nojekyll`, force-replaces the `gh-pages` branch, commits `"Update documentation - $(date '+%Y-%m-%d %H:%M:%S')"`, pushes, returns to original branch |

Swift formatting config lives in `.swift-format` (2-space indent, `lineLength: 100`,
`lineBreakBeforeEachArgument: true`, `UseTripleSlashForDocumentationComments: true`, …).

### 2.9 Documented install flow

```bash
# from PyPI
pip install apple-fm-sdk

# from source (README.md:107-132)
git clone https://github.com/apple/python-apple-fm-sdk
cd python-apple-fm-sdk
uv venv
source .venv/bin/activate
uv sync
# after any change:
uv pip install -e .
pytest
```

Docs build:
```bash
cd docs
uv sync --group docs   # or: pip install -r requirements.txt
make html              # output in docs/build/html
make clean
# live reload:
uv pip install sphinx-autobuild && sphinx-autobuild source build/html
```

---

## 3. Public Python API surface

`src/apple_fm_sdk/__init__.py` `__all__` (verbatim, 41 names):

```python
__all__ = [
    "SystemLanguageModel", "LanguageModelSession",
    "Attachment", "ImageAttachment", "PromptComponent", "Prompt",
    "PromptError", "ImagePromptError",
    "Transcript",
    "SystemLanguageModelUseCase", "SystemLanguageModelGuardrails",
    "SystemLanguageModelUnavailableReason",
    "Tool",
    "FoundationModelsError", "GenerationError", "ExceededContextWindowSizeError",
    "AssetsUnavailableError", "GuardrailViolationError", "UnsupportedGuideError",
    "UnsupportedLanguageOrLocaleError", "InvalidGenerationSchemaError",
    "DecodingFailureError", "RateLimitedError", "ConcurrentRequestsError",
    "RefusalError", "ToolCallError", "GenerationErrorCode",
    "generable", "guide",
    "GenerationSchema", "GeneratedContent",
    "GenerationGuide", "GuideType",
    "GenerationOptions", "SamplingMode", "SamplingModeType",
    "GenerationID", "ConvertibleFromGeneratedContent", "ConvertibleToGeneratedContent",
    "Generable",
]
```

Module map:

| Module | Lines | Public contents |
|---|---|---|
| `core.py` | 399 | `SystemLanguageModel`, `SystemLanguageModelUseCase`, `SystemLanguageModelGuardrails`, `SystemLanguageModelUnavailableReason` |
| `session.py` | 908 | `LanguageModelSession` |
| `prompt.py` | 319 | `Attachment`, `ImageAttachment`, `PromptComponent`, `Prompt`, `PromptError`, `ImagePromptError`, `_composed_prompt_from_prompt` |
| `transcript.py` | 337 | `Transcript` |
| `tool.py` | 374 | `Tool` |
| `generable.py` | 357 | `GenerationID`, `GeneratedContent`, `ConvertibleFromGeneratedContent`, `ConvertibleToGeneratedContent`, `Generable` |
| `generable_utils.py` | 452 | `generable` decorator, `generation_schema`, `resolve_referenced_generables`, `create_partially_generated`, `GenerableDecoratorError` |
| `generation_schema.py` | 199 | `GenerationSchema` |
| `generation_property.py` | 137 | `Property` (**not exported from the package**) |
| `generation_guide.py` | 483 | `GuideType`, `GenerationGuide`, `guide()` |
| `generation_options.py` | 294 | `SamplingModeType`, `SamplingMode`, `GenerationOptions` |
| `errors.py` | 162 | all exception classes + `GenerationErrorCode` + `_status_code_to_exception` |
| `type_conversion.py` | 80 | `_python_type_to_string` (private) |
| `c_helpers.py` | 569 | `_ManagedObject`, `_register_handle`, `_unregister_handle`, `_safe_from_handle`, `_get_error_string`, the three ctypes callbacks, `StreamingCallback` |

Every module that touches native code does:
```python
try:
    from . import _ctypes_bindings as lib
except ImportError:
    raise ImportError(
        "Foundation Models C bindings not found. Please ensure _foundationmodels_ctypes.py is available."
    )
```
(the error message names a *stale* filename `_foundationmodels_ctypes.py` — the real file is
`_ctypes_bindings.py`.)

---

## 4. `SystemLanguageModel` (core.py)

### 4.1 Enums (IntEnum, values match the C enums exactly)

```python
class SystemLanguageModelUnavailableReason(IntEnum):
    APPLE_INTELLIGENCE_NOT_ENABLED = 0
    DEVICE_NOT_ELIGIBLE = 1
    MODEL_NOT_READY = 2
    UNKNOWN = 0xFF

class SystemLanguageModelUseCase(IntEnum):
    GENERAL = 0
    CONTENT_TAGGING = 1

class SystemLanguageModelGuardrails(IntEnum):
    DEFAULT = 0
    PERMISSIVE_CONTENT_TRANSFORMATIONS = 1
```
Swift mapping (FoundationModelsCBindings.swift:107-137): `.general` / `.contentTagging`,
`.default` / `.permissiveContentTransformations`. Unknown use-case values print
`"Warning: Unknown SystemLanguageModel use case \(c), defaulting to .general"` and fall back to
`.general` — tested in `tests/test_system_model.py::test_invalid_use_case`.

Note: the Swift `SystemLanguageModel.UseCase` API here exposes only `general` and `contentTagging` —
no other cases are bridged.

### 4.2 Constructor

```python
SystemLanguageModel(
    use_case: SystemLanguageModelUseCase = SystemLanguageModelUseCase.GENERAL,
    guardrails: SystemLanguageModelGuardrails = SystemLanguageModelGuardrails.DEFAULT,
    _ptr=None,
)
```
Calls `lib.FMSystemLanguageModelCreate(use_case.value, guardrails.value)`.
Both params are positional-or-keyword — `fm.SystemLanguageModel(fm.SystemLanguageModelUseCase.GENERAL,
fm.SystemLanguageModelGuardrails.DEFAULT)` is used in `tests/test_memory_stress.py`.

**There is no `temperature`/`top_p` on `SystemLanguageModel`** despite what
`session.py:87-90` docstring claims (`fm.SystemLanguageModel(temperature=0.7, top_p=0.9)` — that
snippet is wrong and would `TypeError`). Sampling lives in `GenerationOptions`.

### 4.3 `is_available()`

```python
def is_available(self) -> tuple[bool, Optional[SystemLanguageModelUnavailableReason]]
```
Returns `(True, None)` or `(False, reason_enum)`. Implementation:
```python
reason = c_int()
is_available = lib.FMSystemLanguageModelIsAvailable(self._ptr, ctypes.byref(reason))
```

### 4.4 `context_size` (property, added in commit db7afde)

```python
@property
def context_size(self) -> int:
    return int(lib.FMSystemLanguageModelGetContextSize(self._ptr))
```
Docstring: *"The context size is the total number of tokens (prompt, instructions, tools, and
response combined) that the model can process in a single session."*
Swift: `Int32(model.contextSize)`.

### 4.5 `token_count()` (async, added in commit db7afde)

```python
async def token_count(
    self,
    value: "Optional[Union[Prompt, GenerationSchema, Transcript, list[Tool]]]" = None,
    *,
    instructions: Optional[str] = None,
) -> int
```

Dispatch logic (core.py:346-399), in order:
1. `instructions=` given → `FMSystemLanguageModelTokenCountForInstructions`. Raises
   `ValueError("Provide either a value or instructions to token_count(), not both")` if `value` also given.
2. `value is None` → `ValueError("token_count() requires either a value or instructions")`
3. `isinstance(value, GenerationSchema)` → `FMSystemLanguageModelTokenCountForSchema(self._ptr, value._ptr, ...)`
4. `isinstance(value, Transcript)` → `FMSystemLanguageModelTokenCountForTranscript(self._ptr, value.session_ptr, ...)`
5. `isinstance(value, list) and all(isinstance(t, Tool) for t in value)` → `FMSystemLanguageModelTokenCountForTools`
6. otherwise treat as a prompt → `_composed_prompt_from_prompt(value)` → `FMSystemLanguageModelTokenCountForPrompt`

**Ordering gotcha**: an empty list `[]` passes `all(... for t in [])` (vacuously true) so
`await model.token_count([])` goes down the *tools* path with `tool_count=0`, not the prompt path.
A `list[str]` prompt correctly falls through to the prompt path.

Working examples straight out of `tests/test_token_count.py`:
```python
context_size = model.context_size                              # int, >= 1
await model.token_count("Hello")                               # prompt (str)
await model.token_count(["First line of text", "Second line of text"])   # list prompt
await model.token_count("こんにちは世界")                        # unicode ok
await model.token_count(instructions="You are a helpful assistant")
await model.token_count([SimpleCalculatorTool()])              # tools
await model.token_count([SimpleCalculatorTool(), GetUserInfoTool()])
await model.token_count(tester_schemas.Cat.generation_schema())  # schema
await model.token_count(session.transcript)                    # transcript
```
Determinism is asserted: same prompt → same count (`test_token_count_is_deterministic`).

Internal helper (core.py:267-291) — the canonical async-over-C pattern used throughout:
```python
async def _token_count(self, start_task) -> int:
    loop = asyncio.get_running_loop()
    future = loop.create_future()
    future_handle = _register_handle(future)
    task = start_task(future_handle, _token_count_callback)
    try:
        await future
    except asyncio.CancelledError:
        lib.FMTaskCancel(task)
        future.cancel()
        raise
    finally:
        _unregister_handle(future_handle)
        lib.FMRelease(task)
    return future.result()
```

---

## 5. `LanguageModelSession` (session.py)

### 5.1 Constructor

```python
LanguageModelSession(
    instructions: Optional[str] = None,
    model: Optional[SystemLanguageModel] = None,
    tools: Optional[list[Tool]] = None,
    _ptr=None,
)
```
`instructions` is the **first positional** parameter — `fm.LanguageModelSession("You are a helpful
assistant.", model=model)` is the dominant form in tests.

Body (session.py:135-169):
```python
self._request_lock = asyncio.Lock()
self._active_task = None
model_ptr = model._ptr if model else None
instructions_cstr = instructions.encode("utf-8") if instructions else None
tool_count = len(tools) if tools else 0
tool_refs = (ctypes.c_void_p * tool_count)()
for i, tool in enumerate(tools or []):
    tool_refs[i] = tool._ptr
ptr = lib.FMLanguageModelSessionCreateFromSystemLanguageModel(
    model_ptr, instructions_cstr, tool_refs, tool_count)
self.transcript = Transcript(ptr)
super().__init__(ptr)
```
Comment at :166: *"model object will be retained by LanguageModelSession in Swift so here we don't need to retain model"*.

Falsy `instructions` (i.e. `""`) is passed as `NULL` — `LanguageModelSession(instructions="")` is
identical to no instructions.

Session-level gotcha from the docstring (session.py:56-59):
> "Sessions use an internal lock to prevent concurrent requests. If you need to handle multiple
> requests simultaneously, create multiple session instances."

### 5.2 `from_transcript` classmethod

```python
@classmethod
def from_transcript(cls, transcript: Transcript,
                    model: Optional[SystemLanguageModel] = None,
                    tools: Optional[list[Tool]] = None) -> "LanguageModelSession"
```
```python
ptr = lib.FMLanguageModelSessionCreateFromTranscript(
    transcript.session_ptr, model_ptr, tool_refs, tool_count)
transcript._update_session_ptr(ptr)
session = cls(_ptr=ptr)
session.transcript = transcript
```
**Critical documented caveat** (session.py:191-194 and transcript.py:244-255):
> "Tool mentions loaded from a Transcript are historical only. You must **also** pass tool instances
> here if you want to allow the model to make new tool calls in this session."

Canonical usage (from the docstring + `tests/test_session.py`):
```python
with open("transcript.json") as f:
    transcript_dict = json.load(f)
transcript = await fm.Transcript.from_dict(transcript_dict)
session = fm.LanguageModelSession.from_transcript(transcript, tools=[CalculatorTool(), WeatherTool()])
response = await session.respond("Calculate 15 * 24")
```
Also: the transcript already carries the instructions, so you do not re-pass them
(`from_transcript` has no `instructions` parameter at all).

### 5.3 `is_responding` and `_reset_task_state`

```python
@property
def is_responding(self) -> bool:
    return lib.FMLanguageModelSessionIsResponding(self._ptr)

def _reset_task_state(self):
    lib.FMLanguageModelSessionReset(self._ptr)
```
`FMLanguageModelSessionReset` is a **no-op on the Swift side** — literally:
```swift
// For now, this is a no-op as the Swift LanguageModelSession
// should handle task cleanup internally. This function exists to provide
// a hook for future improvements and to signal intent in the Python layer.
_ = session.isResponding
```
(FoundationModelsCBindings.swift:433-444)

### 5.4 `respond()` — signature and overloads

Declared overloads (session.py:299-338) for type checkers:
```python
async def respond(self, prompt: Prompt, *, options: Optional[GenerationOptions] = None) -> str
async def respond(self, prompt: Prompt, *, generating: type[Generable], options=None) -> Type[Any]
async def respond(self, prompt: Prompt, *, generating: Generable, options=None) -> Type[Any]
async def respond(self, prompt: Prompt, *, schema: GenerationSchema, options=None) -> GeneratedContent
async def respond(self, prompt: Prompt, *, json_schema: dict, options=None) -> GeneratedContent
```
Actual runtime signature (session.py:340-348):
```python
async def respond(
    self,
    prompt: Prompt,
    generating: Optional[Union[Type[Generable], Generable]] = None,
    *,
    schema: Optional[GenerationSchema] = None,
    json_schema: Optional[dict] = None,
    options: Optional[GenerationOptions] = None,
) -> Union[str, Any, GeneratedContent]
```
→ `generating` is actually positional-or-keyword even though the overloads mark it keyword-only.

Dispatch body (session.py:458-489), in this exact order:
```python
if generating is not None and schema is not None:
    raise ValueError("Cannot specify both 'generating' and 'schema' arguments")

if generating is not None:
    if not isinstance(generating, Generable):
        raise ValueError(f"{generating.__name__} is not a Generable type. Use @generable decorator.")
    gen_schema = generating.generation_schema()
    generated_content = await self._respond_with_schema(prompt, gen_schema)   # <-- options NOT passed!
    return generating._from_generated_content(generated_content)

if schema is not None:
    return await self._respond_with_schema(prompt, schema, options)

if json_schema is not None:
    return await self._respond_with_schema_from_json(prompt, json_schema, options)

return await self._respond_basic(prompt, options)
```

🔴 **BUG (confirmed by reading, session.py:473): when you pass `generating=`, the `options=` argument
is silently dropped.** `_respond_with_schema(prompt, gen_schema)` is called with only two args, so
`options` defaults to `None`. Temperature / sampling / max-tokens have **no effect** on typed guided
generation. Workaround: use `schema=MyType.generation_schema()` + `options=...` and convert yourself
via `MyType._from_generated_content(result)`.

Return types:
- no constraint → `str`
- `generating=Cls` → an instance of `Cls`
- `schema=` or `json_schema=` → `GeneratedContent`

### 5.5 `_respond_basic` / `_respond_with_schema` / `_respond_with_schema_from_json`

All three share this shape (session.py:491-714):

```python
async with self._request_lock:                     # asyncio.Lock — serializes requests per session
    loop = asyncio.get_running_loop()
    future = loop.create_future()
    composed_prompt = self._composed_prompt_from_prompt(prompt=prompt)
    options_json = json.dumps(options.to_dict()).encode("utf-8") if options is not None else None
    future_handle = _register_handle(future)

    task = lib.FMLanguageModelSessionRespond(          # or ...RespondWithSchema / ...FromJSON
        self._ptr, composed_prompt, options_json, future_handle, _session_callback)
    self._active_task = task

    try:
        await future
    except asyncio.CancelledError as e:
        lib.FMTaskCancel(task)
        future.cancel()
        max_wait_time = 1.0      # Maximum 1 second wait
        poll_interval = 0.01     # Poll every 10ms
        elapsed = 0.0
        while self.is_responding and elapsed < max_wait_time:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
        self._reset_task_state()
        raise e
    except Exception as e:                # NOT present in _respond_basic — see gotchas
        self._reset_task_state()
        raise e
    finally:
        _unregister_handle(future_handle)
        lib.FMRelease(task)
        if composed_prompt:
            try:
                lib.FMRelease(composed_prompt)
            except Exception:
                pass
        self._active_task = None
    return future.result()
```

Differences between the three:
- `_respond_basic` has **no** generic `except Exception` clause (only `CancelledError`); the other
  two do and call `_reset_task_state()` on any error.
- `_respond_with_schema_from_json` does `json_schema_bytes = json.dumps(json_schema).encode("utf-8")`
  first — so a non-JSON-serializable dict raises `TypeError` from `json.dumps` *before* any native
  call (see `tests/test_error_handling.py::test_error_on_invalid_json_schema`, which asserts the word
  `"serializable"` is in the message).
- Passing a **string** as `json_schema` also "works" (`json.dumps("...")` produces a JSON string
  literal), and then Swift's `JSONDecoder().decode(GenerationSchema.self, ...)` fails → the test
  asserts a `fm.GenerationError` whose message contains `"format"`.

The `if composed_prompt: lib.FMRelease(composed_prompt)` blocks are **the entirety of commit
`e868e60`** (see §12).

### 5.6 `stream_response()` — text only, thread + queue based

```python
async def stream_response(self, prompt: Prompt,
                          options: Optional[GenerationOptions] = None) -> AsyncIterator
```
(`options` is positional-or-keyword here, not keyword-only.)

Semantics, verbatim from the docstring (session.py:722-735, 802-807):
> - Yields complete text **snapshots (not deltas)** as generation progresses
> - The final yield contains the complete response
> - Automatically updates the session transcript after completion
> - **Does not support guided generation (text responses only)**
> - Can be cancelled mid-stream using asyncio cancellation
> - "The session transcript is updated only after streaming completes"
> - "Breaking out of the async for loop early will properly clean up resources"

Implementation (`_stream_response_basic`, session.py:816-908):
- Creates a `StreamingCallback()` (thread-safe `queue.Queue` + `threading.Event`).
- Spawns a **daemon `threading.Thread`** running `_start_stream`, which builds the composed prompt,
  calls `lib.FMLanguageModelSessionStreamResponse(self._ptr, composed_prompt, options_json)`, stores
  the returned stream ptr in a 1-element list, then calls
  `lib.FMLanguageModelSessionResponseStreamIterate(stream_ptr, None, callback._callback)` (blocking).
- Main coroutine loops `callback.queue.get(timeout=0.1)`; `None` is the end-of-stream sentinel;
  on `queue.Empty` it checks `callback.completed.is_set()` and drains.
- If `stream_ptr` is falsy → `callback.error = FoundationModelsError("Failed to create response stream")`.
- `finally:` `stream_thread.join(timeout=2.0)` **before** `lib.FMRelease(stream_ptr)` with the comment:
  ```python
  # Ensure the stream thread completes before we exit
  # This prevents segfaults when breaking early from the stream
  ...
  # Now it's safe to release the stream pointer
  # This must happen after the thread completes to prevent segfaults
  ```

🔴 **`stream_response` does NOT acquire `self._request_lock`** — so a stream and a `respond()` can
race on the same session. And **it never releases `composed_prompt`** (see gotchas).

Working snippets:
```python
session = fm.LanguageModelSession()
async for chunk in session.stream_response("Tell me a story"):
    print(chunk, end="", flush=True)          # chunk is a full snapshot each time

options = fm.GenerationOptions(temperature=0.8,
                               sampling=fm.SamplingMode.random(top=50),
                               maximum_response_tokens=1000)
async for chunk in session.stream_response("Write a creative story", options=options):
    ...
```
Tests confirm `chunks[-1]` is the complete response (`tests/test_streaming.py:33`).

---

## 6. Prompts and image attachments (`prompt.py`)

### 6.1 Type aliases

```python
PromptComponent = Union[str, Attachment]
Prompt = Union[PromptComponent, list[PromptComponent]]
```

So a prompt is: a `str`, a single `Attachment`, or a `list` mixing both.

### 6.2 `_composed_prompt_from_prompt` (the only prompt builder)

```python
def _composed_prompt_from_prompt(prompt: "Prompt"):
    composed_prompt = lib.FMComposedPromptInitialize()

    def add_component(component):
        if isinstance(component, str):
            lib.FMComposedPromptAddText(composed_prompt, component.encode("utf-8"))
        elif isinstance(component, Attachment):
            component.add_to_composed_prompt(composed_prompt=composed_prompt)
        else:
            raise PromptError(
                f"Unsupported prompt component type {type(component)}, only str, Image, "
                "IdentifiedImage, and Attachment are supported")

    from collections.abc import Iterable
    if isinstance(prompt, Iterable) and not isinstance(prompt, str):
        for element in prompt:
            add_component(element)
    else:
        add_component(prompt)
    return composed_prompt
```
Gotchas: the `Iterable` check means **any** iterable is expanded — a tuple, a generator, even a
`dict` (which would iterate its keys). The error message still names `Image` / `IdentifiedImage`,
classes that **no longer exist** in the Python API (leftover from before commit `da32e98`).

### 6.3 `Attachment` / `ImageAttachment`

```python
class Attachment(ABC):
    @abstractmethod
    def add_to_composed_prompt(self, composed_prompt): ...

class ImageAttachment(Attachment):
    def __init__(self, path: Path, label: Optional[str] = None):
        if not path.is_file():
            raise ImagePromptError(
                f"Failed to add attachment to prompt: file does not exist at {path}")
        self._path = path
        self._label = label
```
`path` **must be a `pathlib.Path`** (calls `path.is_file()`); a plain `str` raises `AttributeError`.

`add_to_composed_prompt` (prompt.py:152-179):
```python
label_bytes = self._label.encode("utf-8") if self._label else None
error_reason = ctypes.c_int()
if not lib.FMComposedPromptAddAttachment(
        composed_prompt, str(self._path).encode("utf-8"), label_bytes, ctypes.byref(error_reason)):
    if error_reason.value == FMComposedPromptAddImageErrorUnsupportedOS:
        detail = "the current OS does not support attachment prompts"
    elif error_reason.value == FMComposedPromptAddImageErrorUnsupportedSDK:
        detail = "the Xcode version used to build this package doesn't include macOS 27 SDKs"
    else:
        detail = "an unknown error occurred while adding the attachment"
    raise ImagePromptError(f"Failed to add attachment to prompt: {detail}")
```

Swift side (FoundationModelsCBindings.swift:31-48):
```swift
public func add(attachmentFromPath imagePath: String, label: String?) throws {
    // `Attachment` only exists in the macOS 27+ SDK
    #if FM_HAS_MACOS_27_SDK
    if #available(iOS 27.0, macOS 27.0, visionOS 27.0, watchOS 27.0, *) {
      let url = URL(fileURLWithPath: imagePath)
      var attachment = Attachment(imageURL: url)
      if let label { attachment = attachment.label(label) }
      self.components.append(attachment)
      return
    } else { throw ComposedPromptError.unsupportedOS }
    #else
    throw ComposedPromptError.unsupportedSDK
    #endif
}
```
→ the underlying Swift API is `Attachment(imageURL: URL)` and `.label(_:)`.

### 6.4 Image prompt usage (verbatim from `tests/test_image_prompts.py`)

```python
from pathlib import Path
import apple_fm_sdk as fm

TEST_RESOURCES_DIR = Path(__file__).parent / "resources"
SIMPLE_IMAGE = TEST_RESOURCES_DIR / "test-simple-image.jpeg"
TEXT_DENSE_IMAGE = TEST_RESOURCES_DIR / "test-text-dense-image.png"

# text + image
image = fm.ImageAttachment(path=SIMPLE_IMAGE)
response = await session.respond(["What do you see in this image? Describe it briefly.", image])

# image only (single component, not a list)
response = await session.respond(fm.ImageAttachment(path=SIMPLE_IMAGE))

# list of images only
prompt: list[fm.PromptComponent] = [image1, image2]

# labelled attachments
image1 = fm.ImageAttachment(path=SIMPLE_IMAGE, label="image-a")
image2 = fm.ImageAttachment(path=TEXT_DENSE_IMAGE, label="image-b")
response = await session.respond([
    "I'm going to show you two labeled images.", image1, image2,
    "What do you see in image-a and image-b?"])

# guided generation with an image
result = await session.respond(["Analyze this image:", image], generating=ImageAnalysis)

# schema + image
generated_content = await session.respond(["Analyze this image:", image], schema=schema)
```
Every image test is wrapped in `try/except fm.ImagePromptError: pytest.skip(...)` — the test suite
is designed to degrade gracefully on macOS 26.

Test resource formats present: `.jpeg` and `.png`.

---

## 7. Guided generation: `@fm.generable`, `fm.guide`, `GenerationSchema`, `GeneratedContent`

### 7.1 `@generable` decorator (generable_utils.py)

Three call forms, all supported (overloads at generable_utils.py:36-52):
```python
@fm.generable                    # bare
@fm.generable()                  # empty parens
@fm.generable("description")     # with description
```
Detection is `if isinstance(arg, type): return _apply_generable_decorator(arg, description=None)`.

`_apply_generable_decorator` (generable_utils.py:147-251) does, in order:
1. `if not isinstance(cls, type)` → `GenerableDecoratorError` ("can only be applied to classes")
2. `if not hasattr(cls, "__annotations__") or not cls.__annotations__` → `GenerableDecoratorError`
   ("requires the class '<name>' to have type-annotated fields")
3. `if not hasattr(cls, "__dataclass_fields__"): cls = dataclass(cls)` — wraps in a dataclass if
   needed; failures re-raised as `GenerableDecoratorError` mentioning `field(default_factory=...)`
4. `get_type_hints(cls, localns={cls.__name__: cls}, include_extras=True)` — validation only; failures
   → `GenerableDecoratorError` ("Failed to resolve type hints for ...")
5. sets `cls._generable = True`, `cls._generable_description = description`
6. `cls.generation_schema = classmethod(generation_schema)`
7. `cls._from_generated_content = classmethod(_from_generated_content)`
8. `cls.generated_content = property(generated_content)`
9. `cls.PartiallyGenerated = create_partially_generated(cls)`

`GenerableDecoratorError` **subclasses `InvalidGenerationSchemaError`** which subclasses
`FoundationModelsError` — tests catch it as `fm.InvalidGenerationSchemaError`.

Ordering with `@dataclass` — both directions work (tests `test_decorating_dataclass_works` /
`test_decorating_dataclass_alt_works`):
```python
@dataclass
@fm.generable("A description of my generable")
class ValidGenerableDataClass: ...

@fm.generable
@dataclass
class ValidGenerableDataClassAlt: ...
```

`isinstance(MyClass, fm.Generable)` is **True for the class object itself** (`Generable` is a
`@runtime_checkable` Protocol, and the checks are on class attributes). This is exactly how
`respond()` validates (`if not isinstance(generating, Generable)`).

Directly subclassing `fm.Generable` is forbidden:
```python
def __init_subclass__(cls, **kwargs):
    super().__init_subclass__(**kwargs)
    raise TypeError(
        "Subclassing Protocol Generable is not allowed. "
        "Use the @fm.generable() decorator instead.")
```
(generable.py:342-347)

### 7.2 `generation_schema()` — how a Python class becomes a schema

```python
def generation_schema(cls_inner, description: Optional[str] = None) -> GenerationSchema:
    properties = []
    referenced_schemas: list[GenerationSchema] = []
    referenced_schema_names: set[str] = set()
    type_hints = get_type_hints(cls_inner, localns={cls_inner.__name__: cls_inner},
                                include_extras=True)   # namespace needed for self-referential types
    for field_name, field_info in cls_inner.__dataclass_fields__.items():
        field_type = type_hints.get(field_name, str)
        reference = resolve_referenced_generables(field_type, cls_inner.__name__)
        ...
        field_description = field_info.metadata.get("description")
        field_guides = field_info.metadata.get("guides", [])
        properties.append(Property(name=field_name, type_class=field_type,
                                   description=field_description, guides=field_guides))
    return GenerationSchema(type_class=cls_inner, description=description,
                            properties=properties, dynamic_nested_types=referenced_schemas)
```
(generable_utils.py:295-360)

🔴 **BUG: `cls._generable_description` (from `@generable("...")`) is never read.** `generation_schema`
takes `description=None` by default and nothing passes the stored description, so the emitted
`GenerationSchema.description` is always `None` for decorator-created types.
Verified with `grep -rn "_generable_description" src tests docs examples` → only two hits:
the Protocol declaration (`generable.py:340`) and the assignment (`generable_utils.py:227`).
Compare: the Swift-exported `cat.json` DOES carry `"description": "A description of a cute cat"` at
the root. So Python-built schemas lose the type-level description relative to Swift `@Generable(description:)`.
(Field-level descriptions from `fm.guide("...")` **do** flow through.)

`resolve_referenced_generables` (generable_utils.py:257-292) recurses into `get_args(field_type)` and
returns `[schema, *schema.dynamic_nested_types]`; it returns `None` if the referenced type name equals
the outer class name (self-reference short-circuit to avoid infinite recursion). Only the **first**
`get_args(...)` entry is followed:
```python
for inner_type in get_args(field_type):
    return resolve_referenced_generables(inner_type, outer_class_name)
```
— so for `Union[A, B]` only `A` is inspected. (Fine for `Optional[X]`/`list[X]`.)

Each call to `MyType.generation_schema()` **allocates a fresh native `GenerationSchemaBuilder`** —
there is no caching. `Tool.__init__` explicitly stores it (`self._arguments_schema = self.arguments_schema`)
with the comment *"This is necessary because arguments_schema is a property that returns a new object each time"*.

### 7.3 `Property` → C (generation_property.py:91-137)

```python
name_cstr = self.name.encode("utf-8")
desc_cstr = self.description.encode("utf-8") if self.description else None
type_name = _python_type_to_string(self.type_class)     # may raise TypeError
type_cstr = type_name.encode("utf-8")
is_optional = "Optional" in str(self.type_class)        # <-- string sniffing!
prop_ptr = lib.FMGenerationSchemaPropertyCreate(name_cstr, desc_cstr, type_cstr, is_optional)
for guide in self.guides:
    guide.convert_to_c(prop_ptr=prop_ptr)
lib.FMGenerationSchemaAddProperty(schema_ptr, prop_ptr)
lib.FMRelease(prop_ptr)   # Clean up property after adding
```

🔴 **`is_optional = "Optional" in str(self.type_class)` is fragile.** Verified locally:

| Python | `str(typing.Optional[int])` | `str(int \| None)` |
|---|---|---|
| 3.11 / 3.12 / 3.13 | `'typing.Optional[int]'` ✅ | `'int \| None'` ❌ |
| **3.14** | `'int \| None'` ❌ | `'int \| None'` ❌ |

(Measured with `python3.11/3.12/3.13/3.14 -c "from typing import Optional; print(str(Optional[int]))"`.)

Consequences:
- **Never write `x: str | None`** in a `@generable` class — on ≤3.13 it is not detected as optional
  and `_python_type_to_string` also falls through (`types.UnionType` has no `__origin__` and no
  `__name__` on 3.12), returning the literal string `'int | None'`, which Swift then treats as a
  *reference to a schema type named `int | None`* → schema build failure.
  Always use `typing.Optional[X]`.
- **On Python 3.14 even `Optional[X]` silently stops being marked optional** (all properties become
  required). Python 3.14 is not in the classifier list but *is* allowed by `requires-python = ">=3.10"`.
  **UNVERIFIED end-to-end** (needs a built SDK), but the string comparison is unambiguous.

### 7.4 `_python_type_to_string` (type_conversion.py) — the Python→schema type map

```python
str   -> "string"
int   -> "integer"
float -> "number"
bool  -> "boolean"
list  -> TypeError("Generic list types must specify an element type, for example, List[str]")
List[T] / list[T] -> f"array<{_python_type_to_string(T)}>"
Optional[T] / Union[T, None] -> _python_type_to_string(T)   # only when exactly one non-None arg
anything else -> getattr(python_type, "__name__", str(python_type))   # i.e. a schema reference by name
```
Docstring examples confirm: `_python_type_to_string(List[str]) == 'array<string>'`,
`_python_type_to_string(Optional[int]) == 'integer'`.

Swift then maps the type-name string back (FoundationModelsCBindings.swift:1586-1734):

| `typeName` string | Swift `DynamicGenerationSchema.Property` schema |
|---|---|
| `"string"` | `.init(type: String.self, guides: [GenerationGuide<String>])` |
| `"number"`, `"float"`, `"double"` | `.init(type: Double.self, guides: [GenerationGuide<Double>])` |
| `"integer"`, `"int"` | `.init(type: Int.self, guides: [GenerationGuide<Int>])` |
| `"boolean"`, `"bool"` | `.init(type: Bool.self)` — **bool has no guides** |
| `"array<string>"` | `.init(type: [String].self, guides: [GenerationGuide<[String]>])` |
| `"array<integer>"` | `.init(type: [Int].self, ...)` |
| `"array<number>"` | `.init(type: [Double].self, ...)` |
| `array<Foo>` (regex `/array<(\w+)>/`) | `.init(arrayOf: DynamicGenerationSchema(referenceTo: "Foo"), minimumElements:, maximumElements:)` — **only `count` / `maxItems` / `minItems` guides allowed; anything else throws `unsupportedGuide`** |
| any other non-empty name | `.init(referenceTo: typeName)` |

Note `array<Foo>` uses the regex `\w+`, so nested generics like `array<array<string>>` do **not** match
and fall back to "array of strings".

### 7.5 `fm.guide()` — signature and validation

```python
def guide(
    description: Optional[str] = None,
    *,
    anyOf: Optional[List[str]] = None,
    constant: Optional[str] = None,
    count: Optional[int] = None,
    element: Optional["GenerationGuide"] = None,
    max_items: Optional[int] = None,
    maximum: Optional[Union[int, float]] = None,
    min_items: Optional[int] = None,
    minimum: Optional[Union[int, float]] = None,
    range: Optional[tuple] = None,
    regex: Optional[str] = None,
) -> Any                        # actually returns dataclasses.field(metadata={...})
```
Returns `field(metadata={"description": description, "guides": [GenerationGuide, ...]})`.
Multiple constraints per call are allowed and appended in the declaration order above.

Client-side validation (raises `ValueError`):
- `anyOf` must be a `list` of `str`
- `constant` must be a `str`
- `count` must be a **positive** `int` (`count <= 0` rejected)
- `element` must be a `GenerationGuide` instance
- `max_items`, `min_items` must be **non-negative** `int`
- `maximum`, `minimum` must be numbers
- `range` must be a 2-tuple
- `regex` must be a `str`

🔴 Because `guide()` returns a `field()` with **no default**, a `@generable` class whose *first*
fields use `guide()` and later fields have defaults will hit normal dataclass ordering rules.

### 7.6 `GuideType` enum and `GenerationGuide` factories

```python
class GuideType(Enum):
    anyOf    = "enum"       # Serializes to "enum" in JSON schema
    constant = "constant"   # Represented by enum of 1 value
    count    = "count"
    element  = "element"    # Enforces a guide on the elements within the array.
    maxItems = "maxItems"   # called maximumCount in Swift
    maximum  = "maximum"
    minItems = "minItems"   # called minimumCount in Swift
    minimum  = "minimum"
    range    = "range"
    regex    = "regex"      # limited regex vocabulary -> serializes to "pattern"
```

Factory classmethods (all return `GenerationGuide`):
```python
fm.GenerationGuide.anyOf(values: List[str])
fm.GenerationGuide.constant(value: str)
fm.GenerationGuide.count(count: int)
fm.GenerationGuide.element(guide: GenerationGuide)
fm.GenerationGuide.max_items(value: int)
fm.GenerationGuide.maximum(value: Union[int, float])
fm.GenerationGuide.min_items(value: int)
fm.GenerationGuide.minimum(value: Union[int, float])
fm.GenerationGuide.range(range_tuple: tuple)         # note: takes a TUPLE, e.g. range((0, 120))
fm.GenerationGuide.regex(pattern: str)
```
(`.range` and `.max_items`/`.min_items` naming asymmetry: the enum members are `maxItems`/`minItems`
but the factory methods are snake_case `max_items`/`min_items`.)

`convert_to_c` (generation_guide.py:244-335): unwraps `element` guides by replacing the guide type with
the inner guide's type and setting `wrapped = True`; `constant` is implemented as
`anyOf([value])`; `anyOf` builds a `(POINTER(c_char) * n)` array of `create_string_buffer`s.

### 7.7 Guide → type compatibility matrix (extracted from `tests/test_guides.py:560-811`)

These combinations are **asserted to raise `fm.UnsupportedGuideError`** (raised at `respond()` time,
when Swift builds the schema — NOT at decoration time):

| Property type | Guides that FAIL |
|---|---|
| `str` | `minimum`, `maximum`, `range`, `count`, `min_items`, `max_items` |
| `int` | `anyOf`, `regex`, `count`, `min_items`, `max_items` |
| `float` | `anyOf`, `regex`, `count`, `min_items`, `max_items` |
| `List[int]` | `anyOf`, `regex`, `minimum`, `maximum`, `range` |
| `List[float]` | `anyOf`, `regex`, `minimum`, `maximum`, `range` |
| `List[str]` | `regex`, `minimum`, `maximum`, `range` — **but `anyOf` DOES work** (see comment: *"anyOf *does* work on array<string>, so it's not included here"*) |
| `bool` | (no guides at all — Swift maps bool with `schema: .init(type: Bool.self)` and ignores guides) |
| `List[Foo]` (references) | anything other than `count` / `min_items` / `max_items` → *"Unsupported guide for array of a referenced Generable type"* |

Guides that **work** (from the passing tests in the same file):
- `str`: `anyOf`, `constant`, `regex`
- `int` / `float`: `minimum`, `maximum`, `range`
- `List[str]` / `List[int]` / `List[float]`: `count`, `min_items`, `max_items`, `element=<inner guide>`
- `List[str]`: `anyOf` (becomes `GenerationGuide.element(.anyOf(...))` in Swift)

`element=` examples that pass:
```python
ratings:    List[int]   = fm.guide("Product ratings", element=fm.GenerationGuide.range((1, 5)))
prices:     List[float] = fm.guide("Historical prices", element=fm.GenerationGuide.minimum(0.01))
categories: List[str]   = fm.guide("Product categories",
                                   element=fm.GenerationGuide.anyOf(["tech", "home", "sports"]))
```

Swift-side guide resolvers (`resolveStringGuides`, `resolveArrayStringGuides`, `resolveDoubleGuides`,
`resolveIntGuides`, `resolveIntArrayGuides`, `resolveDoubleArrayGuides`) map to real
`FoundationModels.GenerationGuide` cases:
`.anyOf`, `.pattern(Regex(pattern))`, `.count`, `.maximumCount`, `.minimumCount`, `.element`,
`.range(min...max)`, `.maximum`, `.minimum`.

Regex caveat (docs/source/guided_generation.rst:111-112):
> "Note that the `SystemLanguageModel` only supports simple regex patterns like `\d+` for digits or
> `\w+` for word characters."
`tests/test_guides.py` uses only `r"\w"` and `r"\d+"` in *live* tests.
`generation_guide.py` docstrings show the odd form `regex=r"#/[a-zA-Z]+/#"` (Swift regex-literal
syntax leaking into a Python docstring) — inconsistent with the working tests.

### 7.8 `GenerationSchema`

```python
GenerationSchema(
    type_class: Type,
    description: Optional[str] = None,
    properties: Optional[List[Property]] = None,
    dynamic_nested_types: List["GenerationSchema"] = [],   # mutable default!
    _ptr=None,
)
```
Native init:
```python
name_cstr = type_class.__name__.encode("utf-8")
desc_cstr = description.encode("utf-8") if description else None
ptr = lib.FMGenerationSchemaCreate(name_cstr, desc_cstr)
for refType in self.dynamic_nested_types:
    lib.FMGenerationSchemaAddReferenceSchema(ptr, refType._ptr)
for property in self.properties:
    property.convert_to_c(schema_ptr=ptr)
```
Docstring says: *"Do not instantiate GenerationSchema directly. Use the `generable` decorator ... or
load in a json schema from your Swift app instead."*

`to_dict() -> dict`: calls `FMGenerationSchemaGetJSONString(ptr, &errCode, &errDesc)`. On the Swift
side this is literally `try builder.buildSchema().debugDescription` — i.e. **`GenerationSchema.debugDescription`
is the JSON-Schema serialization**. On failure it raises via `_status_code_to_exception(...)` with
`"Failed to serialize GenerationSchema: <desc>"`; empty string → `ValueError`.

`schema.type_class` and `schema.description` are readable Python attributes. `nested_schemas` is
declared as a class attribute but unused; the real one is `dynamic_nested_types`.

### 7.9 `GeneratedContent`

```python
GeneratedContent(content_dict: Optional[Dict] = None,
                 id: Optional[GenerationID] = None,
                 _ptr=None)
```
- With `_ptr`: calls `FMGeneratedContentGetJSONString(_ptr)`, `json.loads` into `_content_dict`.
- With `content_dict`: `json.dumps(content_dict).encode("utf-8")` → `FMGeneratedContentCreateFromJSON`
  with out-params `error_code: c_int32`, `error_description: POINTER(c_char)`.

Methods / properties:
```python
@classmethod from_json(cls, json_str: str) -> "GeneratedContent"
to_json(self) -> str                    # uses FMGeneratedContentGetJSONString, falls back to json.dumps
value(self, type_class: Optional[Type] = None, for_property: Optional[str] = None) -> Any
@property is_complete(self) -> bool     # FMGeneratedContentIsComplete
.id -> GenerationID   (uuid4 wrapper: __str__, __eq__, __hash__)
._content_dict -> dict  (private but widely used in tests)
```

`value()` behaviour:
- `for_property=None` → the whole `_content_dict`
- otherwise `self._content_dict.get(for_property)` → **missing key returns `None`, no exception**
  (asserted in `tests/test_error_handling.py:67-68`: `contents.value(int, "invalid_key") is None`)
- If `type_class` is given, `_unpack_nested_generables(type_class, raw_value, for_property)` runs:
  - `isinstance(type_class, Generable)` → wraps raw value into a new `GeneratedContent` and calls
    `type_class._from_generated_content(content)`
  - `list[T]` → recurses per element; `None` → `[]`; non-list → `TypeError(f"Expected list for property '{p}', got {type}")`
  - `Optional[T]` → `None` stays `None`, else recurse
  - otherwise returns the raw value untouched (so `value(str, ...)` does **not** coerce)

There is a `_convert_value(value_str, type_class)` helper with string→int/float/bool/list coercion
and delimiter-splitting fallbacks, but **it is never called** from `value()` — dead code at
generable.py:175-226.

Both call forms are used in the wild:
```python
args.value(str, for_property="operation")     # keyword
contents.value(int, "invalid_key")            # positional
generated_content.value(List[str], for_property="colors")
generated_content.value(dict, for_property="featuredHedgehog")
```

### 7.10 `PartiallyGenerated`

`create_partially_generated(cls)` builds a companion dataclass named `f"{cls.__name__}PartiallyGenerated"`
where every field is `Optional[...]` with `default=None`, plus an `id: GenerationID = field(default_factory=GenerationID)`.
It bases on `ConvertibleFromGeneratedContent` and gets `_from_generated_content = classmethod(partial_from_generated_content)`.

**It is created but never used** — `stream_response` yields plain `str` snapshots; nothing in the SDK
ever constructs a `PartiallyGenerated`. This is the Python analogue of Swift's `Response.Partial<T>`
plumbing, currently unwired.

### 7.11 Round-trip: instance → content

```python
@property
def generated_content(self) -> GeneratedContent:
    content_dict = {f: getattr(self, f) for f in self.__dataclass_fields__}
    return GeneratedContent(content_dict)
```

### 7.12 Full worked example (README.md:78-101, verbatim)

```python
import apple_fm_sdk as fm

@fm.generable # This decorator signals this type be generated by a model
class Cat:
    name: str
    age:int = fm.guide("Age in years", range=(0, 20))

async def generate_cat():
    model = fm.SystemLanguageModel()
    is_available, reason = model.is_available()
    if is_available:
        session = fm.LanguageModelSession()
        cat = await session.respond("Generate an adorable rescue cat", generating=Cat)
        print(f"Model response: {cat}")
    else:
        print(f"Foundation Models not available: {reason}")
```

### 7.13 Swift ↔ Python schema parity fixtures

`tests/tester_schemas/schemas.swift` and `tests/tester_schemas/schemas.py` are **the same 7 types
expressed in both languages** — the single best reference for translating `@Generable`/`@Guide` to
`@fm.generable`/`fm.guide`. Header comment (schemas.py:7-9):
> "These are the exact same schemas as in tests/tester_schemas/schemas.swift, but expressed in Python
> syntax. They are used to test schema generation and parsing and ensure parity between the Swift and
> Python schemas."

Side-by-side (Hedgehog):

```swift
@Generable
struct Hedgehog {
  @Guide(description: "A cute old-timey name")           var name: String
  @Guide(description: "The hedgehog's age", .range(0...8)) var age: Int
  @Guide(description: "The hedgehog's favorite food", .anyOf(["carrot", "turnip", "leek"]))
  var favoriteFood: String
  @Guide(.constant("a hedge"))                            var home: String
  @Guide(description: "The hedgehog's hobbies", .count(3)) var hobbies: [String]
}
```
```python
@fm.generable()
class Hedgehog:
    name: str = fm.guide(description="A cute old-timey name")
    age: Age = fm.guide(description="The hedgehog's age, at most 8 years")
    favoriteFood: str = fm.guide(description="The hedgehog's favorite food",
                                 anyOf=["carrot", "turnip", "leek"])
    home: str = fm.guide(constant="a hedge")
    hobbies: list[str] = fm.guide(description="The hedgehog's hobbies", count=3)
```
(note: `description=` is a keyword here even though it is the first positional parameter of `guide()`;
also the Python `Hedgehog.age` is a nested `Age` generable while the Swift one is `Int` — the fixtures
are *not* byte-identical.)

Self-referential + optional example:
```python
@fm.generable()
class Person:
    age: Optional[int] = fm.guide(range=(18, 100))
    children: List["Person"] = fm.guide(description="The person's children", max_items=3)
    name: str = fm.guide(description="The person's name")
```
The forward reference `"Person"` works because `generation_schema` passes
`localns={cls_inner.__name__: cls_inner}` to `get_type_hints`.

Swift-exported JSON Schema shape (from `tests/tester_schemas/person.json`) — this is the exact format
you feed to `json_schema=`:
```json
{
  "additionalProperties": false,
  "properties": {
    "age":      { "description": "The person's age", "maximum": 100, "minimum": 18, "type": "integer" },
    "children": { "description": "The person's children", "items": { "$ref": "#" },
                  "maxItems": 3, "type": "array" },
    "name":     { "description": "The person's name", "type": "string" }
  },
  "required": ["children", "name"],
  "title": "Person",
  "type": "object",
  "x-order": ["age", "children", "name"]
}
```
Key observations about the Foundation Models JSON Schema dialect:
- `"title"` = type name; `"x-order"` = declaration order of properties (**custom extension**)
- `"additionalProperties": false` always
- optional properties are simply **absent from `required`** (see `newsletter.json`: only
  `["title", "topic"]` are required)
- nested types live under `"$defs"` and are referenced with `"$ref": "#/$defs/Age"`
- self-reference at the root uses `"$ref": "#"`; inside `$defs` it's `"$ref": "#/$defs/Person"`
- guides serialize as standard JSON Schema keywords: `enum` (anyOf & constant),
  `minimum`/`maximum`, `minItems`/`maxItems`, `pattern` (regex)

### 7.14 Using a raw JSON schema

```python
import json, apple_fm_sdk as fm
with open("tests/tester_schemas/hedgehog.json") as f:
    schema = json.load(f)
session = fm.LanguageModelSession(model=model)
generated_content = await session.respond("Generate a very old hedgehog who likes to dance",
                                          json_schema=schema)          # -> GeneratedContent
name = generated_content.value(str, for_property="name")
```
Swift decodes it with `JSONDecoder().decode(GenerationSchema.self, from: Data(jsonSchemaString.utf8))`.
`docs/source/api/errors.rst` documents exactly this as the way to validate a schema by hand in Swift.

Swift export side (docs/source/guided_generation.rst:246-248):
```swift
let schema = ProductReview.generationSchema
let jsonData = try JSONEncoder().encode(schema)
try jsonData.write(to: URL(fileURLWithPath: "schema.json"))
```

`tests/test_json_guided_generation.py` exercises 7 fixtures and documents what each covers:
`age.json` (basic ints, strict), `cat.json` ($defs/$ref), `hedgehog.json` (min/max, enum, arrays with
size limits), `person.json` (recursive `$ref: "#"`, optional props, maxItems), `shelter.json`
(arrays of complex objects, multi-level $defs), `petClub.json` (multiple entity types),
`newsletter.json` (optional complex objects/arrays).
A notable assertion: with `person.json`'s `maxItems: 3` and a prompt asking for 5 children,
`len(children) == 3` — **schema constraints beat the prompt**.

---

## 8. Tools (`tool.py`)

### 8.1 Contract

```python
class Tool(_ManagedObject, ABC):
    name: str            # class attribute, required
    description: str     # class attribute, required

    @property
    @abstractmethod
    def arguments_schema(self) -> GenerationSchema: ...

    @abstractmethod
    async def call(self, args: GeneratedContent) -> str: ...
```

`_verify_subclass_()` runs first in `__init__` (tool.py:356-374):
```python
assert hasattr(self, "name"), "Tool subclass must have a 'name' property."
assert hasattr(self, "description"), "Tool subclass must have a 'description' property."
assert hasattr(self, "arguments_schema"), "Tool subclass must have an 'arguments_schema' property."
assert hasattr(self, "call"), "Tool subclass must implement the 'call' method."
if not isinstance(self.name, str): raise TypeError("Tool name must be a string.")
if not isinstance(self.description, str): raise TypeError("Tool description must be a string.")
if not isinstance(self.arguments_schema, GenerationSchema):
    raise TypeError("Tool arguments_schema must be a GenerationSchema instance.")
if not asyncio.iscoroutinefunction(self.call):
    raise TypeError("Tool call method must be an async function.")
```
Note these are bare `assert`s → **disabled under `python -O`**.

### 8.2 Canonical tool (from `docs/source/tools.rst`, with a nested `Arguments` class)

```python
import apple_fm_sdk as fm

class WeatherTool(fm.Tool):
    name = "WeatherTool"
    description = "Provides weather information for a given location and units."

    @fm.generable("Weather query parameters")
    class Arguments:
        location: str = fm.guide("City name")
        units: str = fm.guide("Temperature units", anyOf=["celsius", "fahrenheit"])

    @property
    def arguments_schema(self) -> fm.GenerationSchema:
        return self.Arguments.generation_schema()

    async def call(self, args: fm.GeneratedContent) -> str:
        location = args.value(str, for_property="location")
        units = args.value(str, for_property="units")
        temp = 72 if units == "fahrenheit" else 22
        return f"The weather in {location} is {temp}°{units[0].upper()}"

session = fm.LanguageModelSession(
    instructions="You are a helpful assistant with access to tools.",
    tools=[WeatherTool()])
response = await session.respond("What's the weather like in Taipei?")
```

Alternative (module-level params class) — the pattern used by every test tool
(`tests/tester_tools/tester_tools.py`):
```python
@fm.generable("Calculator parameters")
class CalculatorParams:
    operation: str = fm.guide("The operation to perform",
                              anyOf=["add", "subtract", "multiply", "divide"])
    a: float = fm.guide("First number")
    b: float = fm.guide("Second number")

class SimpleCalculatorTool(fm.Tool):
    name = "simple_calculator"
    description = "Perform basic arithmetic operations"

    @property
    def arguments_schema(self) -> fm.GenerationSchema:
        return CalculatorParams.generation_schema()

    async def call(self, args: fm.GeneratedContent) -> str:
        operation = args.value(str, for_property="operation")
        a = args.value(float, for_property="a")
        b = args.value(float, for_property="b")
        ...
        return f"The result of {a} {operation} {b} is {result}"
```

Tools can be invoked **directly** in tests (no model needed):
```python
calc_tool = SimpleCalculatorTool()
args = fm.GeneratedContent(content_dict={"operation": "add", "a": 5.0, "b": 3.0})
result = await calc_tool.call(args)          # "The result of 5.0 add 3.0 is 8.0"
```

### 8.3 The tool callback bridge (the trickiest part of the SDK)

`Tool.__init__` (tool.py:245-354):
```python
CallbackType = ctypes.CFUNCTYPE(ctypes.c_void_p, lib.FMGeneratedContentRef, ctypes.c_uint)

def _c_callback_impl(content_ref, call_id):
    generated_content = GeneratedContent(_ptr=content_ref)   # Swift passRetained -> Python owns it

    async def _run_async_callable():
        try:
            result = await self._async_callable(generated_content)
            if not isinstance(result, str):
                result = str(result)
            lib.FMBridgedToolFinishCall(self._ptr, call_id, result.encode("utf-8"))
        except Exception as e:
            error_msg = f"Tool error: {str(e)}"
            lib.FMBridgedToolFinishCall(self._ptr, call_id, error_msg.encode("utf-8"))

    try:
        loop = asyncio.get_running_loop()   # only to detect whether one exists
        asyncio.create_task(_run_async_callable())
    except RuntimeError:
        # No running loop - create a new thread with event loop
        def _run_in_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(_run_async_callable())
            finally:
                loop.close()
        threading.Thread(target=_run_in_thread, daemon=True).start()

self._c_callback = CallbackType(_c_callback_impl)   # kept alive on self
self._ptr = None                                    # so __del__ is safe if create fails
self._arguments_schema = self.arguments_schema      # keep schema alive across FMBridgedToolCreate
error_code = ctypes.c_int(); error_description = ctypes.POINTER(ctypes.c_char)()
ptr = lib.FMBridgedToolCreate(self.name.encode(), self.description.encode(),
                              self._arguments_schema._ptr, self._c_callback,
                              ctypes.byref(error_code), ctypes.byref(error_description))
if not ptr:
    raise _status_code_to_exception(err_code or error_code.value, "Failed to create bridged tool: ...")
super().__init__(ptr)
```

Important behavioural notes:
- **Tool exceptions never propagate to Python callers of `respond()`.** They are stringified as
  `"Tool error: <msg>"` and handed back to the *model* as the tool's output. The test at
  `tests/test_tool.py:150-161` confirms the model then talks about the error in prose.
  `fm.ToolCallError` exists in the public API but the Python layer **never raises it**
  (`grep` shows only `errors.py` and `__init__.py` mention it) — the `docs/source/tools.rst`
  `except fm.ToolCallError` example is aspirational.
- The Swift side blocks on a `withCheckedThrowingContinuation` keyed by an atomic `callId`
  (`BridgedTool.call`, FoundationModelsCBindings.swift:1766-1775), resolved by
  `FMBridgedToolFinishCall`. If your `call()` never returns (or the thread dies), the Swift
  continuation is never resumed → the session hangs. `tests/test_tool.py` wraps the parallel-tool
  test in `asyncio.wait_for(..., timeout=30.0)` and fails with
  *"Session response timed out - possible infinite tool calling loop or model issue"*.
- `_pending_calls` / `_call_lock` are initialised in `__init__` but never used (dead state).
- `asyncio.create_task(...)` is scheduled on whatever loop happens to be running **on the callback
  thread**. Since the Swift callback fires from a `Task.detached` (not the Python main thread), the
  `RuntimeError` branch (new thread + new event loop) is the likely path — **UNVERIFIED**.
- The C callback type returns `ctypes.c_void_p` while the header declares `void (*)(...)`; the code
  comment explains: *"UNCHECKED(None) in the bindings returns ctypes.c_void_p"*.

### 8.4 Tools + tokens + transcripts

- `await model.token_count([tool_a, tool_b])` counts the tool definitions.
- Tool definitions appear in the transcript's `instructions` entry under `"tools"`, in
  OpenAI-ish `{"type": "function", "function": {"name", "description", "parameters"}}` shape —
  see `tests/tester_schemas/test_transcript_full.json`.

---

## 9. `Transcript` (transcript.py)

`Transcript` is **not** a `_ManagedObject`. It holds `self.session_ptr` — the pointer of the
`LanguageModelSession` that owns it:

```python
def __init__(self, _ptr):
    # A transcript doesn't get it's own pointer, it uses the session's pointer
    self.session_ptr = _ptr
```

### 9.1 API

```python
async def to_dict(self) -> dict            # FMLanguageModelSessionGetTranscriptJSONString
@classmethod async def from_dict(cls, dict: dict) -> "Transcript"   # FMTranscriptCreateFromJSONString
def _update_session_ptr(self, new_ptr)     # internal
```
`to_dict()` and `from_dict()` are `async` even though **neither awaits anything** — they are
synchronous native calls wearing an `async def`. You must still `await` them.

`from_dict` calls `lib.FMTranscriptCreateFromJSONString(json.dumps(dict), ...)` — passing a Python
`str` (not `bytes`); this works only because ctypesgen wraps `char*` params in its `String` helper
type. Swift creates a whole new `LanguageModelSession(transcript:)` just to hold the transcript:
```swift
let transcript = try JSONDecoder().decode(Transcript.self, from: Data(jsonStr.utf8))
let session = LanguageModelSession(transcript: transcript)
return FMLanguageModelSessionRef(Unmanaged.passRetained(session).toOpaque())
```
**That retained session pointer is never released by Python** (see gotchas).

Decode failures set `outErrorCode = StatusCode.decodingFailure.rawValue (6)` →
`fm.DecodingFailureError`.

### 9.2 Transcript JSON format (documented in transcript.py:27-56, confirmed by fixtures)

```
{
  "version": 1,
  "type": "FoundationModels.Transcript",
  "transcript": { "entries": [ ... ] }
}
```
Each entry: `id` (UUID string), `role` ∈ `{"instructions", "user", "response", "tool"}`,
`contents` (array of `{type, id, ...}`).

Role-specific fields:
- `instructions`: `tools` (array of function definitions), `contents` (text)
- `user`: `contents`, `options` (`{}` in fixtures), `responseFormat`
  (`{"type": "jsonSchema", "jsonSchema": {"schema": {...}, "name": "Recipe"}}`)
- `response`: `toolCalls` (`[{name, arguments (JSON string), id}]`), `contents`, `assets`
- `tool`: `toolName`, `toolCallID`, `contents`

Content object types seen: `"text"` (`{"type":"text","text":..., "id":...}`) and `"structure"`
(`{"type":"structure","structure":{"source":"Recipe","content":{...}},"id":"0"}`).

`assets` values look like real model asset IDs:
```
"com.apple.fm.language.instruct_3b.fm_api_generic"
"com.apple.fm.language.instruct_3b.fm_api_generic.draft"
"com.apple.fm.language.instruct_3b.tokenizer"
```
→ the on-device model is a **3B instruct** model with a **draft** model (speculative decoding) and a
tokenizer asset. (Observed in fixture data, not documented prose.)

When transcripts update (transcript.py:58-64, verbatim):
> - After each `respond()` call completes successfully
> - After each `stream_response()` completes
> - After tool invocations are processed
> - **NOT** during streaming (only after completion)
> - **NOT** if a request fails or is cancelled

### 9.3 Round trip

```python
session = fm.LanguageModelSession()
await session.respond("Hello!")
transcript = await session.transcript.to_dict()
with open("session.json", "w") as f:
    json.dump(transcript, f, indent=2)

# later...
with open("session.json") as f:
    d = json.load(f)
t = await fm.Transcript.from_dict(d)
session2 = fm.LanguageModelSession.from_transcript(t, tools=[MyTool()])
```

### 9.4 Swift-side export snippet (docs/source/evaluation.rst:21-33)

```swift
import FoundationModels
let transcript = session.transcript
if let jsonData = try? JSONEncoder().encode(transcript),
   let jsonString = String(data: jsonData, encoding: .utf8) {
    try? jsonString.write(to: transcriptURL, atomically: true, encoding: .utf8)
}
```

### 9.5 `examples/transcript_processing.py` (350 lines)

Pure-Python transcript analytics — no SDK import at all. Useful shapes:
```python
def extract_text_from_contents(contents):
    for content in contents:
        if content.get("type") == "text":         text_parts.append(content.get("text", ""))
        elif content.get("type") == "structure":  text_parts.append(json.dumps(
                                                      content.get("structure", {}).get("content", {})))

entries = transcript.get("transcript", {}).get("entries", [])
instructions_entries = [e for e in entries if e.get("role") == "instructions"]
tool_calls = [tc for e in response_entries if "toolCalls" in e for tc in e["toolCalls"]]
has_structured_output = any("responseFormat" in e for e in user_entries)
```
It reads `tests/tester_schemas/test_transcript_full.json` by relative path and writes
`transcript_analyses.jsonl`.

---

## 10. `GenerationOptions` & `SamplingMode`

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

    @classmethod def greedy(cls) -> "SamplingMode"
    @classmethod def random(cls, top=None, probability_threshold=None, seed=None) -> "SamplingMode"

@dataclass
class GenerationOptions:
    sampling: Optional[SamplingMode] = None
    temperature: Optional[float] = None
    maximum_response_tokens: Optional[int] = None
```

Validation (`ValueError` messages are matched by tests):
- `SamplingMode.random`: `"Cannot specify both 'top' and 'probability_threshold'. Choose one sampling constraint."`
- `"'top' must be a positive integer"`
- `"'probability_threshold' must be between 0.0 and 1.0"`
- `"'seed' must be an integer"`
- `GenerationOptions.__post_init__`: `"'temperature' must be a number"`, `"'temperature' must be non-negative"`,
  `"'maximum_response_tokens' must be an integer"`, `"'maximum_response_tokens' must be positive"`,
  `"'sampling' must be a SamplingMode instance"`

Serialization (`to_dict`, generation_options.py:275-294):
```python
result = {}
if self.sampling is not None:
    sampling_dict = {"mode": self.sampling.mode_type.value}
    if self.sampling.mode_type == SamplingModeType.RANDOM:
        if self.sampling.top is not None:
            sampling_dict["top_k"] = str(self.sampling.top)                    # <-- str()!
        if self.sampling.probability_threshold is not None:
            sampling_dict["top_p"] = str(self.sampling.probability_threshold)  # <-- str()!
        if self.sampling.seed is not None:
            sampling_dict["seed"] = str(self.sampling.seed)                    # <-- str()!
    result["sampling"] = sampling_dict
if self.temperature is not None:            result["temperature"] = self.temperature
if self.maximum_response_tokens is not None: result["maximum_response_tokens"] = self.maximum_response_tokens
return result
```

Swift parser (`parseGenerationOptions`, FoundationModelsCBindings.swift:516-563):
```swift
if let samplingDict = json["sampling"] as? [String: Any], let mode = samplingDict["mode"] as? String {
  switch mode {
  case "greedy": options.sampling = .greedy
  case "random":
    let seed = samplingDict["seed"] as? UInt64
    // Swift API supports either topK or probabilityThreshold, not both
    if let topK = samplingDict["top_k"] as? Int {
      options.sampling = .random(top: topK, seed: seed)
    } else if let probabilityThreshold = samplingDict["top_p"] as? Double {
      options.sampling = .random(probabilityThreshold: probabilityThreshold, seed: seed)
    }
  default: break
  }
}
if let temperature = json["temperature"] as? Double { options.temperature = temperature }
if let maxTokens = json["maximum_response_tokens"] as? Int { options.maximumResponseTokens = maxTokens }
```

🔴 **BUG (type mismatch across the boundary): Python serializes `top_k` / `top_p` / `seed` as JSON
*strings* (`"50"`), while Swift casts with `as? Int` / `as? Double` / `as? UInt64`. Those casts fail
for `NSString`, so `options.sampling` is never assigned for `mode == "random"` and the random-sampling
parameters (including `seed`) are silently ignored.** `greedy`, `temperature`, and
`maximum_response_tokens` are unaffected. The `to_dict` docstring itself contradicts the code — it
shows `{'sampling': {'mode': 'random', 'top_k': 50}}` (int). Status: **confirmed by reading both
sides; not executed** (would need a real model to observe non-determinism with a fixed seed).

Practical implication: `fm.SamplingMode.random(top=50, seed=42)` will **not** give reproducible
outputs today. Tests only assert that a string comes back, never that the seed reproduces.

Swift maps only these three GenerationOptions fields; there is **no** `topP`+`topK` together,
no penalties, no stop sequences.

Documented warning (generation_options.py:166-174):
> "Only use `maximum_response_tokens` when you need to protect against unexpectedly verbose responses.
> Enforcing a strict token response limit can lead to the model producing malformed results or
> grammatically incorrect responses."
> "All input to the model contributes tokens to the context window, including the Instructions,
> Prompt, Tool definitions, and Generable types, as well as the model's responses."

---

## 11. Errors (`errors.py`)

Hierarchy:
```
Exception
└── FoundationModelsError
    ├── GenerationError
    │   ├── ExceededContextWindowSizeError
    │   ├── AssetsUnavailableError
    │   ├── GuardrailViolationError
    │   ├── UnsupportedGuideError
    │   ├── UnsupportedLanguageOrLocaleError
    │   ├── DecodingFailureError
    │   ├── RateLimitedError
    │   ├── ConcurrentRequestsError
    │   └── RefusalError(message, debug_description=None, explanation_entries=None)
    ├── InvalidGenerationSchemaError
    │   └── GenerableDecoratorError          (generable_utils.py, not exported)
    └── ToolCallError(tool_name, underlying_error)

Exception
└── PromptError                              (prompt.py — NOT a FoundationModelsError!)
    └── ImagePromptError
```
⚠️ `PromptError`/`ImagePromptError` inherit from plain `Exception`, so
`except fm.FoundationModelsError` will **not** catch them. (`tests/test_image_prompts.py:276` hedges
with `pytest.raises((fm.ImagePromptError, fm.FoundationModelsError))`.)

### Status codes (must stay in sync with Swift's private `enum StatusCode`)

| Code | Python `GenerationErrorCode` | Python exception | Swift case |
|---|---|---|---|
| 0 | `SUCCESS` | — | `.success` |
| 1 | `EXCEEDED_CONTEXT_WINDOW_SIZE` | `ExceededContextWindowSizeError` | `.exceededContextWindowSize` |
| 2 | `ASSETS_UNAVAILABLE` | `AssetsUnavailableError` | `.assetsUnavailable` |
| 3 | `GUARDRAIL_VIOLATION` | `GuardrailViolationError` | `.guardrailViolation` |
| 4 | `UNSUPPORTED_GUIDE` | `UnsupportedGuideError` | `.unsupportedGuide` |
| 5 | `UNSUPPORTED_LANGUAGE_OR_LOCALE` | `UnsupportedLanguageOrLocaleError` | `.unsupportedLanguageOrLocale` |
| 6 | `DECODING_FAILURE` | `DecodingFailureError` | `.decodingFailure` |
| 7 | `RATE_LIMITED` | `RateLimitedError` | `.rateLimited` |
| 8 | `CONCURRENT_REQUESTS` | `ConcurrentRequestsError` | `.concurrentRequests` |
| 9 | `REFUSAL` | `RefusalError` | `.refusal` |
| 10 | `INVALID_SCHEMA` | `InvalidGenerationSchemaError` | `.invalidSchema` |
| 11 | — (**not in Python**) | falls to generic `GenerationError` | `.invalidArgument` ("For NULL pointer errors (not in Python but useful for C API)") |
| 255 | `UNKNOWN_ERROR` | generic `GenerationError` | `.unknownError` |

`_status_code_to_exception(status_code, debug_description=None)` produces
`error_class(f"{message}: {debug_description}")` with these canned messages:
`"Context window size exceeded"`, `"Required assets are unavailable"`, `"Guardrail violation occurred"`,
`"Unsupported guide used"`, `"Unsupported language or locale"`, `"Failed to decode response"`,
`"Request was rate limited"`, `"Too many concurrent requests"`, `"Model refused to generate content"`,
`"Invalid generation schema provided"`.
Unknown codes → `GenerationError(f"Unknown generation error (status: {status_code}): {debug_description}")`.

⚠️ **Cancellation is reported as code 255**, not a distinct code: Swift's `catch is CancellationError`
branches call back with `StatusCode.unknownError.rawValue` and the message `"Operation cancelled"` /
`"Stream cancelled"`. The Python layer's own `asyncio.CancelledError` handling usually wins the race,
but a late native cancellation surfaces as a generic `GenerationError`.

`docs/source/api/errors.rst` adds authoritative colour:
> "**RateLimitedError** — Rate limits do not apply to the on-device `SystemLanguageModel` on macOS
> so you should not encounter this error."
> "**ConcurrentRequestsError** — The python SDK does not enforce concurrency limits so you should not
> encounter this error."
> "**RefusalError** — Raised when the model refuses to generate a response _specifically_ for safety
> reasons on a **generable** output."
> "**InvalidGenerationSchemaError** is unique to the Python SDK and does not have a direct Swift
> equivalent since it means a schema failed to compile in the underlying Swift."

Error-handling snippet from `docs/source/basic_usage.rst`:
```python
try:
    response = await session.respond("Your prompt here")
except fm.ExceededContextWindowSizeError:
    print("Prompt is too long")
except fm.GuardrailViolationError as e:
    print(f"Caught GuardrailViolationError: {e}")
except fm.GenerationError as e:
    print(f"Generation error: {e}")
```

---

## 12. Memory management model (`c_helpers.py`) + the `e868e60` fix

### 12.1 Ownership rules (documented verbatim, c_helpers.py:33-36, 206-240)

> "All C pointers passed from Swift to Python are assumed to be retained (ownership transferred).
> Python is responsible for releasing them exactly once when the object is deallocated."
> "When Swift passes a pointer via `passRetained`, it transfers ownership to Python with +1 reference
> count. Python must release it exactly once in `__del__`. Subclasses should NOT call `_retain()` in
> their `__init__` methods, as this would create +2 references but only -1 release, causing memory leaks."

```python
class _ManagedObject:
    def __init__(self, ptr):
        if not ptr:
            raise FoundationModelsError("Failed to create object")
        self._ptr = ptr
    def _retain(self):  lib.FMRetain(self._ptr)
    def _release(self):
        if hasattr(self, "_ptr") and self._ptr:
            lib.FMRelease(self._ptr)
    def __del__(self): self._release()
```
Subclasses: `SystemLanguageModel`, `LanguageModelSession`, `GenerationSchema`, `GeneratedContent`, `Tool`.
**Not** subclasses: `Transcript`, `Property` (Property releases its own ptr immediately after adding).

### 12.2 Handle registry (keeps Python futures alive across the C boundary)

```python
_active_handles = {}                 # id(obj) -> obj
_handle_lock = threading.Lock()

def _register_handle(obj):           # returns ctypes.c_void_p(id(obj))
def _unregister_handle(handle_ptr):  # pops it
def _safe_from_handle(handle_ptr):   # -> obj or None
```
> "Every call to `_register_handle` must be paired with a call to `_unregister_handle` to prevent memory leaks."

The `userInfo` pointer passed to Swift is literally `id(future)`. Since Python ints from `id()` are
addresses, and the registry keeps the object alive, the address stays valid.

### 12.3 Callbacks

Three module-level ctypes callbacks are created via decorator syntax on ctypesgen's function types:
```python
@lib.FMLanguageModelSessionResponseCallback
def _session_callback(status, content, length, future_handle): ...

@lib.FMLanguageModelSessionStructuredResponseCallback
def _session_structured_callback(status, content_ptr, future_handle): ...

@lib.FMSystemLanguageModelTokenCountCallback
def _token_count_callback(status, token_count, error_desc, future_handle): ...
```
All three resolve the future with `asyncio.run_coroutine_threadsafe(_set_future_result(...), future.get_loop())`
— because the callback runs on a **Swift `Task.detached` thread**, not the loop thread.

Text decoding in `_session_callback`:
```python
content_bytes = bytes(content[:length].data)
content_str = content_bytes.decode("utf-8")
```
(`StreamingCallback._callback_impl` uses `.decode("utf-8", errors="replace")` — more forgiving.)

`_session_structured_callback` carefully tracks `content_ptr_owned` so the `FMGeneratedContentRef` is
released exactly once even on the error path; on error it stringifies `generated_content._content_dict`
into `debug_description` before deleting.

### 12.4 `StreamingCallback`

```python
class StreamingCallback:
    error: Optional[FoundationModelsError]
    queue: queue.Queue          # None is the end-of-stream sentinel
    completed: threading.Event
    _callback                   # ctypes-wrapped closure
```
End of stream is signalled by Swift calling back with `content = nil, length = 0`.

### 12.5 Commit `e868e60` — "Release composed_prompt pointer in all respond() paths (#18)"

Author: Zhen Li, 2026-07-07. Full commit message:
> - `_respond_with_schema_from_json` already released it; extend the same fix to `_respond_basic` and
>   `_respond_with_schema`, which leaked one native `FMComposedPrompt` (and any retained image file
>   descriptors) per call.
> - Add regression tests covering success/error/cancellation paths for all three methods via mocked
>   native bindings.

Diff = 3 identical 7-line inserts into the `finally:` blocks:
```python
                if composed_prompt:
                    try:
                        lib.FMRelease(composed_prompt)
                    except Exception:
                        pass
```
plus `tests/test_composed_prompt_cleanup.py` (236 lines).

The regression test file is the best example in the repo of **mocking the native layer**:
```python
from apple_fm_sdk import session as session_module
from apple_fm_sdk.c_helpers import _safe_from_handle

FAKE_GENERATION_SCHEMA = SimpleNamespace(_ptr=ctypes.c_void_p(0xABCD))

METHOD_CONFIGS = [
    {"name": "_respond_basic",                "lib_func": "FMLanguageModelSessionRespond",
     "future_handle_index": 3, "extra_args": ()},
    {"name": "_respond_with_schema",          "lib_func": "FMLanguageModelSessionRespondWithSchema",
     "future_handle_index": 4, "extra_args": (FAKE_GENERATION_SCHEMA,)},
    {"name": "_respond_with_schema_from_json","lib_func": "FMLanguageModelSessionRespondWithSchemaFromJSON",
     "future_handle_index": 4, "extra_args": (DUMMY_SCHEMA,)},
]

@pytest.fixture
def mocked_session(monkeypatch):
    release_calls = []
    monkeypatch.setattr(session_module.lib, "FMRelease", lambda ptr: release_calls.append(ptr))
    monkeypatch.setattr(session_module.lib,
        "FMLanguageModelSessionCreateFromSystemLanguageModel", lambda *a, **k: ctypes.c_void_p(1))
    monkeypatch.setattr(session_module, "Transcript", lambda ptr: None)
    session = fm.LanguageModelSession()
    composed_prompt_ptr = ctypes.c_void_p(0x1234)
    monkeypatch.setattr(session, "_composed_prompt_from_prompt", lambda prompt: composed_prompt_ptr)
    yield session, composed_prompt_ptr, release_calls
    # The session wraps a fake pointer that was never really allocated by the native framework.
    # Neutralize it before monkeypatch restores the real FMRelease, otherwise a later GC pass would
    # call into native code with a bogus pointer and crash the process.
    session._ptr = None
```
Four parametrized tests: released on success / on error / on cancellation / **exactly once**.

⚠️ The module docstring claims *"2. An integration regression test that drives real sequential
structured generation requests with image attachments and asserts the process's open file descriptor
count stays flat"* — **that test is not present in the file** (the file contains only the four unit
tests). It imports `gc`, `os`, `asyncio` for it but never uses `gc`/`os`.

### 12.6 Remaining leaks I found by reading (all **UNVERIFIED at runtime**, but structurally clear)

1. **`_stream_response_basic` never releases `composed_prompt`.** `session.py:832-844` creates it,
   `session.py:897-908` releases only `stream_ptr_holder[0]`. The `e868e60` fix covered only the three
   `respond()` paths. → one leaked `FMComposedPrompt` (and any image FDs) per `stream_response()` call.
2. **`SystemLanguageModel.token_count(<prompt>)` never releases `composed_prompt`**
   (`core.py:394-399`). Same leak class.
3. **`Transcript.from_dict` leaks a whole `LanguageModelSession`.** `FMTranscriptCreateFromJSONString`
   returns a `passRetained` session; `Transcript` is not a `_ManagedObject` and has no `__del__`, so
   that pointer is never `FMRelease`d.
4. `Transcript` created by `LanguageModelSession.__init__` shares the session's pointer, which the
   session does release — correct there. But `from_transcript` calls `transcript._update_session_ptr(ptr)`
   and the *old* transcript-holder session pointer (from `from_dict`) is dropped without release.

### 12.7 Memory-test infrastructure

`tests/test_memory.py` (918 lines) covers: `weakref`-based deallocation checks for sessions / models /
`GeneratedContent` / tools, request queuing, cancellation cleanup, stream cleanup (normal / early break /
exception), and a comprehensive lifecycle test.

`tests/test_memory_stress.py` (152 lines) is **a standalone script, not a pytest test**
(`if __name__ == "__main__": sys.exit(asyncio.run(main()))`) — it creates **1000** model+session pairs,
runs `await session.respond("What is 2+2?")` on each with `PAUSE_BETWEEN_REQUESTS = 0.1`,
`gc.collect()` every `GC_INTERVAL = 10`, and fails if RSS grows more than
`MEMORY_LEAK_THRESHOLD_MB = 50`. Requires `psutil`.

⚠️ Because `python_files = ["test_*.py"]`, pytest **will still collect `test_memory_stress.py`** —
but it defines no `test_*` functions, so nothing runs. Run it manually:
```bash
python tests/test_memory_stress.py
```

---

## 13. Concurrency / async model

- Every native async operation returns an `FMTaskRef` (a retained Swift `TaskBox`) which must be
  `FMTaskCancel`-able and `FMRelease`d.
- Python side: `loop.create_future()` + registered handle + callback resolves via
  `asyncio.run_coroutine_threadsafe`.
- **Per-session serialization**: `self._request_lock = asyncio.Lock()` guards all three `respond*`
  methods. `tests/test_memory.py::test_concurrent_requests_queued` asserts
  `completion_order == ["first", "second"]`.
- **Cross-session concurrency is allowed** (`test_multiple_sessions_concurrent` runs 3 sessions with
  `asyncio.gather`) — but `docs/source/evaluation.rst:76-78` warns:
  > "Note that each inference call will be processed one at a time (not in parallel) at the macOS
  > hardware level, so consider the time implications of large batches."
- **`stream_response` does NOT take the lock** — mixing a stream and a `respond()` on one session is
  unguarded.
- Cancellation recipe (from `tests/test_memory.py::test_timeout_handling`):
  ```python
  task = asyncio.create_task(session.respond("Write a very long essay ..."))
  await asyncio.sleep(0.1)
  task.cancel()
  with pytest.raises(asyncio.CancelledError):
      await task
  # then WAIT for the native side:
  while session.is_responding:
      await asyncio.sleep(0.5)
  await asyncio.sleep(0.2)     # "Additional delay for native cleanup"
  ```
  The SDK itself polls `is_responding` for up to **1.0 s** at **10 ms** intervals after a cancellation
  before calling `_reset_task_state()`.
- The Swift `respond` implementation does `try Task.checkCancellation()` at start, before the callback,
  and (for schema paths) before/after schema building — so cancellation granularity is coarse.

---

## 14. The C ABI (`FoundationModels.h`, 146 lines) — full reference

### Opaque types
```c
typedef const void *_Nonnull FMTaskRef;
typedef const void *FMSystemLanguageModelRef;
typedef const void *FMLanguageModelSessionRef;
typedef const void *FMLanguageModelSessionResponseStreamRef;
typedef const void *FMGenerationSchemaRef;
typedef const void *FMGeneratedContentRef;
typedef const void *FMGenerationSchemaPropertyRef;
typedef const void *FMBridgedToolRef;
typedef const void *_Nonnull FMComposedPrompt;
```

### Callbacks
```c
typedef void (*FMLanguageModelSessionResponseCallback)(
    int status, const char *content, size_t length, void *userInfo)      __attribute__((swift_attr("@Sendable")));
typedef void (*FMLanguageModelSessionStructuredResponseCallback)(
    int status, FMGeneratedContentRef content, void *userInfo)           __attribute__((swift_attr("@Sendable")));
typedef void (*FMSystemLanguageModelTokenCountCallback)(
    int status, int tokenCount, const char *errorDescription, void *userInfo) __attribute__((swift_attr("@Sendable")));
```

### Enums
```c
FMSystemLanguageModelUnavailableReason{AppleIntelligenceNotEnabled=0, DeviceNotEligible=1, ModelNotReady=2, Unknown=0xFF}
FMSystemLanguageModelUseCase{General=0, ContentTagging=1}
FMSystemLanguageModelGuardrails{Default=0, PermissiveContentTransformations=1}
FMComposedPromptAddImageError{None, UnsupportedOS, UnsupportedSDK, Unknown}
```

### Functions (grouped, exact signatures)
```c
/* Model */
FMSystemLanguageModelRef FMSystemLanguageModelGetDefault(void);
FMSystemLanguageModelRef FMSystemLanguageModelCreate(FMSystemLanguageModelUseCase, FMSystemLanguageModelGuardrails);
bool FMSystemLanguageModelIsAvailable(FMSystemLanguageModelRef, FMSystemLanguageModelUnavailableReason *);
int  FMSystemLanguageModelGetContextSize(FMSystemLanguageModelRef);

/* Sessions */
FMLanguageModelSessionRef FMLanguageModelSessionCreateDefault(void);
FMLanguageModelSessionRef FMLanguageModelSessionCreateFromSystemLanguageModel(
    FMSystemLanguageModelRef model, const char *instructions, FMBridgedToolRef *tools, int toolCount);
FMLanguageModelSessionRef FMLanguageModelSessionCreateFromTranscript(
    FMLanguageModelSessionRef transcriptSession, FMSystemLanguageModelRef model,
    FMBridgedToolRef *tools, int toolCount);
bool FMLanguageModelSessionIsResponding(FMLanguageModelSessionRef);
void FMLanguageModelSessionReset(FMLanguageModelSessionRef);

/* Prompts */
FMComposedPrompt FMComposedPromptInitialize(void);
void FMComposedPromptAddText(FMComposedPrompt, const char *text);
bool FMComposedPromptAddImage(FMComposedPrompt, const char *imagePath, FMComposedPromptAddImageError *);          /* DECLARED, NOT IMPLEMENTED */
bool FMComposedPromptAddIdentifiedImage(FMComposedPrompt, const char *imagePath,
                                        const char *imageIdentifier, FMComposedPromptAddImageError *);            /* DECLARED, NOT IMPLEMENTED */
bool FMComposedPromptAddAttachment(FMComposedPrompt, const char *imagePath,
                                   const char *label, FMComposedPromptAddImageError *);

/* Token counting (all return FMTaskRef; cancel with FMTaskCancel, release with FMRelease) */
FMTaskRef FMSystemLanguageModelTokenCountForPrompt(FMSystemLanguageModelRef, FMComposedPrompt, void *, FMSystemLanguageModelTokenCountCallback);
FMTaskRef FMSystemLanguageModelTokenCountForInstructions(FMSystemLanguageModelRef, const char *, void *, FMSystemLanguageModelTokenCountCallback);
FMTaskRef FMSystemLanguageModelTokenCountForTools(FMSystemLanguageModelRef, FMBridgedToolRef *, int, void *, FMSystemLanguageModelTokenCountCallback);
FMTaskRef FMSystemLanguageModelTokenCountForSchema(FMSystemLanguageModelRef, FMGenerationSchemaRef, void *, FMSystemLanguageModelTokenCountCallback);
FMTaskRef FMSystemLanguageModelTokenCountForTranscript(FMSystemLanguageModelRef, FMLanguageModelSessionRef, void *, FMSystemLanguageModelTokenCountCallback);

/* Responses */
FMTaskRef FMLanguageModelSessionRespond(FMLanguageModelSessionRef, FMComposedPrompt, const char *optionsJSON, void *, FMLanguageModelSessionResponseCallback);
FMLanguageModelSessionResponseStreamRef FMLanguageModelSessionStreamResponse(FMLanguageModelSessionRef, FMComposedPrompt, const char *optionsJSON);
void FMLanguageModelSessionResponseStreamIterate(FMLanguageModelSessionResponseStreamRef, void *, FMLanguageModelSessionResponseCallback);
FMTaskRef FMLanguageModelSessionRespondWithSchema(FMLanguageModelSessionRef, FMComposedPrompt, FMGenerationSchemaRef, const char *optionsJSON, void *, FMLanguageModelSessionStructuredResponseCallback);
FMTaskRef FMLanguageModelSessionRespondWithSchemaFromJSON(FMLanguageModelSessionRef, FMComposedPrompt, const char *schemaJSONString, const char *optionsJSON, void *, FMLanguageModelSessionStructuredResponseCallback);

/* Transcript */
FMLanguageModelSessionRef FMTranscriptCreateFromJSONString(const char *jsonString, int *outErrorCode, char **outErrorDescription);
char *FMLanguageModelSessionGetTranscriptJSONString(FMLanguageModelSessionRef, int *outErrorCode, char **outErrorDescription);

/* Schema */
FMGenerationSchemaRef         FMGenerationSchemaCreate(const char *name, const char *description);
FMGenerationSchemaPropertyRef FMGenerationSchemaPropertyCreate(const char *name, const char *description, const char *typeName, bool isOptional);
void FMGenerationSchemaPropertyAddAnyOfGuide(FMGenerationSchemaPropertyRef, const char **anyOf, int choiceCount, bool wrapped);
void FMGenerationSchemaPropertyAddCountGuide(FMGenerationSchemaPropertyRef, int count, bool wrapped);
void FMGenerationSchemaPropertyAddMaximumGuide(FMGenerationSchemaPropertyRef, double maximum, bool wrapped);
void FMGenerationSchemaPropertyAddMinimumGuide(FMGenerationSchemaPropertyRef, double minimum, bool wrapped);
void FMGenerationSchemaPropertyAddMinItemsGuide(FMGenerationSchemaPropertyRef, int minItems);   /* NOTE: no `wrapped` */
void FMGenerationSchemaPropertyAddMaxItemsGuide(FMGenerationSchemaPropertyRef, int maxItems);   /* NOTE: no `wrapped` */
void FMGenerationSchemaPropertyAddRangeGuide(FMGenerationSchemaPropertyRef, double minValue, double maxValue, bool wrapped);
void FMGenerationSchemaPropertyAddRegex(FMGenerationSchemaPropertyRef, const char *pattern, bool wrapped);
void FMGenerationSchemaAddProperty(FMGenerationSchemaRef, FMGenerationSchemaPropertyRef);
void FMGenerationSchemaAddReferenceSchema(FMGenerationSchemaRef, FMGenerationSchemaRef);
char *FMGenerationSchemaGetJSONString(FMGenerationSchemaRef, int *outErrorCode, char **outErrorDescription);

/* GeneratedContent */
FMGeneratedContentRef FMGeneratedContentCreateFromJSON(const char *jsonString, int *outErrorCode, char **outErrorDescription);
char *FMGeneratedContentGetJSONString(FMGeneratedContentRef);
char *FMGeneratedContentGetPropertyValue(FMGeneratedContentRef, const char *propertyName, int *outErrorCode, char **outErrorDescription);
bool  FMGeneratedContentIsComplete(FMGeneratedContentRef);

/* Tools */
FMBridgedToolRef FMBridgedToolCreate(const char *name, const char *description, FMGenerationSchemaRef parameters,
                                     void (*callable)(FMGeneratedContentRef, unsigned int),
                                     int *outErrorCode, char **outErrorDescription) __attribute__((swift_attr("@Sendable")));
void FMBridgedToolFinishCall(FMBridgedToolRef, unsigned int callId, const char *output);

/* Memory */
void FMTaskCancel(FMTaskRef);
void FMRetain(const void *);
void FMRelease(const void *);
void FMFreeString(char *);
```

Strings returned by `FM*GetJSONString` / `FM*GetPropertyValue` / `outErrorDescription` are
`strdup`-allocated and **must be freed with `FMFreeString`**. Python relies on ctypesgen's `String`
wrapper for the JSON-string returns (`# The String wrapper handles memory, so we don't need to manually
free`) but explicitly calls `lib.FMFreeString(error_desc)` in `_get_error_string`.

### Arity mismatches (Python passes 3 args to 2-arg C functions)
`generation_guide.py:290-293`:
```python
lib.FMGenerationSchemaPropertyAddMaxItemsGuide(prop_ptr, int(value), wrapped)
lib.FMGenerationSchemaPropertyAddMinItemsGuide(prop_ptr, int(value), wrapped)
```
but the header and Swift both declare only `(property, count)`. On arm64 the extra argument lands in
an ignored register, so it is harmless in practice — but it means `element=GenerationGuide.min_items(...)`
wrapping is **silently dropped** (the `wrapped` flag never reaches Swift for min/max items).

### Dead C declarations
`FMComposedPromptAddImage` and `FMComposedPromptAddIdentifiedImage` are declared in the header but
**have no `@_cdecl` implementation** at HEAD (they were replaced by `FMComposedPromptAddAttachment`
in commit `da32e98`, "Clarify the error for image inputs being unsupported"). ctypesgen will emit
bindings for them; calling them would fail to resolve the symbol.
`FMSystemLanguageModelGetDefault` and `FMLanguageModelSessionCreateDefault` are implemented but never
used from Python (Python always goes through `FMSystemLanguageModelCreate`).

### The C example is stale
`foundation-models-c/Sources/fm-c-example/main.c:52`:
```c
FMLanguageModelSessionResponseStreamRef stream =
    FMLanguageModelSessionStreamResponse(session, "What programming language is better, Swift or C?", NULL);
```
passes a **string literal where an `FMComposedPrompt` is expected**. It still compiles (implicit
`const char*` → `const void*` in C) but `Unmanaged<ComposedPrompt>.fromOpaque(...)` on a string
literal is undefined behaviour. The Swift test (`BasicSystemModelTests.swift:47-48`) does it correctly:
```swift
let prompt = FMComposedPromptInitialize()
FMComposedPromptAddText(prompt, "What programming language is better, Swift or C?")
```
**UNVERIFIED** that `fm-c-example` actually crashes; I did not build it.

---

## 15. Swift binding internals worth knowing

- `ComposedPrompt: NSObject, PromptRepresentable` accumulates `[PromptRepresentable]` and exposes
  `var promptRepresentation: Prompt { Prompt { components.map(\.promptRepresentation) } }`.
- Every async entry point wraps a `Task.detached { ... }` inside a `final class TaskBox` and returns
  `Unmanaged.passRetained(taskBox).toOpaque()`.
- `private struct UnsafeSendableUserInfo: @unchecked Sendable { var pointer: UnsafeMutableRawPointer? }`
  is how the Python future handle crosses the Sendable boundary.
- Streaming: `UnsafeSendableResponseStreamBox<Content: Generable>` holds the
  `LanguageModelSession.ResponseStream<Content>` **and a strong reference to the session**;
  `deinit { iterationTask?.cancel() }`. The box is instantiated as
  `UnsafeSendableResponseStreamBox<String>` — hence **text-only streaming**.
  The stream loop is `for try await snapshot in stream { ... snapshot.content.withCString { ... } }`,
  then a final `callback(success, nil, 0, userInfo)` to signal completion.
- Guided generation calls `session.respond(to: prompt, schema: finalSchema, options: options ?? GenerationOptions())`.
- `GenerationSchemaBuilder.buildSchema()`:
  ```swift
  let refSchemas = try referenceSchemas.map { try $0.buildDynamicSchema() }
  let dynamicSchema = try buildDynamicSchema()
  let schema = try GenerationSchema(root: dynamicSchema, dependencies: refSchemas)
  ```
- `BridgedTool: Tool` uses `Atomic<CUnsignedInt>` for call IDs and
  `Mutex<[CUnsignedInt: CheckedContinuation<String, any Error>]>` for pending calls
  (needs `import Synchronization`).
- `FMGeneratedContentGetPropertyValue` calls `try wrapper.content.value(forProperty: propName)` typed
  as `String` — **it can only return string properties**. Python never uses it (it JSON-decodes the
  whole content instead).

Swift package products (`Package.swift`):
```swift
.library(name: "FoundationModels",       type: .dynamic, targets: ["FoundationModelsCBindings"]),
.library(name: "FoundationModelsStatic", type: .static,  targets: ["FoundationModelsCBindings"]),
.executable(name: "fm-c-example", targets: ["fm-c-example"])
```
`FoundationModelsCDeclarations` is a "placeholder target that exposes the declarations from the
bindings header to the bindings library itself" — its only real content is
`include/module.modulemap`:
```
module FoundationModelsCDeclarations {
  header "../../FoundationModelsCBindings/include/FoundationModels.h"
  export *
}
```
and a one-line `FoundationModelsCDeclarations.c` (`// Placeholder file`).

Swift tests (`Tests/FoundationModelsCBindingsTests/BasicSystemModelTests.swift`, 253 lines) use
swift-testing (`@Suite`, `@Test`, `#expect`, `.enabled(if: SystemLanguageModel.default.isAvailable)`)
and cover availability, a full respond round-trip, BridgedTool concurrency (10 concurrent calls),
sequential reuse, unique-ID generation (50 calls), context size, and token count for a prompt.
Run with `cd foundation-models-c && swift test`.

---

## 16. Tests: how to run, layout, patterns

### Commands (tests/README.md)
```bash
pytest                               # all
pytest tests/test_session.py         # one file
pytest -s                            # show the (very chatty) debug prints
pytest tests/test_doc_website_snippets.py -v
```
⚠️ Many tests open fixtures by **repo-root-relative** path (`"tests/tester_schemas/test_transcript.json"`),
so you must run pytest from the repository root.

Imports like `from tester_tools.tester_tools import ...` and `import tester_schemas.schemas as tester_schemas`
work because pytest (rootdir-insert, no `__init__.py` in `tests/`) puts `tests/` on `sys.path`.

### `tests/conftest.py` (221 lines) — notable machinery
- `pytest_collection_modifyitems` **reorders** so everything outside `doc_tests/` runs first.
- `pytest_runtest_makereport` hookwrapper **converts `fm.ExceededContextWindowSizeError` failures into
  `UserWarning`s and marks the test passed** — a real signal that context overflow is flaky:
  ```python
  if exc_type is fm.ExceededContextWindowSizeError:
      warnings.warn(f"ExceededContextWindowSizeError in {item.nodeid}: {exc_value}", UserWarning, stacklevel=2)
      report.outcome = "passed"
      report.wasxfail = f"ExceededContextWindowSizeError (converted to warning): {exc_value}"
  ```
- `pytest_runtest_teardown` + an autouse `cleanup_between_tests` fixture do `gc.collect()` twice and
  `time.sleep(0.1)` / `0.05` "to allow native resources to be released".
- Fixtures: `model` (skips with `pytest.skip(f"Model not available: {reason}")`),
  `session` (`fm.LanguageModelSession(model=model)`), `test_image_path`.
- Helper `assert_schema_properties(schema, title, properties)` — checks `jsn["title"]`, property count,
  and presence of each property name.

### Test files
| File | Lines | Focus |
|---|---|---|
| `test_session.py` | 458 | init options, `is_responding`, `GenerationOptions` with `respond`, `from_transcript` (basic/full/tools/no-model/continue/empty-tools) |
| `test_system_model.py` | 112 | enums, availability, custom model, invalid use-case fallback |
| `test_streaming.py` | 126 | streaming + all `GenerationOptions` combos |
| `test_prompts.py` | 74 | basic / unsafe / invalid prompts (`""`, `"   "`, `"A"*10000`, `"A dog jumped over a log. "*10000`, `"Hello\x00World"`) |
| `test_transcript.py` | 474 | `to_dict`, `from_dict`, pointer validity, lifetime/weakref |
| `test_tool.py` | 626 | creation, direct invocation, session integration, error handling, complex types, async/parallel, subclass validation failures |
| `test_guided_generation.py` | 272 | the 7 parity types via `generating=` |
| `test_guides.py` | 811 | every guide type + the full unsupported-guide matrix |
| `test_json_guided_generation.py` | 298 | the 7 JSON fixtures via `json_schema=` |
| `test_generable_protocol.py` | 300 | decorator forms + decorator error messages |
| `test_generation_options.py` | 243 | pure-Python validation of options/sampling |
| `test_error_handling.py` | 210 | invalid schemas, context window, guardrails, locale, status-code mapping |
| `test_image_prompts.py` | 363 | attachments (skips on `ImagePromptError`) |
| `test_token_count.py` | 138 | `context_size` + all 5 `token_count` inputs + arg validation |
| `test_memory.py` | 918 | weakref leak detection, concurrency, cancellation, stream cleanup |
| `test_memory_stress.py` | 152 | standalone 1000-iteration RSS test |
| `test_composed_prompt_cleanup.py` | 236 | the `e868e60` regression tests (mocked native layer) |
| `doc_tests/test_readme_snippets.py` | 94 | executes README snippets verbatim |
| `doc_tests/test_doc_website_snippets.py` | 982 | executes every `.rst` snippet |
| `doc_tests/test_symbol_docs_*.py` | 133–380 each | executes every docstring snippet, per source module |

The doc-test convention is spelled out in each file's module docstring:
> "Copy the snippet from the source **exactly** as it appears in the documentation. Surround the
> original source with `####...` / `# From: src/apple_fm_sdk/<file>.py` / `# class, function, or other
> entity name: <name>` / `####...`. The test passes if the snippet runs without errors."

`tests/README.md` "Known Pylance Warnings" section is partly stale — it claims *"`fm.Transcript` may
show as unknown because Transcript is not exported in `__init__.py`"*, but `Transcript` **is** in
`__all__` (`__init__.py:72`). It also says the docs use `def arguments_schema(self)` while the API
uses `@property` — the current `.rst` docs do use `@property`.

---

## 17. Recent commit history (`git log --oneline -50`, full history is 10 commits)

```
e868e60 Release composed_prompt pointer in all respond() paths (#18)     2026-07-07  Zhen Li
84841bb Bump version to 0.2.1
db7afde Add SystemLanguageModel context size and token count (#15)       2026-06-22  Zhen Li
da32e98 Clarify the error for image inputs being unsupported (#14)       2026-06-22  eric gourlaouen
3ff9c60 Images in prompts                                                2026-06-08  Mary Beth Kery
8d56a2d Make @generable decorator more flexible (#10)                    2026-03-08  MaryBeth
0f65c9b Adding generation options (#9)
6b6f833 Adding the ability to load a session from a saved transcript (#8)
e9a40a5 Updating README.md (#7)
3204b7e Hello apple-fm-sdk
```

What each of the interesting ones changed:
- **`3ff9c60` "Images in prompts"** (+1340/-49): created `prompt.py` (282 lines new), added
  `Attachment`/`ImageAttachment`/`Prompt` types, the `FM_HAS_MACOS_27_SDK` build flag in
  `build_backend.py`, `docs/source/api/attachment.rst`, `tests/test_image_prompts.py`,
  and the two test image resources. Before this, prompts were plain strings all the way down.
- **`da32e98`** replaced `FMComposedPromptAddImage`/`AddIdentifiedImage` with
  `FMComposedPromptAddAttachment(…, label, error)`, added the `FMComposedPromptAddImageError` enum,
  and moved the "your Xcode is too old" explanation into the error message. Commit body:
  *"Remove docs re: image input SDKs — The error message should be self-explanatory."*
- **`db7afde`** added `SystemLanguageModelGetContextSize`, the five `TokenCountFor*` functions, the
  `FMSystemLanguageModelTokenCountCallback` type, `_token_count_callback`, `core.py::context_size` and
  `token_count`, and `tests/test_token_count.py`. It also refactored `session.py` to use the shared
  `_composed_prompt_from_prompt` from `prompt.py`.
- **`8d56a2d` "Make @generable decorator more flexible"** (+470/-27) added the bare-`@fm.generable`
  form (the `isinstance(arg, type)` branch + overloads) and all the long, example-rich
  `GenerableDecoratorError` messages, plus `tests/test_generable_protocol.py`.
- **`e868e60`** — see §12.5.

Signal: the project is actively evolving around **memory correctness**, **image input**, and
**token accounting**. Nothing in the visible history touches structured *streaming*.

---

## 18. Gotchas, footguns, and bugs (consolidated)

**Build / install**
1. `pip install apple-fm-sdk` from **sdist compiles Swift on your machine** — you need full Xcode ≥26,
   `xcode-select` pointing at Xcode (not CommandLineTools), and macOS ≥26.
2. Image attachments require the **macOS 27 SDK at build time** (`FM_HAS_MACOS_27_SDK`) **and**
   macOS 27 at runtime. A wheel built on Xcode 26 permanently lacks image support.
3. Token counting requires **macOS 26.4+**; older OSes get an `NSError` surfaced as
   `GenerationError(... "Token counting requires macOS 26.4, iOS 26.4, or visionOS 26.4 or later.")`.
4. `apple_fm_sdk.__version__ == "0.1.0"` while the package version is `0.2.1`.
5. `_ctypes_bindings.py` is generated; if it's missing you get
   `ImportError("Foundation Models C bindings not found. Please ensure _foundationmodels_ctypes.py is available.")`
   — the message names a file that doesn't exist.

**Typing / schema**
6. 🔴 `Property.convert_to_c` detects optionality with `"Optional" in str(type)`.
   → **`x: str | None` (PEP 604) is never optional** on Python ≤3.13, and worse,
   `_python_type_to_string` mangles it into a bogus schema *reference*.
   → **On Python 3.14 even `typing.Optional[X]` stops being detected** because `str(Optional[int])`
   became `'int | None'`. (Measured on 3.11/3.12/3.13/3.14 in this session.)
   Use `typing.Optional[X]` and pin Python ≤3.13 until this is fixed.
7. Bare `list` annotations raise `TypeError("Generic list types must specify an element type, for
   example, List[str]")`. Use `List[str]` / `list[str]`.
8. 🔴 `@fm.generable("A description")` stores `_generable_description` but **never puts it in the
   schema** — the type-level description is lost vs Swift's `@Generable(description:)`.
9. Guides are validated **on the Swift side at `respond()` time**, not at decoration time — a bad
   guide/type pairing only blows up (as `UnsupportedGuideError`) when you actually run inference.
10. `bool` properties ignore all guides (Swift builds them as `.init(type: Bool.self)`).
11. Arrays of referenced Generables accept only `count` / `min_items` / `max_items`.
12. `element=` wrapping for `min_items` / `max_items` is dropped because those C functions have no
    `wrapped` parameter.
13. `datetime.date` (and any non-JSON-schema type) fails at `schema.to_dict()` time with
    `InvalidGenerationSchemaError` (`tests/test_error_handling.py::test_error_on_invalid_generation_schema`).
14. `Property` is documented with `>>> from apple_fm_sdk import Property` but is **not exported**.

**Runtime behaviour**
15. 🔴 `respond(..., generating=X, options=...)` **drops `options`** (session.py:473).
16. 🔴 `GenerationOptions.to_dict()` stringifies `top_k`/`top_p`/`seed`; Swift casts them as
    `Int`/`Double`/`UInt64` → **random sampling params and seeds are silently ignored**.
    Only `greedy`, `temperature`, and `maximum_response_tokens` actually take effect.
17. `stream_response` is **text-only** and **does not acquire the session request lock**.
18. `stream_response` leaks the composed prompt (and any image FDs) per call; so does
    `token_count(<prompt>)`; so does `Transcript.from_dict` (leaks a whole native session).
19. Tool exceptions are converted to the string `"Tool error: <msg>"` and fed back to the model —
    they never surface as Python exceptions from `respond()`. `fm.ToolCallError` is never raised by
    the SDK.
20. A tool whose `call()` never resolves hangs the Swift `CheckedContinuation` → the session hangs.
    Wrap in `asyncio.wait_for`.
21. `Tool` validation uses bare `assert`s → **silently skipped under `python -O`**.
22. `GeneratedContent()` / `GeneratedContent(content_dict={})` never sets `self._ptr`, so
    `.to_json()` / `.is_complete` raise `AttributeError`.
23. `GeneratedContent.value(T, for_property="missing")` returns `None` — no `KeyError`.
24. `GeneratedContent.value()` does **not** coerce types; the `type_class` argument only drives
    Generable unpacking. `_convert_value` is dead code.
25. `LanguageModelSession(instructions="")` == no instructions (falsy → `NULL`).
26. `Transcript.to_dict()` / `Transcript.from_dict()` are `async` but await nothing.
27. `PromptError`/`ImagePromptError` are **not** `FoundationModelsError` subclasses.
28. `_composed_prompt_from_prompt` expands *any* non-str iterable, including dicts and generators.
29. `ImageAttachment(path=...)` requires a `pathlib.Path` (calls `.is_file()`), not a `str`.
30. Cancellation surfaces from the native side as status **255** with message `"Operation cancelled"`,
    i.e. a plain `GenerationError`, not `asyncio.CancelledError` — the Python-side handling usually
    wins the race but not guaranteed.
31. After cancelling, you must poll `session.is_responding` (plus ~0.2 s) before reusing the session
    — this pattern appears in every cancellation test.
32. `token_count([])` takes the *tools* branch, not the prompt branch.
33. `PartiallyGenerated` classes are generated for every `@generable` type but are never used —
    there is no structured/partial streaming.

**Docs that are wrong**
34. `session.py:87-90` shows `fm.SystemLanguageModel(temperature=0.7, top_p=0.9)` — those kwargs
    don't exist.
35. `generable_utils.py:109-112` and `test_symbol_docs_generable_utils.py` show
    `session.respond(Cat, prompt="...")` in a comment — the real order is `respond(prompt, generating=Cat)`.
36. `generation_options.py:273` docstring shows `'top_k': 50` (int) while the code emits `"50"` (str).
37. `tests/README.md` claims `Transcript` isn't exported (it is).
38. `test_composed_prompt_cleanup.py`'s docstring describes an FD-count integration test that isn't
    in the file.

---

## 19. Limitations vs the Swift Foundation Models API

Things the Swift API has that this SDK does **not** expose (based on what's absent from the C header
and Python surface):

- **No structured streaming.** Swift's `streamResponse(to:generating:)` yielding
  `Response.Partial<T>` snapshots has no Python equivalent — `stream_response` yields `str` only,
  and the Swift shim hard-codes `ResponseStream<String>`.
- **No `Response` wrapper.** Swift returns `Response<Content>` with `.content`, `.rawContent`,
  `.transcriptEntries`; Python returns the bare `str` / typed object / `GeneratedContent` and you
  must re-read `session.transcript` for entries.
- **No prewarm / adapter APIS.** No `session.prewarm()`, no `SystemLanguageModel(adapter:)`,
  no `SystemLanguageModel.Adapter`.
- **No `Instructions` builder / `@InstructionsBuilder` / `@PromptBuilder`.** Instructions are a plain
  `str`; prompts are a `str` / list.
- **No `Tool.Output` / `ToolOutput` richness.** Python tools must return a `str`
  (non-strings are `str()`-ed).
- **No `GeneratedContent` typed accessors.** Swift's `content.value(Int.self, forProperty:)` is
  approximated by a JSON dict lookup.
- **No dynamic `GenerationSchema` construction from Python** beyond the `Property`/guide set the C
  shim exposes — no `DynamicGenerationSchema(anyOf:)`, no union/`oneOf` schemas.
- **`GenerationOptions` is limited to** `sampling` (greedy / random top-k / random top-p, all with an
  optional seed), `temperature`, `maximumResponseTokens`. (And random sampling is currently broken —
  gotcha #16.)
- **`SystemLanguageModel.UseCase`** exposes only `general` and `contentTagging`.
- **No `Transcript.Entry` object model** — transcripts are opaque `dict`s in Python.
- **`isResponding` only; no `Task`/priority control.**
- **Attachments: images only** (`Attachment(imageURL:)`), file path only — no in-memory image data,
  no other attachment kinds.
- Positioning is explicit (docs/source/index.rst:13-16): *"You can use this Python SDK to **evaluate**
  your Swift app's Foundation Models features … so you can be confident that your evaluations reflect
  real on-device performance and behavior."*

---

## 20. Copy-paste starter snippets

```python
# --- minimal ---------------------------------------------------------------
import asyncio
import apple_fm_sdk as fm

async def main():
    model = fm.SystemLanguageModel()
    ok, reason = model.is_available()
    if not ok:
        print(f"Foundation Models not available: {reason}")   # reason is an IntEnum; use reason.name
        return
    session = fm.LanguageModelSession(instructions="You are a helpful assistant.")
    print(await session.respond("What is the capital of France?"))
    print(await session.respond("What is its population?"))    # context carries over

asyncio.run(main())
```

```python
# --- guided generation, nested + guides ------------------------------------
from typing import List
import apple_fm_sdk as fm

@fm.generable("Habitat information")
class Habitat:
    location: str   = fm.guide("Geographic location")
    climate: str    = fm.guide("Climate type", anyOf=["temperate", "tropical", "arid", "polar"])
    vegetation: str = fm.guide("Primary vegetation")

@fm.generable("Hedgehog profile")
class Hedgehog:
    name: str       = fm.guide("Hedgehog name")
    age: int        = fm.guide("Age in years", range=(0, 10))
    weight: float   = fm.guide("Weight in grams", range=(200.0, 1200.0))
    habitat: Habitat = fm.guide("Natural habitat")
    diet: str       = fm.guide("Primary diet")

session = fm.LanguageModelSession("Extract hedgehog information from the prompt")
result = await session.respond(
    "Spike is a 3-year-old hedgehog weighing 800 grams. He lives in temperate European "
    "woodlands with mixed vegetation and primarily eats insects.",
    generating=Hedgehog)
print(result.name, result.habitat.climate, result.diet)
```

```python
# --- raw JSON schema exported from Swift -----------------------------------
import json, apple_fm_sdk as fm
with open("schema.json") as f:
    swift_schema = json.load(f)
session = fm.LanguageModelSession(instructions="Generate a product review.")
content = await session.respond("This laptop is amazing! Great performance and battery life.",
                                json_schema=swift_schema)     # -> fm.GeneratedContent
print(content.to_json())
print(content.value(str, for_property="sentiment"))
```

```python
# --- generation options (note the random-sampling caveat) ------------------
options = fm.GenerationOptions(
    temperature=0.7,
    sampling=fm.SamplingMode.random(top=50, seed=42),          # top/seed currently dropped, see §10
    maximum_response_tokens=500,
)
text = await session.respond("Write a creative story", options=options)
```

```python
# --- streaming --------------------------------------------------------------
async for snapshot in session.stream_response("Tell me a short story"):
    print(snapshot, end="", flush=True)     # each snapshot is the FULL text so far
```

```python
# --- token budgeting --------------------------------------------------------
model = fm.SystemLanguageModel()
budget = model.context_size
used  = await model.token_count("Tell me about the history of Swift.")
used += await model.token_count(instructions="You are a helpful assistant.")
used += await model.token_count([MyTool()])
used += await model.token_count(MyType.generation_schema())
print(f"Using {used} of {budget} tokens")
```

```python
# --- batch evaluation loop (docs/source/evaluation.rst) --------------------
results = []
for i, test_case in enumerate(test_cases):
    session = fm.LanguageModelSession()
    try:
        if "schema" in test_case:
            result = await session.respond(prompt=test_case["prompt"], json_schema=test_case["schema"])
        else:
            result = await session.respond(prompt=test_case["prompt"])
        results.append({"test_id": i, "success": test_case["expected"] in result, "result": result})
    except Exception as e:
        results.append({"test_id": i, "success": False, "error": str(e)})
with open("evaluation_results.json", "w") as f:
    json.dump(results, f, indent=2)
```
(Note: `respond(prompt=...)` works because `prompt` is the parameter name.)

---

## 21. Source inventory — every file I actually read this session

All paths relative to `/Volumes/ExtStor/FM and MLX and CoreAI/repos/apple__python-apple-fm-sdk`.

Read **in full**:
- `README.md`, `pyproject.toml`, `MANIFEST.in`, `build_backend.py`, `.gitignore`, `.swift-format`,
  `LICENSE.md` (head)
- `src/apple_fm_sdk/__init__.py`, `core.py`, `session.py`, `prompt.py`, `transcript.py`, `tool.py`,
  `generable.py`, `generable_utils.py`, `generation_schema.py`, `generation_property.py`,
  `generation_guide.py`, `generation_options.py`, `errors.py`, `type_conversion.py`, `c_helpers.py`
- `foundation-models-c/Package.swift`
- `foundation-models-c/Sources/FoundationModelsCBindings/include/FoundationModels.h`
- `foundation-models-c/Sources/FoundationModelsCBindings/FoundationModelsCBindings.swift` (all 1831 lines, in 2 pages)
- `foundation-models-c/Sources/FoundationModelsCDeclarations/FoundationModelsCDeclarations.c`
- `foundation-models-c/Sources/FoundationModelsCDeclarations/include/module.modulemap`
- `foundation-models-c/Sources/fm-c-example/main.c`
- `foundation-models-c/Tests/FoundationModelsCBindingsTests/BasicSystemModelTests.swift`
- `examples/simple_inference.py`, `examples/streaming_example.py`, `examples/transcript_processing.py`
- `docs/source/index.rst`, `getting_started.rst`, `basic_usage.rst`, `streaming.rst`,
  `guided_generation.rst`, `tools.rst`, `evaluation.rst`, `conf.py`
- `docs/source/api/attachment.rst`, `errors.rst`, `generable.rst`, `generation_options.rst`,
  `session.rst`, `systemmodel.rst`, `tools.rst`, `transcript.rst`
- `docs/README.md`, `docs/requirements.txt`, `docs/Makefile`
- `bin/build-distribution.sh`, `bin/clean.sh`, `bin/clean-build-files.sh`, `bin/install-git-hooks.sh`,
  `bin/git-pre-commit.sh`, `bin/publish-docs.sh`
- `tests/conftest.py`, `tests/README.md`
- `tests/test_composed_prompt_cleanup.py`, `test_session.py`, `test_streaming.py`,
  `test_token_count.py`, `test_system_model.py`, `test_generable_protocol.py`,
  `test_json_guided_generation.py`, `test_guided_generation.py`, `test_error_handling.py`,
  `test_prompts.py`, `test_image_prompts.py`, `test_guides.py`, `test_memory_stress.py`
- `tests/tester_tools/tester_tools.py`, `tests/tester_schemas/schemas.py`,
  `tests/tester_schemas/schemas.swift`
- `tests/tester_schemas/hedgehog.json`, `person.json`, `cat.json`, `newsletter.json`,
  `test_transcript.json`, `test_transcript_full.json`
- `tests/doc_tests/test_readme_snippets.py`

Read **partially / by grep**:
- `tests/test_tool.py` (lines 1-340, 505-626 + structural grep)
- `tests/test_memory.py` (structural grep + lines 20-130, 232-330, 371-445, 691-780)
- `tests/test_transcript.py` (structural grep)
- `tests/test_generation_options.py` (lines 1-120)
- `tests/tester_schemas/validate_schemas.py` (lines 1-120)
- `tests/doc_tests/test_symbol_docs_core.py`, `test_symbol_docs_generable_utils.py` (partial)
- `bin/verify-license-header.sh` (not read; 230 lines)

Commands run:
- `git log --oneline -50`, `git branch -a`, `git remote -v`
- `git show e868e60 --stat`, `git show e868e60 -- src/`
- `git show db7afde --stat`, `git show da32e98 --stat`, `git show 3ff9c60 --stat`, `git show 8d56a2d --stat`
- `wc -l` across all source/test/doc files
- `python3{,.11,.12,.13,.14} -c ...` to characterise `str(Optional[int])` / `int | None` behaviour

Files **not** read: `CODE_OF_CONDUCT.md`, the remaining `tests/doc_tests/test_symbol_docs_*.py`,
`tests/doc_tests/test_doc_website_snippets.py` (982 lines), `tests/tester_schemas/{age,shelter,petClub}.json`,
`docs/source/_static/custom.css`, the two `.png/.jpeg` binaries.

---

## 22. Open questions / unverified

1. **Random-sampling string/Int mismatch (§10)** — I read both sides; I could not execute. Someone
   with a working install should run:
   `await session.respond("...", options=fm.GenerationOptions(sampling=fm.SamplingMode.random(top=1, seed=1)))`
   twice and check for identical output. If outputs differ, the seed is confirmed dead.
2. **Python 3.14 optional-detection regression (§7.3)** — the `str()` behaviour change is measured,
   but I could not run the SDK on 3.14 to confirm all properties become `required`.
3. **`respond(generating=..., options=...)` dropping options** — read from source; not executed.
4. Does `pip install apple-fm-sdk` from PyPI ship **prebuilt wheels**, or is it always an
   sdist→compile? `pyproject.toml`'s `package-data` implies wheels are possible, and
   `build_sdist` deliberately skips compiling; but there is no CI config in the repo and I have no
   network access to check PyPI. **UNVERIFIED.**
5. Which thread do tool callbacks actually land on? `Tool._c_callback_impl` has both an
   `asyncio.create_task` path and a "no running loop → new thread + new loop" path. I believe the
   latter is the normal path (Swift `Task.detached`), but did not observe it.
6. Whether `fm-c-example` crashes at runtime (it passes a `char*` where an `FMComposedPrompt` is
   expected). Not built.
7. Is there a `Package.resolved`? `MANIFEST.in` includes it but the file is not in the working tree —
   so the Swift package apparently has **zero external dependencies** (consistent with `Package.swift`).
8. Exact behaviour of `FMComposedPromptAddImage`/`AddIdentifiedImage` in the generated
   `_ctypes_bindings.py` — ctypesgen usually guards missing symbols, so they are probably simply
   absent from the module, but I could not inspect a generated file.
9. `GenerationSchemaWrapper` and `GenerationSchemaPropertyWrapper` are declared in the Swift file
   (lines 1349-1363) but appear unused — likely dead code from an earlier design.
10. No CI configuration (`.github/`) is present in this clone — how the project tests/releases is
    unknown.
11. Whether `session.respond()` can be given a `Generable` **instance** (the overload at
    session.py:314-320 says `generating: Generable`) — the implementation calls
    `generating.generation_schema()` and `generating._from_generated_content(...)`, both of which work
    on instances too via the classmethod, so it probably works. Untested anywhere.
