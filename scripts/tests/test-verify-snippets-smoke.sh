#!/usr/bin/env bash
# test-verify-snippets-smoke.sh — LOCAL-ONLY end-to-end smoke of the snippet
# verifier against the real toolchains (deliberately excluded from CI, like
# test-sdk-interface-capture.sh: needs Xcode 26.6 + the Xcode 27 beta).
#
# Re-runs the five planning-time spikes through the real pipeline and asserts
# the verdicts: (1) @Generable macro typechecks on 27, (2) and on 26,
# (3) xfail:26 compile:27 proves PrivateCloudComputeLanguageModel is 27-only,
# (4) Evaluations resolves via -F on 27, (5) sim27 target typechecks.
set -euo pipefail

SCRIPT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH='' cd -- "$SCRIPT_DIR/../.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

mkdir -p "$TMP/guides"
cat > "$TMP/guides/smoke.md" <<'MD'
# Smoke

```swift compile:26,27
import FoundationModels

@Generable
struct Recipe {
    @Guide(description: "A dish name")
    var name: String
    @Guide(.range(1...5))
    var difficulty: Int
}
```

```swift xfail:26 compile:27
import FoundationModels

let model = PrivateCloudComputeLanguageModel()
```

```swift compile:27 imports:Evaluations
let metric = Metric("Match")
```

```swift compile:sim27
import FoundationModels

let session = LanguageModelSession()
```

```swift compile:27 imports:FoundationModels
let session = LanguageModelSession()
let response = try await session.respond(to: "Hello",
    options: GenerationOptions(maximumResponseTokens: 10))
```
MD

set +e
out="$(python3 "$REPO_ROOT/scripts/verify-snippets.py" --guides "$TMP/guides" --jobs 4)"
rc=$?
set -e
echo "$out"
[ "$rc" -eq 0 ] || { echo "SMOKE FAIL: verifier exit $rc" >&2; exit 1; }

expect() {
    printf '%s\n' "$out" | grep -Eq "$1" || { echo "SMOKE FAIL: missing $1" >&2; exit 1; }
}
# Note: a fence carrying BOTH compile: and xfail: reports overall VERIFIED once
# both requirements hold; the per-target column shows the xfail-pass.
expect $'smoke.md\t3\t.*VERIFIED'                 # @Generable on both SDKs
expect $'smoke.md\t15\t.*VERIFIED.*xfail-pass'    # PCC absent on 26, present on 27
expect $'smoke.md\t21\t.*VERIFIED'                # Evaluations via -F
expect $'smoke.md\t25\t.*VERIFIED'                # sim27 target
expect $'smoke.md\t31\t.*VERIFIED'                # async-throws body wrap + imports: marker

echo "SMOKE OK"
