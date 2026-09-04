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

# Finish mode-specific validation before reserving a durable run id. A typo or
# missing local tool must not consume an otherwise retryable automation run.
case "$mode" in
  host)
    command -v swift >/dev/null 2>&1 || {
      echo "swift is required" >&2
      exit 69
    }
    ;;
  simulator)
    destination="${destination:-${PROBE_SIMULATOR_DESTINATION:-platform=iOS Simulator,name=iPhone 17 Pro,OS=27.0}}"
    command -v xcodebuild >/dev/null 2>&1 || {
      echo "xcodebuild is required" >&2
      exit 69
    }
    command -v python3 >/dev/null 2>&1 || {
      echo "python3 is required" >&2
      exit 69
    }
    ;;
  device)
    [[ -n "$destination" ]] || {
      echo "device mode requires --destination 'platform=iOS,id=<device-udid>'" >&2
      exit 64
    }
    [[ -n "$team_id" ]] || {
      echo "device mode requires --team-id or DEVELOPMENT_TEAM" >&2
      exit 64
    }
    command -v xcodegen >/dev/null 2>&1 || {
      echo "xcodegen is required (install with: brew install xcodegen)" >&2
      exit 69
    }
    command -v xcodebuild >/dev/null 2>&1 || {
      echo "xcodebuild is required" >&2
      exit 69
    }
    ;;
  *)
    echo "unknown mode '$mode' (expected host, simulator, or device)" >&2
    exit 64
    ;;
esac

artifact_base="${PROBE_ARTIFACT_ROOT:-$repo_root/artifacts/freshness/$automation_id}"
run_root="$artifact_base/$run_id"
if [[ -e "$run_root" ]]; then
  echo "refusing to reuse artifact directory: $run_root" >&2
  exit 73
fi

mkdir -p "$run_root/Build" "$run_root/Logs" "$run_root/ProbeArtifacts" "$run_root/Results"
echo "Probe artifacts: $run_root"
export PROBE_ARTIFACT_DIR="$run_root/ProbeArtifacts"

run_logged() {
  local log_path="$1"
  shift
  set +e
  "$@" 2>&1 | tee "$log_path"
  local command_status=${PIPESTATUS[0]}
  set -e
  return "$command_status"
}

run_logged_in() {
  local working_directory="$1"
  local log_path="$2"
  shift 2
  set +e
  (cd "$working_directory" && "$@") 2>&1 | tee "$log_path"
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
  simulator)
    build_arguments=(
      build-for-testing
      -scheme Probes-Package
      -destination "$destination"
      -derivedDataPath "$run_root/Build/DerivedData"
    )
    if ((extra_argument_count)); then
      build_arguments+=("${extra_arguments[@]}")
    fi
    # The Swift-package simulator lane is intentionally tool-hosted. Existing
    # SIM-27 baselines were established against this topology; the app host is
    # device-only. Xcode sanitizes the test process environment, so inject the
    # supported probe knobs into the generated launch specification explicitly.
    run_logged_in "$repo_root/probes" "$run_root/Logs/xcodebuild-build-for-testing.log" \
      xcodebuild "${build_arguments[@]}"

    shopt -s nullglob
    xctestrun_files=("$run_root"/Build/DerivedData/Build/Products/*.xctestrun)
    shopt -u nullglob
    if ((${#xctestrun_files[@]} != 1)); then
      echo "expected one generated .xctestrun, found ${#xctestrun_files[@]}" >&2
      exit 70
    fi
    xctestrun_path="${xctestrun_files[0]}"

    probe_variable_names=(
      PROBE_AIMODEL_URL
      PROBE_ARTIFACT_DIR
      PROBE_CONCURRENT_SESSIONS
      PROBE_ENABLE_ATTACHMENT
      PROBE_ENABLE_GENERATOR
      PROBE_ENABLE_HOST_MODEL
      PROBE_ENABLE_PCC
      PROBE_ENUM_RUNS
      PROBE_INSTRUMENTS_WORKLOAD
      PROBE_WORKLOAD_ATTACH_SECONDS
      PROBE_WORKLOAD_SECONDS
    )
    probe_environment=()
    for variable_name in "${probe_variable_names[@]}"; do
      if [[ "${!variable_name+x}" == x ]]; then
        probe_environment+=("$variable_name=${!variable_name}")
      fi
    done
    python3 "$repo_root/scripts/inject-xctestrun-environment.py" \
      "$xctestrun_path" "${probe_environment[@]}"

    test_arguments=(
      test-without-building
      -xctestrun "$xctestrun_path"
      -destination "$destination"
      -resultBundlePath "$run_root/Results/Probes-Package.xcresult"
    )
    if ((extra_argument_count)); then
      test_arguments+=("${extra_arguments[@]}")
    fi
    run_logged_in "$repo_root/probes" "$run_root/Logs/xcodebuild-test.log" \
      xcodebuild "${test_arguments[@]}"
    ;;
  device)
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
    xcode_arguments+=(
      -allowProvisioningUpdates
      "DEVELOPMENT_TEAM=$team_id"
    )
    if ((extra_argument_count)); then
      xcode_arguments+=("${extra_arguments[@]}")
    fi

    run_logged "$run_root/Logs/xcodebuild-test.log" xcodebuild "${xcode_arguments[@]}"
    ;;
esac
