# Core AI 0.4.3 / coreai-opt 0.3.0 refresh evidence

Audit date: **2026-10-06**. Reviewed starting guide revision:
`9a7d5920754e0889bb7533726d0f8b5b4a6b9a0e` on PR #48.
This record distinguishes implementation inspection, portable checks, native fixture execution,
and dated upstream/community measurements. Source inspection is not runtime verification.

## Immutable source contract

| Source | Revision | Use |
|---|---|---|
| [apple/coreai-torch](https://github.com/apple/coreai-torch/tree/b51fd006d978b6db7debef2566a373e258d91ba4) | `b51fd006` / 0.4.3 | Converter lifetime, op/sub-byte behavior, release boundary |
| [apple/coreai-optimization](https://github.com/apple/coreai-optimization/tree/189612be60bc1d5cca9b73ad8811660f738c637d) | `189612be` / 0.3.0 | Compression implementation, signatures, presets, dependencies and restrictions |
| [apple/coreai-models](https://github.com/apple/coreai-models/tree/db63a2d897b5df8adfe521ff0c20babba3500c11) | `db63a2d8` | Export compatibility pins and model recipes |
| Installed `coreai-core` wheel | `1.0.0b3` | Authoring rewrite, persistence and runtime; source hashes in [wheel-source-hashes.json](wheel-source-hashes.json) |

Implementation wins over conflicting release documentation. In particular, the tagged 0.3.0
integration docs still call the removed `AIProgram.optimize()` method. Current examples are
adaptations of those docs. Historical quotations in Parts 8 and 17 retain their original
0.4.1/b2 text, including `.optimize()`; they are not current instructions. The inspected
`mlx2coreai` 0.1.1 bridge retains its historical private API behavior without an inferred b3
compatibility claim.

## Coverage and claim dispositions

The review plan counted 140 Part 9 Python fences. The actual reviewed revision has **142**
(76 in 9.1, 48 in 9.2, 18 in 9.3; none in its README). All 142 were included, along with the README.
[python-fence-audit.tsv](python-fence-audit.tsv) records each original fence's section, hash,
retained/updated/replaced disposition, corresponding current ID and source scope, plus two new
replacement examples. [section-audit.tsv](section-audit.tsv) records the disposition and content
hash of 341 section groups, including their version-sensitive prose claims and retained dated
measurements. Sources that are SDK, Metal or MLX claims retain the pinned sources already cited
in those sections; the three Core AI repositories cannot establish their hardware claims.

[static-api-audit.json](static-api-audit.json) covers all 142 current fences: 123 AST-readable
examples and 19 signature/pseudocode fragments. Imported Core AI symbols and 125 directly
resolvable constructor/function calls were checked against the installed release signatures,
with zero import or keyword errors. This is a bounded static check: guide-local model/data
placeholders and whole training notebooks were not executed by that audit. Only the five named
fences in the native JSON records were executed by the native verifier.

| Version-sensitive claim / guide scope | Disposition | Authoritative source at pinned revision |
|---|---|---|
| Conversion, state protocol, summaries and diagrams in Parts 7/8/9/10/17 | Rewrite on successful exit from `with module:`, before `AIProgram(module)`; remove separate optimizer calls and ineffective options | `coreai-torch/coreai_torch/converter.py` and b3 `authoring/module.py` |
| b3 persistence and current pre-save deletion | Existing file/directory is replaced; remove redundant deletion | b3 `authoring/asset.py::AIProgram.save_asset`; native repeated save |
| Complete Part 10 export dependency profile | b3 / 0.4.3 / opt 0.3.0 / Torch 2.9.0 / TorchAO <0.18 | `coreai-models/python/pyproject.toml` at `db63a2d8` |
| Compression package and extras (all Part 9 headers) | Python >=3.11,<3.14; Torch >=2.8, TorchAO >=0.15 with no upper bounds; tested pairs recorded separately; CoreML optional | `coreai-optimization/pyproject.toml`, `Makefile`, `_utils/version_utils.py` |
| b3 cp314 inventory versus Part 9 Python limit | Include wheel; compression package still excludes 3.14 | Wheel inventory and compression `pyproject.toml` |
| Lifecycle, defaults, config precedence, presets (9.1 §§2–7) | Retain source-supported contracts; update backend/mmap boundaries | `base_model_compressor.py`, `quantization/{quantizer,config,spec}/`, `config/compression_config.py` |
| Graph/eager supported ops and numerical equivalence (9.1 §8) | 26 graph patterns; separate implementations, no numerical equivalence promise | `_graph/_annotation_pattern_registry.py`, `_eager/supported_ops_registry.py`, `quantization/quantizer.py` |
| Graph composite externalization (9.1 §8.9) | Released experimental graph path; complete native example with compressed reference | `_utils/torch_utils.py`, `_graph/quantizer.py`, converter externalized parameters |
| Observer constraints and block activations (9.1 §9, 9.3 §2) | Shape-aware per-channel behavior; block activation simulation released, built-in backend export rejects it | `_graph/_qspec_constraints.py`, `_utils/export_utils.py`; native prepare/finalize fixture |
| QAT/tied weights (9.1 §11) | Graph dtype/schedule conflict fixed in 0.3.0; eager warning/consistent shared configs retained | `_graph/quantizer.py`, `_eager/quantizer.py`; optimization #41 |
| KV-cache quantization (9.1 §12) | Graph-only state configuration retained; no new runtime/device claim | `_graph/quantizer.py`, `tests/quantization/test_kv_cache_quantization.py` |
| Casting return value and ignored ops (9.1 §14) | Mutates and returns same ExportedProgram; exclusions accept op packets/overloads or predicate | `casting/casting.py`; native exclusion fixture |
| Dynamic activation overflow calibration | Not released in 0.3.0; #117 merged October 2 after the tag | `casting/casting.py` release signature; post-tag PR #117 |
| Direct IR imports/signatures/default threshold/op sets (9.1 §15, 9.2 §12) | QScheme from `common`; preserve XOR rules and required `lut_dtype`; transform then serialize, no automatic frontend rewrite claim | `coreai_utils/{__init__,common}.py`, `coreai_utils/passes/` |
| Backend restrictions and root CoreML bug (9.1 §16, 9.3 §2.8) | Release restrictions retained; root regression fixed before 0.3.0 | Quantization/palettization `_export_utils.py`, optimization #15 |
| Graph/eager finalize cleanup and mmap (9.1 §2.6, 9.2 §10.3) | Both quantization modes remove dense originals; CoreAI/CPU/empty directory and file lifetime restrictions | `_graph/_prepare_for_export.py`, `_eager/_prepare_for_export.py`, `_utils/export_utils.py`; both native modes |
| Palettization fields, ops, defaults (9.2 §§2–7, 9.3 §2.5) | Six fields including training strategy; supported bit widths/granularities retained | `palettization/{config,spec,kmeans}/` |
| PAT/training strategy (9.2 §2.1) | training_mode/step/PATSchedule released; default freezes centroids/indices, custom strategy needed for learned centroids | `palettization/spec/training_strategy.py`, `config/palettization_config.py`, `kmeans/palettizer.py` |
| Sensitivities and clustering (9.2 §§8–9) | weights_only loading retained; exact scalar clustering and vector k-means++ implementation recorded | `kmeans_fake_palettize.py`, `_efficient_kmeans.py`, vendored `_kmeans1d` |
| Pruning signatures, schedules and negative axis (9.2 §11) | Floor rounding/schedules retained; negative-axis bug fixed before release | `pruning/{magnitude_pruner,config,spec}/`; optimization #45 |
| Joint compression (9.2 §13) | Palettize first with quantized LUT, then activation quantization; no sparsity speed promise | `tests/test_joint_compression.py`, release integration/export utilities; native fixture |
| Mixed precision and inspection (9.2 §§14–15) | Greedy search is pseudocode, not public helper; ModelInspector/format_summary and analytical BPW limitations recorded | `docs/src/utils/mixed_precision.md`, `inspection/{model_inspector,bits_per_weight}.py` |
| Model compression metrics helpers | Exact `check_divisibility`, `extract_layer_specs`, `compute_average_bitwidth` signatures replace unresolved gap | `coreai-models` compression exploration `compression_metrics.py` at `db63a2d8` |
| SDK numeric store set, ANE/Metal/MLX compute claims (9.3 §§3–6) | Retain their independently pinned SDK/Metal/MLX scope; no inference from Python release | Existing guide primary source footnotes |
| Defect registers and footguns | Fully qualify repository names; separate fixed release bugs, tag defects and post-release merges | Release code plus issue/PR status snapshot below |
| Published benchmarks (9.1 §18, 9.2 §§17/20, 9.3 §11) | Preserve values, hardware and dates; these are historical source measurements, not 0.3.0 remeasurements | Dated Apple example tables, WWDC26 session 325, `notes/repos/john-rocky-models.md` |
| TripoSplat optimizer stall | Retain historical report; remove upgrade recommendation; no public bypass, no claim resolved or reproduced on 0.4.3 | Archived report and 0.4.3's unrelated debug op-ID change |
| Artifact parity gates (8.1 §11.4, 8.2 §10.5) | Load the caller's RELEASE asset, check contracts/shapes/finiteness, separate export/runtime budgets, copy outputs inside context | Actual named guide fences and native negative fixtures |

## Defect status snapshot

These repository-qualified references avoid attributing optimizer issue numbers to the model
repository. Merge status does not imply that a fix is in an earlier tag.

| Reference | Status checked / release disposition |
|---|---|
| `apple/coreai-optimization#3` | Closed unmerged; historical export/conflict discussion, not a released feature |
| `apple/coreai-optimization#7` | Closed 2026-10-02; dynamic calibration fix in #117 is post-0.3.0 |
| `apple/coreai-optimization#15` | Merged 2026-08-03; root CoreML fix present in 0.3.0 |
| `apple/coreai-optimization#16` | Issue closed 2026-07-01; release uses weights_only sensitivity loading |
| `apple/coreai-optimization#22` | Merged 2026-07-14; current release code takes precedence over historical observer report |
| `apple/coreai-optimization#25` | Merged 2026-07-10; release-supported behavior retained |
| `apple/coreai-optimization#40` | Closed unmerged; do not equate this proposed rewrite with released annotation code |
| `apple/coreai-optimization#41` | Closed 2026-08-21; graph shared-weight conflict fixed in release implementation |
| `apple/coreai-optimization#42` | Merged 2026-07-20 (`56c4a362`); CoreML restriction checks present |
| `apple/coreai-optimization#44` | Merged 2026-07-22 (`012f3998`); palettization CoreML restriction checks present |
| `apple/coreai-optimization#45` | Merged 2026-08-03; pruning negative-axis fix present |
| `apple/coreai-optimization#52` | Merged 2026-07-24; shape-aware per-channel observer handling present |
| `apple/coreai-optimization#56` | Merged 2026-08-06; block activation simulation present, backend restriction remains |
| `apple/coreai-optimization#117` | Merged 2026-10-02, after 0.3.0; no calibration_data argument in release casting API |
| `apple/coreai-torch#24` | Merged 2026-07-08; negative quantization-axis correction present |
| `apple/coreai-torch#41` | Merged 2026-09-25, outside 0.4.3; packed cat dimension defect remains in that tag |
| `apple/coreai-torch#49` | Historical 32×32 failure versus 17×23 success; 0.4.3 path verified fixed October 2; 0.4.2 not established |

## Native fixture execution

Host: **Mac mini / Mac14,12 / Apple M2 Pro / 32 GB**, macOS **27.0 (26A428)**,
Xcode **27.0 (27A266a)**, Python **3.12.14**. Environments were isolated under no-space paths in
`/tmp`, with separate artifact directories. Final records:
[native-model-export.json](native-model-export.json),
[native-standalone.json](native-standalone.json).

| Profile | Torch | TorchAO | NumPy | Shared packages | Outcome |
|---|---|---|---|---|---|
| Model export | 2.9.0 | 0.17.0 | 2.4.6 | coreai-core 1.0.0b3, coreai-torch 0.4.3, coreai-opt 0.3.0, scikit-learn 1.9.1 | 24/24 fixtures passed |
| Standalone compression | 2.11.0 | 0.18.0 | 2.4.6 | Same | 24/24 fixtures passed |

The verifier executes guide fences selected by hidden IDs and records their code SHA-256:
`shipped-asset-gate`, `ci-asset-gate`, `state-protocol`, `compression-native-fixtures`, and
`composite-quantization`. Line positions may move with prose edits; IDs and code hashes identify
what was executed. The full raw fixture details are in the JSON files.

- Stateful demonstration: lengths 2, 8 and 32, consecutive updates, named sum/mean accumulators,
  repeat-run reset, asymmetric initial buffers and owned outputs after executable exit.
- Bounds 1/33 rejected by the application wrapper. Torch export specializes 0/1 dimensions and
  does not reliably enforce the declared minimum by itself; the guide explicitly records this
  limitation and enforces the 2–32 contract at the boundary.
- Shipping/CI gates load the supplied RELEASE path; its file bytes remain unchanged. Repeated b3
  save replaces the existing destination. Wrong weights, wrong shape, non-finite output and
  excessive runtime error are rejected. Runtime loader errors cannot count as parity rejection.
- Graph/eager INT8 quantization, graph/eager mmap finalize, scalar palettization, 50% magnitude
  pruning, joint compression, direct IR quantization/palettization/sparsification, casting
  exclusions, block activation simulation/restriction and graph composite externalization.
- Eligible weights have 4096 elements. BPW/observers/zero counts or emitted compression ops
  establish that compression occurred. Pruning produces 2048 zero weights. Quantization finalize
  checks that dense 4096-element floating originals are gone, including graph mode.
- Conversion is compared against the **prepared compressed reference captured before finalize**;
  quality against dense output is measured separately. INT8 conversion max absolute error was
  `2.98e-8` versus compression quality error `0.001646`; composite conversion error was `3.58e-7`
  versus quality error `0.009538` in both profiles. These are tiny fixture measurements, not model
  quality benchmarks. Direct IR fixtures check emitted compression ops, serialization, shape,
  finite runtime output and quality versus dense; they do not establish an independent exact
  compressed PyTorch reference for those IR transforms.

Initial attempts exposed two harness limitations: a virtualenv path containing spaces broke the
vendored Torch C++ JIT compiler command, and simultaneous writes to shared fixture asset paths
caused Core AI loader/cache errors. Final runs use no-space environments, separate artifact
paths and sequential profile execution. Their successful records supersede those failed runs;
the failures are not claimed as passing verification.

No CoreML runtime export was exercised (the optional CoreML extra requires NumPy <2.4), no ANE
placement/latency or iOS-device behavior was measured, and no full production models, training
runs or published benchmark tables were remeasured. Source-supported restrictions remain
labelled as such. Torch deprecation warnings were present but did not fail these fixtures.

## Reproduction and portable validation

From the repository root, create each Python 3.12 environment and install the exact profile:

```sh
uv venv --python python3.12 /tmp/coreai-030-model-export
uv pip install --python /tmp/coreai-030-model-export/bin/python 'torch==2.9.0' 'torchao==0.17.0' 'numpy==2.4.6' 'coreai-core==1.0.0b3' 'coreai-torch==0.4.3' 'coreai-opt==0.3.0' 'scikit-learn==1.9.1'
# Review the full immutable source commit and the separate clean runner first.
source_repo=/path/to/reviewed-source
runner_repo=/path/to/trusted-runner
reviewed_revision=<full-40-character-reviewed-commit-sha>
/tmp/coreai-030-model-export/bin/python -I "$runner_repo/scripts/verify_coreai_examples.py" \
  --source-repo "$source_repo" --reviewed-revision "$reviewed_revision" \
  --compression --out /tmp/coreai-native/model-export/results.json
uv venv --python python3.12 /tmp/coreai-030-standalone
uv pip install --python /tmp/coreai-030-standalone/bin/python 'torch==2.11.0' 'torchao==0.18.0' 'numpy==2.4.6' 'coreai-core==1.0.0b3' 'coreai-torch==0.4.3' 'coreai-opt==0.3.0' 'scikit-learn==1.9.1'
/tmp/coreai-030-standalone/bin/python -I "$runner_repo/scripts/verify_coreai_examples.py" \
  --source-repo "$source_repo" --reviewed-revision "$reviewed_revision" \
  --compression --out /tmp/coreai-native/standalone/results.json
```

Selecting the reviewed immutable revision establishes trust in the examples, which execute with
host privileges. Virtual environments isolate dependencies; they are not a code sandbox.
The runner rejects symbolic/abbreviated revisions, differing HEAD, local non-ignored edits,
malformed metadata, duplicate IDs, current optimizer calls, and optimized Python. Helpers come
only from verified runner blobs, and guide fences come only from approved Git blobs. Native
execution remains manual; portable CI does not invoke this verifier. Reports identify both
commits, helper/example hashes, package versions, and the actual OS and toolchain.

Run the two native commands sequentially. `scripts/coreai_examples.py` is the shared standard-library
fence/token reader. All 464 current Python fences across Parts 7/8/9/10/17 pass the removed optimizer
scan. Comments and strings are ignored; historical exemptions require valid version metadata.
Malformed fences/tokenization/metadata and duplicate IDs fail closed. Portable fixtures cover
assignments, chained calls, await/return, line continuation, nested blockquotes, backtick/tilde
fences, actual prior guide wording, and a subprocess timeout with 800 parenthesis pairs.

Final repository checks are recorded in [validation.md](validation.md). Generated indexes, skills,
callout classifications and Swift verification line records are reconciled in the final delivery
commit; unchanged Swift compiler verdicts are carried only with matching identity/content hash.
