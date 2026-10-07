# Current Core AI verification evidence

Consolidated 2026-10-07. Native execution remains dated **2026-10-06**; moving these records is not a fresh execution. [The manifest](manifest.json) preserves original paths and byte hashes.

The separately reviewed source and runner revision is `893624e9a09adf991d87c191b91795986a82b422`. The verifier reads immutable Git blobs with isolated Python from a separate trusted runner; it never imports candidate helpers. Core packages: `coreai-core 1.0.0b3`, `coreai-torch 0.4.3`, `coreai-opt 0.3.0`.

| Sequential profile | Packages | Results |
|---|---|---|
| [Model export](native-model-export.json) | Torch 2.9.0, TorchAO 0.17.0 | 38 fixture outcomes, passed |
| [Standalone compression](native-standalone.json) | Torch 2.11.0, TorchAO 0.18.0 | 38 fixture outcomes, passed |

Records preserve every expected rejection, runner/helper/example hash, toolchain identity, package version, and fixture measurement. [Preflight](preflight.json) identifies the approved examples. [Fence hashes](python-fence-hashes.tsv) preserve their source provenance.

The distinct negative controls cover incorrect shapes/weights, non-finite output, required composites, range boundaries, overwrite/non-mutation, casting exclusions and entry/exit boundaries, overflow no-op substitution, and protected-result user counts. The verifier and portable tests continue to enforce these controls. Do not remove trust checks or relabel expected rejections as successful inference.

[Source verification](immutable-source-verification.json), [model-export package integrity](model-export-package-integrity.json), [standalone integrity](standalone-package-integrity.json), [wheel/source hashes](wheel-source-hashes.json), and [static API audit](static-api-audit.json) retain pin and API boundaries. Converter issue #49 is fixed in the tested 0.4.3 path; 0.4.2 remains unverified. Packed-intx PR #41 is merged but outside the inspected converter tag. Eager re-tying remains unsupported. Casting behavior is fixture-scoped, not a general numerical-quality guarantee.

[Fresh final-SDK Swift results](swift-final-results.tsv) and [toolchain identities](swift-toolchains.json) retain available SDK-27 checks and explicit unavailable SDK-26 targets. [Apple release captures](apple-release-captures.json) retain observed release sources. Current line positions and verification status live in the canonical snippet-verification ledger.

Reproduce native checks using each existing pinned profile, sequentially, from a separately reviewed clean runner:

```sh
<profile-python> -I <trusted-runner>/scripts/verify_coreai_examples.py \
  --source-repo <clean-source-at-reviewed-commit> \
  --reviewed-revision <full-reviewed-commit-sha> \
  --compression --out <durable-run-directory>/results.json
```

Resolved review narratives, superseded full-corpus reconciliation tables, and duplicate earlier native results remain recoverable from Git. Keep new evidence only if it updates current claims or demonstrates a distinct regression.
