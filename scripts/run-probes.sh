#!/usr/bin/env bash
# Run probes with every build product, log, and result bundle in one durable,
# ignored run directory. The source checkout is never used as a build location.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mode="${1:-}"
if [[ -z "$mode" ]]; then
  echo "usage: $0 host|simulator|device [--run-id ID] [--destination DESTINATION] [--team-id TEAM] [-- XCODEBUILD_ARGS...]" >&2
  exit 64
fi
shift

run_id="${PROBE_RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)-$$}"
destination=""
team_id="${DEVELOPMENT_TEAM:-}"
extra_arguments=()
extra_argument_count=0

while (($#)); do
  case "$1" in
    --run-id)
      [[ $# -ge 2 ]] || { echo "--run-id requires a value" >&2; exit 64; }
      run_id="$2"
      shift 2
      ;;
    --destination)
      [[ $# -ge 2 ]] || { echo "--destination requires a value" >&2; exit 64; }
      destination="$2"
      shift 2
      ;;
    --team-id)
      [[ $# -ge 2 ]] || { echo "--team-id requires a value" >&2; exit 64; }
      team_id="$2"
      shift 2
      ;;
    --)
      shift
      extra_arguments=("$@")
      extra_argument_count=$#
      break
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 64
      ;;
  esac
done

if [[ ! "$run_id" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]]; then
  echo "invalid run id '$run_id' (use letters, digits, '.', '_', and '-')" >&2
  exit 64
fi

automation_id="${AUTOMATION_ID:-manual-probes}"
if [[ ! "$automation_id" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]]; then
  echo "invalid AUTOMATION_ID '$automation_id'" >&2
  exit 64
fi

artifact_base="${PROBE_ARTIFACT_ROOT:-$repo_root/artifacts/freshness/$automation_id}"
run_root="$artifact_base/$run_id"
if [[ -e "$run_root" ]]; then
  echo "refusing to reuse artifact directory: $run_root" >&2
  exit 73
fi

mkdir -p "$run_root/Build" "$run_root/Logs" "$run_root/ProbeArtifacts" "$run_root/Results"
echo "Probe artifacts: $run_root"

run_logged() {
  local log_path="$1"
  shift
  set +e
  "$@" 2>&1 | tee "$log_path"
  local command_status=${PIPESTATUS[0]}
  set -e
  return "$command_status"
}

case "$mode" in
  host)
    if ((extra_argument_count)); then
      run_logged "$run_root/Logs/swift-test.log" \
        swift test \
        --package-path "$repo_root/probes" \
        --scratch-path "$run_root/Build/SwiftPM" \
        "${extra_arguments[@]}"
    else
      run_logged "$run_root/Logs/swift-test.log" \
        swift test \
        --package-path "$repo_root/probes" \
        --scratch-path "$run_root/Build/SwiftPM"
    fi
    ;;
  simulator|device)
    if [[ "$mode" == "simulator" ]]; then
      destination="${destination:-${PROBE_SIMULATOR_DESTINATION:-platform=iOS Simulator,name=iPhone 17 Pro,OS=latest}}"
    else
      [[ -n "$destination" ]] || {
        echo "device mode requires --destination 'platform=iOS,id=<device-udid>'" >&2
        exit 64
      }
      [[ -n "$team_id" ]] || {
        echo "device mode requires --team-id or DEVELOPMENT_TEAM" >&2
        exit 64
      }
    fi

    command -v xcodegen >/dev/null 2>&1 || {
      echo "xcodegen is required (install with: brew install xcodegen)" >&2
      exit 69
    }

    project_dir="$run_root/Build/Project"
    mkdir -p "$project_dir"
    xcodegen generate \
      --spec "$repo_root/probes/device-project.yml" \
      --project "$project_dir" \
      --project-root "$repo_root/probes"
    # XcodeGen keeps ordinary source groups relative to --project-root, but a
    # folder resource uses SOURCE_ROOT. Bridge that one folder inside the
    # disposable generated-project directory instead of generating in source.
    ln -s "$repo_root/probes/DeviceProbeAssets" "$project_dir/DeviceProbeAssets"

    xcode_arguments=(
      test
      -project "$project_dir/DeviceProbes.xcodeproj"
      -scheme DeviceProbes
      -destination "$destination"
      -derivedDataPath "$run_root/Build/DerivedData"
      -resultBundlePath "$run_root/Results/DeviceProbes.xcresult"
    )
    if [[ "$mode" == "device" ]]; then
      xcode_arguments+=(
        -allowProvisioningUpdates
        "DEVELOPMENT_TEAM=$team_id"
      )
    fi
    if ((extra_argument_count)); then
      xcode_arguments+=("${extra_arguments[@]}")
    fi

    export PROBE_ARTIFACT_DIR="$run_root/ProbeArtifacts"
    run_logged "$run_root/Logs/xcodebuild-test.log" xcodebuild "${xcode_arguments[@]}"
    ;;
  *)
    echo "unknown mode '$mode' (expected host, simulator, or device)" >&2
    exit 64
    ;;
esac
