# Agent Skills for Apple's on-device AI stack

Generated from [`guides/`](../guides/) — the canonical corpus. Edit the guides and run `./scripts/build-skills.sh`; never edit anything in this directory by hand.

Install every skill for Codex into the current project:

```bash
npx skills add hbmartin/Foundation-Models-and-Core-AI-and-MLX-skills --skill '*' --agent codex
```

Install every skill for Claude Code into the current project:

```bash
npx skills add hbmartin/Foundation-Models-and-Core-AI-and-MLX-skills --skill '*' --agent claude-code
```

Or install just one skill by replacing `'*'` with its name. Project-scoped installs are recommended because their target directory is explicit and can be checked into git.

```bash
npx skills add hbmartin/Foundation-Models-and-Core-AI-and-MLX-skills --skill apple-foundation-models --agent codex
```

| Skill | Covers | What it is for |
|---|---|---|
| `apple-on-device-ai` | Part 1 | Choose among Apple Foundation Models, Core AI, MLX, Metal, or Core ML for on-device inference, and apply OS, SDK, hardware, and availability gates across Apple platforms. Use when selecting a stack; writing @available or SystemLanguageModel.availability checks; resolving 26.0, 26.2, 26.4, or 27.0 floors; diagnosing code that compiles but is unavailable at runtime; or routing an unfamiliar symbol, error, or silent failure to the owning framework. |
| `apple-foundation-models` | Part 2, 3, 4, 5 | Build and debug apps using Apple's Foundation Models framework: LanguageModelSession, @Generable, @Guide, streaming, tools, the Instructions-versus-Prompt trust boundary, context and KV cache, DynamicProfile, custom LanguageModel backends, Playground, Instruments, and fm CLI. Use for import FoundationModels; unconstrained guided output; hung respond(to:); guardrail refusals; LanguageModelError or exceededContextWindowSize; prompt injection; tool loops; or non-Apple backends behind the same API. |
| `apple-ai-evaluations` | Part 6, 16.5 | Measure and regression-test on-device model output with Apple's Evaluations framework: eval harnesses, prompt hill-climbing, model-as-judge graders and alignment, synthetic or adversarial data, and tool-trajectory scoring; also use DNIKit to audit datasets and networks before conversion. Use when scoring generations, calibrating graders, checking agent tool order, constructing eval sets, finding duplicate training data, or inspecting excess network width. |
| `apple-core-ai` | Part 7, 8, 9, 10 | Build, convert, optimize, and debug Core AI 27 neural models using AIModel, NDArray, bundles, engines, guided decoding, specialization, caching, AOT compilation, coreai-torch conversion, custom Metal ops, quantization, palettization, pruning, and ANE/GPU profiling. Use for import CoreAI or .aimodel work; missing Metal compiler errors; unsupported conversion ops; Neural Engine fallback; slow compiled models; numeric drift; compression accuracy loss; or deciding what should remain in Core ML. |
| `apple-metal-tensorops` | Part 11 | Write and debug hand-built on-device ML kernels with Metal TensorOps and Metal Performance Primitives: MPP and MTLTensor APIs, quantized or multiplane operands, cooperative tensors, threadgroup and memory layout, and flash attention. Use when implementing an attention or tensor kernel, diagnosing a Metal performance cliff or numerical error, or determining whether a TensorOps surface is available in 26.x or only in 27. |
| `apple-mlx` | Part 12, 13, 14 | Build and debug MLX in Python or Swift: mx.array and lazy evaluation, unified memory, mx.compile and transforms, custom kernels, quantization, mlx-lm generation and prompt caching, serving, distributed inference, fine-tuning, model ports, mlx-swift-lm apps, tools, and bridges to Foundation Models or Core AI. Use for import mlx or mlx_lm; unevaluated arrays; recompilation storms; memory growth; quantization drift; checkpoint port failures; or MLX/Core AI conversion. |
| `apple-ai-shipping` | Part 15 | Ship and operate on-device AI models in released Apple apps: distribution outside the app binary, background asset packs and updates, download and disk budgets, memory pressure and jetsam, thermal throttling, and honest inference benchmarks. Use when choosing an update channel, diagnosing termination or throttling mid-inference, sizing deployed assets, or designing and interpreting cold-start, steady-state, memory, power, and thermal measurements. |
| `apple-speech` | Part 16.1 | Build and debug speech-to-text with Apple's Speech framework: SpeechAnalyzer, SpeechTranscriber, DictationTranscriber, AssetInventory installation, custom vocabulary, live or file transcription, AnalyzerInputConverter, and volatile versus finalized results. Use for empty transcripts with a clean console, truncated final sentences, duplicated merged phrases, ignored vocabulary, asset or audio-format problems, or determining whether this framework provides speech generation. |
| `apple-app-intents` | Part 16.2, 16.3, 16.4 | Expose app content and actions to Siri and Apple Intelligence with App Intents, assistant schema domains, IntentParameter.valueState, AppEntity, IndexedEntity and Spotlight indexing, on-screen awareness, FileEntityIdentifier and FileRepresentation, display representations, and .system.searchInApp fallbacks. Use when an intent reports success but changes nothing, Siri uses screen text instead of an entity, clarification selects the wrong item, attachments are refused, or indexed content is invented. |
| `apple-ai-migration` | Part 17 | Migrate a shipping Apple AI app or model pipeline from the 26 SDK generation to 27: changed APIs, the Foundation Models Adapter sunset, LanguageModelError taxonomy changes, dual-SDK builds, Core ML-to-Core AI decisions, Metal toolchain requirements, and asset compatibility. Use when old code stops compiling or loading under Xcode 27, an Adapter is rejected, error cases moved, one codebase must support both SDKs, or a neural Core ML model should become .aimodel. |

Each skill's `SKILL.md` is a router: it carries the evidence-marker legend, the version floors, a triage table, and a lookup protocol. The bulk of the material sits in `references/`, which costs nothing until read — the part READMEs, a symbol index sliced to that skill, a silent-failure index sliced to that skill, and section maps addressing the bundled deep reference guides. Each skill also includes OpenAI UI metadata and portable trigger-evaluation fixtures.

Generated 2026-08-03.
