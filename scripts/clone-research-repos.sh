#!/usr/bin/env bash
# Re-clone the third-party repositories this guide series was researched against.
#
# These are NOT vendored into this repository (~628 MB, each with its own .git).
# The research notes in ../notes/ cite them by path, so run this from the repo root
# to make those citations resolvable again.
#
#   ./scripts/clone-research-repos.sh
#
# Clones are shallow (--depth 50). That is enough for `git log`/`git show` on recent
# work, but NOT enough to date when a file was introduced — several notes flag this
# as a source of UNVERIFIED dates. Re-clone without --depth if you need real history.
#
# Snapshot taken 2026-07-27/28. HEADs recorded below are what the notes were written
# against; upstream will have moved.

set -euo pipefail

cd "$(dirname "$0")/.."
mkdir -p repos
cd repos

# repo                                        directory name
REPOS=(
  "apple/python-apple-fm-sdk"
  "apple/foundation-models-utilities"
  "apple/coreai-models"
  "apple/coreai-torch"
  "apple/coreai-optimization"
  "apple/dnikit"
  "john-rocky/coreai-models"
  "john-rocky/coreai-model-zoo"
  "ml-explore/mlx"
  "ml-explore/mlx-lm"
  "ml-explore/mlx-examples"
  "ml-explore/mlx-swift-lm"
  "ml-explore/mlx-swift-examples"
  "1amageek/swift-lm"
  "noemaai-labs/noema-ios"
  "lucasnewman/mlx2coreai"
)

for slug in "${REPOS[@]}"; do
  dir="${slug//\//__}"
  if [ -d "$dir/.git" ]; then
    echo "== $slug: already present, skipping"
    continue
  fi
  echo "== $slug -> $dir"
  git clone --depth 50 "https://github.com/$slug" "$dir" 2>&1 | tail -1 || {
    echo "!! FAILED: $slug (repo may have moved, been renamed, or gone private)" >&2
  }
done

echo
echo "Done. HEADs at the time the notes were written:"
cat <<'SNAPSHOT'
  apple__python-apple-fm-sdk        e868e60  2026-07-07  Release composed_prompt pointer in all respond() paths (#18)
  apple__foundation-models-utilities         2026-07-16  (only two commits exist; tags 1.0.0-beta1, 1.0.0-beta3)
  apple__coreai-models             5ed9981  2026-07-23  Move away from deprecated FM API (#123)
  apple__coreai-torch              4529671  2026-07-23  Remove run_transforms helper in favor of result.optimize() (#50)
  apple__coreai-optimization       cd95cb2  2026-07-24  fix: per-channel act quant fallback for shared observers (#52)
  apple__dnikit                    2f39056  2026-07-09  Handle Keras 3 tensor metadata in TF2 models (#4)
  john-rocky__coreai-models        0fdf710  2026-07-03  InferenceEngine: trimKVCache primitive for cross-turn prefix reuse
  john-rocky__coreai-model-zoo     9001528  2026-07-27  Open the device gate to contributors
  ml-explore__mlx                  973e27f  2026-07-24  [CUDA] Fix grid overflow in gemm conv unfold kernels
  ml-explore__mlx-lm               e5baded  2026-07-26  Support for Poolside LagunaXS in nvfp4 (#1334)
  ml-explore__mlx-examples         796f5b5  2026-04-06  Add wan 2.1 model (#1409)
  ml-explore__mlx-swift-lm         3cbf928  2026-07-24  Integration tests: build on both macOS 26 and 27 SDKs (#464)
  ml-explore__mlx-swift-examples   378f244  2026-06-16  MLXChatExample: fix VLM image handling on iOS (#472)
  1amageek__swift-lm               db7a802  2026-07-18  Add Core AI vision language model adapter
  noemaai-labs__noema-ios          (see repo)
  lucasnewman__mlx2coreai          059c9f3  2026-06-09  Add a swift runner as python bindings are incomplete as of now
SNAPSHOT
