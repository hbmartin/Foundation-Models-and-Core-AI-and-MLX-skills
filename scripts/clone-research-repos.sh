#!/usr/bin/env bash
# Re-clone the third-party repositories this guide series was researched against.
#
# These are NOT vendored into this repository (~628 MB, each with its own .git).
# The research notes in ../notes/ cite them by path, so run this from the repo root
# to make those citations resolvable again.
#
#   ./scripts/clone-research-repos.sh
#
# Each checkout is detached at the exact commit used by the research corpus. The
# fetch is intentionally shallow because reproducibility needs the recorded tree,
# not the moving default branch. Re-fetch without --depth if you need history.

set -euo pipefail

cd "$(dirname "$0")/.."
mkdir -p repos
cd repos

# Repository and exact research snapshot. Keep full SHAs so abbreviated-object
# ambiguity can never change what this script checks out.
REPOS=(
  "apple/python-apple-fm-sdk e868e60811aa0706feb2ccb33cfe7e27626287b7"
  "apple/foundation-models-utilities 376ca60e61985369d5067bd3c575bdb6a13f0e1b"
  "apple/coreai-models 5ed9981303b38d5a44aa6b45509bc4f6945029f5"
  "apple/coreai-torch 4529671d7d4d4c9800be178a9ce8af71c47abc3f"
  "apple/coreai-optimization cd95cb2545a586dbc14c85f5efd16b4635e5786c"
  "apple/dnikit 2f39056311d6e0fbbe4e5f73da3767a5b5070dac"
  "john-rocky/coreai-models 0fdf710774638ced1fc82783a1456835b4be1811"
  "john-rocky/coreai-model-zoo 9001528f028da237a53cadb8ef67481e274e9222"
  "ml-explore/mlx 973e27f82ffe68dbd626cda31ba34997045d1eb7"
  "ml-explore/mlx-lm e5baded8c1d286754edb479ffbde4655a68e2758"
  "ml-explore/mlx-examples 796f5b53cab69a3d48a44233ce21aae889e94a08"
  "ml-explore/mlx-swift-lm 3cbf928b5eb24190e8952725699ae6a3bb02824d"
  "ml-explore/mlx-swift-examples 378f2449c257788c5067b9f8b086731d76b39b33"
  "1amageek/swift-lm db7a8022c91857a0a1e7893101871872403ed190"
  "noemaai-labs/noema-ios 8366103f7bc8d9ed083680c6079af3f2ca7d2f89"
  "lucasnewman/mlx2coreai 059c9f365c9f48dc7d238cc37b0e30eb9d47fdbe"
)

for entry in "${REPOS[@]}"; do
  read -r slug expected_sha <<<"$entry"
  dir="${slug//\//__}"
  remote="https://github.com/$slug"
  actual_remote=""

  if [ ! -d "$dir/.git" ]; then
    echo "== $slug -> $dir"
    mkdir -p "$dir"
    git -C "$dir" init --quiet
    git -C "$dir" remote add origin "$remote"
  else
    actual_remote="$(git -C "$dir" remote get-url origin)"
    actual_remote="${actual_remote%.git}"
    if [ "$actual_remote" != "$remote" ]; then
      echo "!! REFUSING: $dir has an unexpected origin" >&2
      exit 1
    fi
  fi

  if ! git -C "$dir" cat-file -e "$expected_sha^{commit}" 2>/dev/null; then
    git -C "$dir" fetch --depth 1 origin "$expected_sha"
  fi
  git -C "$dir" checkout --quiet --detach "$expected_sha"

  actual_sha="$(git -C "$dir" rev-parse HEAD)"
  if [ "$actual_sha" != "$expected_sha" ]; then
    echo "!! FAILED: $slug expected $expected_sha, got $actual_sha" >&2
    exit 1
  fi
  echo "== $slug pinned at $actual_sha"
done

echo "Done. All research repositories match their recorded commits."
