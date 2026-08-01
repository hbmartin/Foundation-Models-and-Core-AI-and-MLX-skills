# Claude Code skills for Apple's on-device AI stack

Generated from [`guides/`](../guides/) — the canonical corpus. Edit the guides and run `./scripts/build-skills.sh`; never edit anything in this directory by hand.

Install every skill into the current project:

```bash
npx skills add hbmartin/Foundation-Models-and-Core-AI-and-MLX-skills --all
```

Or just the one you need, globally:

```bash
npx skills add hbmartin/Foundation-Models-and-Core-AI-and-MLX-skills --skill apple-foundation-models -g
```

| Skill | Covers | What it is for |
|---|---|---|
| `apple-on-device-ai` | Part 1 | Decide which Apple on-device AI stack a project should use - Foundation Models, Core AI, MLX or Metal - and get the platform, OS-version and hardware gates right across iOS, iPadOS, macOS, visionOS, tvOS and watchOS 26 and 27. Also the corpus-wide entry point: carries the full symbol index and silent-failure index for all 17 guide parts. |
| `apple-foundation-models` | Part 2, 3, 4, 5 | Apple's built-in on-device language model: LanguageModelSession, @Generable and @Guide guided generation, snapshot streaming, the Tool protocol and tool-calling loops, the Instructions-vs-Prompt trust boundary, context window and KV cache, DynamicProfile and session state, agentic orchestration, custom LanguageModel backends including Private Cloud Compute and ChatCompletionsLanguageModel, and prototyping with #Playground, Instruments and the fm CLI. |
| `apple-ai-evaluations` | Part 6, 16.5 | Apple's Evaluations framework, new in the 27 cycle with no back-deployment: building an eval harness for on-device model output, hill-climbing a prompt against it, model-as-judge graders and judge alignment, synthetic data generation, and tool-trajectory evaluation. Also DNIKit, for auditing a dataset or a network before you spend time converting it. |
| `apple-core-ai` | Part 7, 8, 9, 10 | Core AI, the new-in-27 runtime and the successor path for neural networks, while Core ML remains right for tree and non-neural models: import CoreAI, AIModel, NDArray, model bundles and engines, guided decoding, specialization, caching and ahead-of-time compilation - plus the Python side, converting a torch.nn.Module to an .aimodel with coreai-torch, op coverage and composites, custom Metal kernels, quantization, palettization and pruning, numeric formats, ANE-versus-GPU authoring rules, debugging, profiling and end-to-end LLM export. |
| `apple-metal-tensorops` | Part 11 | Metal TensorOps and Metal Performance Primitives for hand-written on-device ML kernels on Apple silicon: quantized operands, multiplane quantized tensors, cooperative tensors, and implementing flash attention in Metal. |
| `apple-mlx` | Part 12, 13, 14 | MLX on Apple silicon in both languages: mx.array, unified memory, lazy evaluation, mx.compile, function transforms, custom Metal kernels, quantization, numerics and hardware gating, the mlx-lm CLI with generation and prompt caching, serving and distributed inference, fine-tuning and porting models; MLX Swift with mlx-swift-lm in an app, generation, tools and caching, and the Foundation Models bridge; plus converting between MLX and Core AI. |
| `apple-ai-shipping` | Part 15 | Getting an on-device model out of development and into a shipping app: model distribution, background asset packs and model updates, memory budgets and jetsam, thermal throttling, and honest benchmarking of on-device inference. |
| `apple-speech` | Part 16.1 | Apple's 2026 Speech framework: SpeechAnalyzer, SpeechTranscriber and DictationTranscriber, asset installation through AssetInventory, custom vocabulary, live and file-based transcription, AnalyzerInputConverter, and volatile-versus-finalized results. |
| `apple-app-intents` | Part 16.2, 16.3, 16.4 | Making an app's content and actions available to Siri and Apple Intelligence: the assistant schema domains and the categories that have none, IntentParameter.valueState, AppEntity, IndexedEntity and indexAppEntities, on-screen awareness, FileEntityIdentifier and FileRepresentation, displayRepresentations, and .system.searchInApp as the fallback when no domain fits. |
| `apple-ai-migration` | Part 17 | Moving a shipping app or pipeline from the iOS/macOS 26 generation to 27: the what-changed checklist, the Foundation Models adapter sunset, the error-taxonomy migration, dual-SDK builds, Core ML to Core AI conversion, and toolchain and asset compatibility. |

Each skill's `SKILL.md` is a router: it carries the evidence-marker legend, the version floors, a triage table, and a lookup protocol. The bulk of the material sits in `references/`, which costs nothing until read — the part READMEs, a symbol index sliced to that skill, a silent-failure index sliced to that skill, and section maps addressing the deep reference guides that stay in this repository.

Generated 2026-08-01.
