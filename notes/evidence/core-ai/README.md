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

## Historical issue #49 regression

**COMMUNITY-MEASURED**, preserved from the guide at `9faa6496593b5e67173e6b62e8424df7e07ae973` and
[the original issue](https://github.com/apple/coreai-torch/issues/49). This archival edit does not
assert a fresh issue lookup or native execution. Reporter `dkomoroske` filed the regression on
2026-07-23, also as **FB23695952**, with `coreai-torch 0.4.1`, `coreai-core 1.0.0b2`,
Torch 2.11.0, Python 3.12.13, and macOS 27 builds `26A5378j` / `26A5388g`.

The trigger was the expanded squared-distance expression
`D[i,j] = ‖xᵢ‖² − 2·z[i,j] + ‖yⱼ‖²`, with `z` supplied directly or computed as
`x @ y.transpose(-1, -2)`. The separate 0.4.1 optimizer removed the axis move of the `y`
norms from `(1,N,1)` to `(1,1,N)`. The wrong operand still broadcast for square inputs,
producing plausible output with the expected shape. Summing with `keepdim=True` did not fix it.

| Reporter fixture | Separate optimization | Maximum absolute error |
|---|---|---|
| Original or keepdim, 32×32 | Bypassed | `1.907e-06` |
| Original or keepdim, 32×32 | Enabled | `1.022e+01` |
| Reordered `(‖x‖² + ‖y‖²) − 2·z`, 32×32 | Either | `3.815e-06` |

The asymmetric 17×23 control and the norm-sum-only control passed; `cpu_only()` reproduced the
square-input failure. The larger GeoTransformer fixture measured about 17 dB PSNR with
optimization and 78–85 dB when bypassed. These are community fixture measurements, not general
quality thresholds. Historical 0.4.1 workarounds were bypassing the separate optimizer or
reordering the algebra as above.

The reporter's **2026-10-02** retest passed all three minimal patterns with maximum absolute
errors `1.907e-06` to `3.815e-06` using `coreai-torch 0.4.3` / `coreai-core 1.0.0b3` on an M5,
macOS 27.2 `26B5091g`, and Xcode 27.2 `27B5028f`. The issue closed as completed; **0.4.2 remains
unverified**. The retest did not establish full end-to-end registration parity or an expanded
boundary sweep. The separate optimizer is absent in 0.4.3: `to_coreai()` returns an already
optimized program. Use the [shipped-asset parity gate](../../../guides/part-08-coreai-pytorch-conversion/references/01-conversion-and-the-io-contract.md#114-️-the-shipped-asset-parity-gate)
and [current defect register](../../../guides/part-08-coreai-pytorch-conversion/references/02-op-coverage-composites-and-externalization.md#97-the-register)
with production shapes and value ranges. The distinct native evidence above retains its original
2026-10-06 execution date and trusted-runner provenance.
