#!/usr/bin/env bash
# Capture the selected Xcode's macOS Swift interfaces and relevant CLI help.
#
# The capture is deliberately conservative: it verifies the selected Xcode,
# iPhoneOS SDK, and Metal Toolchain before creating any temporary or destination
# files. Existing evidence is immutable unless its manifest provenance and hash
# both match the fresh capture.
#
#   ./scripts/dump-sdk-interfaces.sh
#   ./scripts/dump-sdk-interfaces.sh --check-only
#   ./scripts/dump-sdk-interfaces.sh --dest /tmp/sdk-capture

set -euo pipefail

SCRIPT_DIR="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
REPO_ROOT="$(CDPATH='' cd -- "$SCRIPT_DIR/.." && pwd)"
DEST="$REPO_ROOT/notes/sdk-interfaces"
CHECK_ONLY=0

usage() {
  sed -n '2,12p' "$0"
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

need_value() {
  [ "$#" -ge 2 ] && [ -n "$2" ] || die "$1 needs a value"
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --dest)
      need_value "$@"
      DEST="$2"
      shift 2
      ;;
    --check-only)
      CHECK_ONLY=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown argument: $1"
      ;;
  esac
done

command -v python3 >/dev/null 2>&1 || die 'python3 is required'
command -v xcodebuild >/dev/null 2>&1 || die 'xcodebuild is required'
command -v xcrun >/dev/null 2>&1 || die 'xcrun is required'
command -v plutil >/dev/null 2>&1 || die 'plutil is required'

# ---- Read-only preflight. DEVELOPER_DIR is intentionally left untouched: ------
# xcodebuild and xcrun honor it natively, which makes the selected developer
# directory per-process rather than mutating global xcode-select state.

XCODE_VERSION_OUTPUT="$(xcodebuild -version 2>/dev/null)" || \
  die 'the selected developer directory does not contain a usable Xcode'
XCODE_VERSION="$(printf '%s\n' "$XCODE_VERSION_OUTPUT" | sed -n '1s/^Xcode[[:space:]]*//p')"
XCODE_BUILD="$(printf '%s\n' "$XCODE_VERSION_OUTPUT" | sed -n '2s/^Build version[[:space:]]*//p')"
[ -n "$XCODE_VERSION" ] && [ -n "$XCODE_BUILD" ] || \
  die 'could not parse xcodebuild -version'
XCODE_MAJOR="${XCODE_VERSION%%.*}"
case "$XCODE_MAJOR" in
  ''|*[!0-9]*) die "unrecognized Xcode version: $XCODE_VERSION" ;;
esac
[ "$XCODE_MAJOR" -ge 27 ] || die "Xcode 27 or newer is required (selected: $XCODE_VERSION)"

IPHONE_SDK_VERSION="$(xcrun --sdk iphoneos --show-sdk-version 2>/dev/null)" || \
  die 'the selected Xcode has no iPhoneOS SDK'
IPHONE_SDK_BUILD="$(xcrun --sdk iphoneos --show-sdk-build-version 2>/dev/null)" || \
  die 'could not read the selected iPhoneOS SDK build'
xcrun --sdk iphoneos --show-sdk-path >/dev/null 2>&1 || \
  die 'could not resolve the selected iPhoneOS SDK'
IPHONE_SDK_MAJOR="${IPHONE_SDK_VERSION%%.*}"
case "$IPHONE_SDK_MAJOR" in
  ''|*[!0-9]*) die "unrecognized iPhoneOS SDK version: $IPHONE_SDK_VERSION" ;;
esac
[ "$IPHONE_SDK_MAJOR" -ge 27 ] || \
  die "iPhoneOS SDK 27 or newer is required (selected: $IPHONE_SDK_VERSION)"

MACOS_SDK_VERSION="$(xcrun --sdk macosx --show-sdk-version 2>/dev/null)" || \
  die 'the selected Xcode has no macOS SDK'
MACOS_SDK_BUILD="$(xcrun --sdk macosx --show-sdk-build-version 2>/dev/null)" || \
  die 'could not read the selected macOS SDK build'
MACOS_SDK_PATH="$(xcrun --sdk macosx --show-sdk-path 2>/dev/null)" || \
  die 'could not resolve the selected macOS SDK'
MACOS_PLATFORM_PATH="$(xcrun --sdk macosx --show-sdk-platform-path 2>/dev/null)" || \
  die 'could not resolve the selected macOS platform'
[ -n "$MACOS_SDK_VERSION" ] && [ -n "$MACOS_SDK_BUILD" ] || \
  die 'the selected macOS SDK has incomplete version metadata'

COREAI_BUILD_PATH="$(xcrun --no-cache --find coreai-build 2>/dev/null)" || \
  die 'coreai-build is missing; install the selected Xcode Metal Toolchain component'
METAL_PATH="$(xcrun --no-cache --find metal 2>/dev/null)" || \
  die 'metal is missing; install the selected Xcode Metal Toolchain component'

toolchain_root() {
  case "$1" in
    *.xctoolchain/*) printf '%s.xctoolchain\n' "${1%%.xctoolchain/*}" ;;
    *) return 1 ;;
  esac
}

COREAI_TOOLCHAIN_ROOT="$(toolchain_root "$COREAI_BUILD_PATH")" || \
  die 'coreai-build did not resolve from an .xctoolchain component'
METAL_TOOLCHAIN_ROOT="$(toolchain_root "$METAL_PATH")" || \
  die 'metal did not resolve from an .xctoolchain component'
COREAI_TOOLCHAIN_ROOT="$(CDPATH='' cd -- "$COREAI_TOOLCHAIN_ROOT" && pwd -P)" || \
  die 'could not resolve the coreai-build toolchain root'
METAL_TOOLCHAIN_ROOT="$(CDPATH='' cd -- "$METAL_TOOLCHAIN_ROOT" && pwd -P)" || \
  die 'could not resolve the metal toolchain root'
[ "$COREAI_TOOLCHAIN_ROOT" = "$METAL_TOOLCHAIN_ROOT" ] || \
  die 'coreai-build and metal resolve from different toolchain components'

TOOLCHAIN_INFO="$COREAI_TOOLCHAIN_ROOT/ToolchainInfo.plist"
[ -f "$TOOLCHAIN_INFO" ] || die 'the selected Metal Toolchain has no ToolchainInfo.plist'
TOOLCHAIN_IDENTIFIER="$(plutil -extract Identifier raw -o - "$TOOLCHAIN_INFO" 2>/dev/null)" || \
  die 'could not read Identifier from Metal Toolchain ToolchainInfo.plist'
[ -n "$TOOLCHAIN_IDENTIFIER" ] || die 'the Metal Toolchain identifier is empty'

COMPONENT_INFO="$(xcodebuild -showComponent MetalToolchain 2>/dev/null)" || \
  die 'xcodebuild does not report an installed MetalToolchain component'
COMPONENT_STATUS="$(printf '%s\n' "$COMPONENT_INFO" | sed -n 's/^Status:[[:space:]]*//p')"
COMPONENT_BUILD="$(printf '%s\n' "$COMPONENT_INFO" | sed -n 's/^Build Version:[[:space:]]*//p')"
COMPONENT_IDENTIFIER="$(printf '%s\n' "$COMPONENT_INFO" | sed -n 's/^Toolchain Identifier:[[:space:]]*//p')"
COMPONENT_SEARCH_PATH="$(printf '%s\n' "$COMPONENT_INFO" | sed -n 's/^Toolchain Search Path:[[:space:]]*//p')"
[ "$COMPONENT_STATUS" = 'installed' ] || die 'the selected MetalToolchain component is not installed'
[ -n "$COMPONENT_BUILD" ] && [ -n "$COMPONENT_IDENTIFIER" ] && [ -n "$COMPONENT_SEARCH_PATH" ] || \
  die 'xcodebuild returned incomplete MetalToolchain component metadata'
[ "$COMPONENT_IDENTIFIER" = "$TOOLCHAIN_IDENTIFIER" ] || \
  die 'MetalToolchain component identifier does not match ToolchainInfo.plist'
COMPONENT_TOOLCHAIN_ROOT="$(CDPATH='' cd -- "$COMPONENT_SEARCH_PATH/Metal.xctoolchain" && pwd -P)" || \
  die 'the reported MetalToolchain search path has no Metal.xctoolchain'
[ "$COMPONENT_TOOLCHAIN_ROOT" = "$COREAI_TOOLCHAIN_ROOT" ] || \
  die 'xcrun tools do not resolve from the MetalToolchain reported by the selected Xcode'

COREAI_BUILD_VERSION="$("$COREAI_BUILD_PATH" --version 2>&1 | sed -n '1p')" || \
  die 'coreai-build --version failed'
METAL_VERSION="$("$METAL_PATH" --version 2>&1 | sed -n '1p')" || \
  die 'metal --version failed'
[ -n "$COREAI_BUILD_VERSION" ] && [ -n "$METAL_VERSION" ] || \
  die 'tool version output was empty'

FM_PATH=''
FM_VERSION=''
FM_PRESENT=0
if FM_PATH="$(xcrun --no-cache --find fm 2>/dev/null)"; then
  FM_PRESENT=1
  FM_VERSION="$("$FM_PATH" --version 2>&1 | sed -n '1p' || true)"
else
  FM_PATH=''
fi

HOST_ARCH="$(uname -m)"
HOST_OS_VERSION="$(sw_vers -productVersion 2>/dev/null || true)"
HOST_OS_BUILD="$(sw_vers -buildVersion 2>/dev/null || true)"

# Validate all already-managed evidence before either --check-only or capture.
python3 - "$DEST" <<'PY'
import fnmatch
import hashlib
import json
import pathlib
import sys

dest = pathlib.Path(sys.argv[1])
patterns = ("*.swiftinterface", "*-help-*.txt", "*-key-declarations.md")

def is_artifact(name):
    return any(fnmatch.fnmatch(name, pattern) for pattern in patterns)

if not dest.exists():
    raise SystemExit(0)
if not dest.is_dir():
    raise SystemExit(f"error: destination is not a directory: {dest}")

artifact_names = sorted(p.name for p in dest.iterdir() if p.is_file() and is_artifact(p.name))
manifest_path = dest / "capture-manifest.json"
if not manifest_path.exists():
    if artifact_names:
        raise SystemExit("error: destination contains unmanaged capture artifacts (capture-manifest.json is missing)")
    raise SystemExit(0)

try:
    manifest_text = manifest_path.read_text(encoding="utf-8")
    if "/Users/" in manifest_text or "/Volumes/" in manifest_text:
        raise SystemExit("error: capture-manifest.json contains a machine-specific path")
    manifest = json.loads(manifest_text)
except (OSError, json.JSONDecodeError) as exc:
    raise SystemExit(f"error: invalid capture-manifest.json: {exc}")
if manifest.get("schema_version") != 1 or not isinstance(manifest.get("captures"), list):
    raise SystemExit("error: unsupported capture-manifest.json schema")

managed = {}
for capture in manifest["captures"]:
    for entry in capture.get("files", []):
        name = entry.get("path")
        digest = entry.get("sha256")
        source = entry.get("source")
        if not isinstance(name, str) or pathlib.PurePath(name).name != name:
            raise SystemExit("error: manifest artifact paths must be plain filenames")
        if source is not None and (not isinstance(source, str) or source.startswith("/")
                                   or "/Users/" in source or "/Volumes/" in source):
            raise SystemExit(f"error: manifest source for {name} is not normalized")
        if name in managed:
            raise SystemExit(f"error: manifest records {name} more than once")
        managed[name] = digest

RECOVERY_HINT = ("; if a capture was interrupted, see notes/sdk-interfaces/README.md "
                 "(Recovering from an interrupted capture)")
unmanaged = sorted(set(artifact_names) - set(managed))
missing = sorted(set(managed) - set(artifact_names))
if unmanaged:
    raise SystemExit("error: destination contains unmanaged capture artifacts: "
                     + ", ".join(unmanaged) + RECOVERY_HINT)
if missing:
    raise SystemExit("error: manifest-managed artifacts are missing: "
                     + ", ".join(missing) + RECOVERY_HINT)

for name, expected in sorted(managed.items()):
    data = (dest / name).read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected:
        raise SystemExit(f"error: manifest hash mismatch for {name}")
    entry = next(entry for capture in manifest["captures"] for entry in capture.get("files", [])
                 if entry["path"] == name)
    if entry.get("size_bytes") != len(data):
        raise SystemExit(f"error: manifest size mismatch for {name}")
    if entry.get("line_count") != data.count(b"\n"):
        raise SystemExit(f"error: manifest line-count mismatch for {name}")
PY

printf 'Selected Xcode %s (%s); macOS SDK %s (%s); iPhoneOS SDK %s (%s)\n' \
  "$XCODE_VERSION" "$XCODE_BUILD" "$MACOS_SDK_VERSION" "$MACOS_SDK_BUILD" \
  "$IPHONE_SDK_VERSION" "$IPHONE_SDK_BUILD"
printf 'Metal Toolchain %s (%s); %s; %s\n' \
  "$TOOLCHAIN_IDENTIFIER" "$COMPONENT_BUILD" "$COREAI_BUILD_VERSION" "$METAL_VERSION"
if [ -n "$FM_PATH" ]; then
  printf 'Optional fm CLI: present%s\n' "${FM_VERSION:+ ($FM_VERSION)}"
else
  printf 'Optional fm CLI: absent\n'
fi

if [ "$CHECK_ONLY" -eq 1 ]; then
  printf 'Preflight and destination integrity checks passed; no files written.\n'
  exit 0
fi

# ---- Capture everything into an isolated directory before touching DEST. ------

TMP="$(mktemp -d "${TMPDIR:-/tmp}/sdk-interface-capture.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT HUP INT TERM
CAPTURE_DIR="$TMP/capture"
mkdir -p "$CAPTURE_DIR"
SOURCE_MAP="$TMP/sources.tsv"
: > "$SOURCE_MAP"

FRAMEWORKS=(
  FoundationModels CoreAI CoreAIDelegates CoreAIRuntime CoreAIAsset CoreAICache
  CoreAICommon CoreAICompiler Vision _Vision_FoundationModels Evaluations Speech
  CoreSpotlight _CoreSpotlight_FoundationModels AppIntents MetalPerformancePrimitives
)
ABSENT_FRAMEWORKS=''

find_interface() {
  local fwdir="$1"
  local preferred_pattern="$2"
  local candidate
  [ -d "$fwdir" ] || return 1
  candidate="$(find "$fwdir" -type f -name '*.swiftinterface' -print 2>/dev/null | \
    LC_ALL=C sort | grep "$preferred_pattern" | head -n 1 || true)"
  if [ -z "$candidate" ]; then
    candidate="$(find "$fwdir" -type f -name '*.swiftinterface' -print 2>/dev/null | \
      LC_ALL=C sort | head -n 1 || true)"
  fi
  [ -n "$candidate" ] || return 1
  printf '%s\n' "$candidate"
}

printf '\nCapturing framework interfaces in a temporary directory:\n'
for fw in "${FRAMEWORKS[@]}"; do
  fwdir="$MACOS_SDK_PATH/System/Library/Frameworks/$fw.framework"
  preferred_pattern='arm64e-apple-macos'
  source_root="$MACOS_SDK_PATH"
  source_label='macosx-sdk'
  if [ ! -d "$fwdir" ]; then
    fwdir="$MACOS_SDK_PATH/System/Library/SubFrameworks/$fw.framework"
  fi
  if [ ! -d "$fwdir" ]; then
    fwdir="$MACOS_PLATFORM_PATH/Developer/Library/Frameworks/$fw.framework"
    # Xcode-bundled developer frameworks target ordinary arm64 hosts rather
    # than the OS SDK's arm64e slice. This also preserves the original
    # Evaluations evidence slice captured by this repository.
    preferred_pattern='/arm64-apple-macos'
    source_root="$MACOS_PLATFORM_PATH"
    source_label='macosx-platform'
  fi
  iface="$(find_interface "$fwdir" "$preferred_pattern" || true)"
  if [ -n "$iface" ]; then
    out_name="${fw}-${MACOS_SDK_VERSION}-macos.swiftinterface"
    cp "$iface" "$CAPTURE_DIR/$out_name"
    case "$iface" in
      "$source_root"/*) source_relative="$source_label/${iface#"$source_root"/}" ;;
      *) die "could not normalize the source for $fw" ;;
    esac
    printf '%s\t%s\n' "$out_name" "$source_relative" >> "$SOURCE_MAP"
    printf '  %-32s %6s lines -> %s\n' \
      "$fw" "$(wc -l < "$CAPTURE_DIR/$out_name" | tr -d ' ')" "$out_name"
  else
    ABSENT_FRAMEWORKS="${ABSENT_FRAMEWORKS}${ABSENT_FRAMEWORKS:+,}${fw}"
    # Same manifest bucket either way; the run output distinguishes a C/ObjC-only
    # framework (headers ship, no Swift interface) from one absent outright.
    if [ -d "$MACOS_SDK_PATH/System/Library/Frameworks/$fw.framework/Headers" ] || \
       [ -d "$MACOS_SDK_PATH/System/Library/SubFrameworks/$fw.framework/Headers" ] || \
       [ -d "$MACOS_PLATFORM_PATH/Developer/Library/Frameworks/$fw.framework/Headers" ]; then
      printf '  %-32s no Swift interface; C/ObjC headers present\n' "$fw"
    else
      printf '  %-32s absent from this SDK\n' "$fw"
    fi
  fi
done

COREAI_HELP_NAME="coreai-build-help-${MACOS_SDK_VERSION}.txt"
{
  printf '# coreai-build help surface\n'
  printf '# Version: %s\n' "$COREAI_BUILD_VERSION"
  printf '# Toolchain: %s\n' "$TOOLCHAIN_IDENTIFIER"
  for args in '--help' 'compile --help' 'package --help' 'inspect --help' 'metadata --help'; do
    printf '\n===== coreai-build %s =====\n' "$args"
    # Intentional word splitting: args is a fixed list above, never user input.
    # shellcheck disable=SC2086
    "$COREAI_BUILD_PATH" $args
  done
} > "$CAPTURE_DIR/$COREAI_HELP_NAME"
printf '%s\t%s\n' "$COREAI_HELP_NAME" \
  'metal-toolchain/Metal.xctoolchain/usr/bin/coreai-build' >> "$SOURCE_MAP"
printf '  %-32s -> %s\n' 'coreai-build help' "$COREAI_HELP_NAME"

if [ -n "$FM_PATH" ]; then
  FM_HELP_NAME="fm-help-${MACOS_SDK_VERSION}.txt"
  {
    printf '# fm help surface\n'
    [ -z "$FM_VERSION" ] || printf '# Version: %s\n' "$FM_VERSION"
    printf '\n===== fm --help =====\n'
    "$FM_PATH" --help
  } > "$CAPTURE_DIR/$FM_HELP_NAME"
  printf '%s\t%s\n' "$FM_HELP_NAME" 'xcrun/fm' >> "$SOURCE_MAP"
  printf '  %-32s -> %s\n' 'fm help' "$FM_HELP_NAME"
fi

if [ -n "${HOME:-}" ] && grep -R -F -q "$HOME" "$CAPTURE_DIR"; then
  die 'a captured artifact contains the current home-directory path'
fi
if grep -R -E -q '/Users/|/Volumes/' "$CAPTURE_DIR"; then
  die 'a captured artifact contains a machine-specific user or volume path'
fi

CAPTURED_AT="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
CAPTURE_ID="xcode-${XCODE_BUILD}-macosx-${MACOS_SDK_VERSION}-${MACOS_SDK_BUILD}-iphoneos-${IPHONE_SDK_BUILD}-metal-${COMPONENT_BUILD}-${TOOLCHAIN_IDENTIFIER//./-}"
MERGED_MANIFEST="$TMP/capture-manifest.json"
ADDITIONS="$TMP/additions.txt"

export SDK_CAPTURE_ID="$CAPTURE_ID"
export SDK_CAPTURED_AT="$CAPTURED_AT"
export SDK_XCODE_VERSION="$XCODE_VERSION"
export SDK_XCODE_BUILD="$XCODE_BUILD"
export SDK_MACOS_VERSION="$MACOS_SDK_VERSION"
export SDK_MACOS_BUILD="$MACOS_SDK_BUILD"
export SDK_IPHONEOS_VERSION="$IPHONE_SDK_VERSION"
export SDK_IPHONEOS_BUILD="$IPHONE_SDK_BUILD"
export SDK_HOST_ARCH="$HOST_ARCH"
export SDK_HOST_OS_VERSION="$HOST_OS_VERSION"
export SDK_HOST_OS_BUILD="$HOST_OS_BUILD"
export SDK_METAL_COMPONENT_BUILD="$COMPONENT_BUILD"
export SDK_METAL_IDENTIFIER="$TOOLCHAIN_IDENTIFIER"
export SDK_COREAI_VERSION="$COREAI_BUILD_VERSION"
export SDK_METAL_VERSION="$METAL_VERSION"
export SDK_FM_PRESENT="$FM_PRESENT"
export SDK_FM_VERSION="$FM_VERSION"
export SDK_ABSENT_FRAMEWORKS="$ABSENT_FRAMEWORKS"

python3 - "$DEST" "$CAPTURE_DIR" "$SOURCE_MAP" "$MERGED_MANIFEST" > "$ADDITIONS" <<'PY'
import fnmatch
import hashlib
import json
import os
import pathlib
import re
import sys

dest = pathlib.Path(sys.argv[1])
stage = pathlib.Path(sys.argv[2])
source_map_path = pathlib.Path(sys.argv[3])
manifest_out = pathlib.Path(sys.argv[4])
manifest_path = dest / "capture-manifest.json"

if manifest_path.exists():
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
else:
    manifest = {"schema_version": 1, "captures": []}

owners = {}
capture_by_id = {}
for capture in manifest["captures"]:
    capture_id = capture.get("capture_id")
    if not isinstance(capture_id, str) or capture_id in capture_by_id:
        raise SystemExit("error: capture IDs must be unique strings")
    capture_by_id[capture_id] = capture
    for entry in capture.get("files", []):
        name = entry["path"]
        if name in owners:
            raise SystemExit(f"error: manifest records {name} more than once")
        owners[name] = (capture, entry)

sources = {}
for line in source_map_path.read_text(encoding="utf-8").splitlines():
    name, source = line.split("\t", 1)
    if name in sources or pathlib.PurePath(name).name != name or source.startswith("/"):
        raise SystemExit("error: invalid normalized source map")
    sources[name] = source

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def kind_and_framework(name):
    match = re.match(r"(.+)-([0-9]+(?:\.[0-9]+)*)-macos\.swiftinterface$", name)
    if match:
        return "swiftinterface", match.group(1)
    if name.startswith("coreai-build-help-"):
        return "cli-help", "coreai-build"
    if name.startswith("fm-help-"):
        return "cli-help", "fm"
    return "capture-artifact", None

current_id = os.environ["SDK_CAPTURE_ID"]
current_metadata = {
    "capture_id": current_id,
    "captured_at": os.environ["SDK_CAPTURED_AT"],
    "provenance": "scripted-capture",
    "xcode": {
        "version": os.environ["SDK_XCODE_VERSION"],
        "build": os.environ["SDK_XCODE_BUILD"],
    },
    "sdks": {
        "macosx": {
            "version": os.environ["SDK_MACOS_VERSION"],
            "build": os.environ["SDK_MACOS_BUILD"],
        },
        "iphoneos": {
            "version": os.environ["SDK_IPHONEOS_VERSION"],
            "build": os.environ["SDK_IPHONEOS_BUILD"],
        },
    },
    "host": {
        "architecture": os.environ["SDK_HOST_ARCH"],
        "os_version": os.environ["SDK_HOST_OS_VERSION"] or None,
        "os_build": os.environ["SDK_HOST_OS_BUILD"] or None,
    },
    "metal_toolchain": {
        "component_build": os.environ["SDK_METAL_COMPONENT_BUILD"],
        "identifier": os.environ["SDK_METAL_IDENTIFIER"],
        "coreai_build_version": os.environ["SDK_COREAI_VERSION"],
        "metal_version": os.environ["SDK_METAL_VERSION"],
        "coreai_build_path": "Metal.xctoolchain/usr/bin/coreai-build",
        "metal_path": "Metal.xctoolchain/usr/bin/metal",
    },
    "optional_tools": {
        "fm": ({"present": True, "version": os.environ["SDK_FM_VERSION"] or None}
               if os.environ["SDK_FM_PRESENT"] == "1" else {"present": False})
    },
    "absent_or_non_swift_frameworks": [
        item for item in os.environ["SDK_ABSENT_FRAMEWORKS"].split(",") if item
    ],
    "files": [],
}

current_capture = capture_by_id.get(current_id)
if current_capture is not None:
    for key in ("xcode", "sdks", "metal_toolchain"):
        if current_capture.get(key) != current_metadata[key]:
            raise SystemExit(f"error: capture ID {current_id} has conflicting {key} metadata")

additions = []
new_entries = []
for source in sorted(p for p in stage.iterdir() if p.is_file()):
    name = source.name
    if name not in sources:
        raise SystemExit(f"error: no normalized source recorded for {name}")
    digest = sha256(source)
    owner = owners.get(name)
    target = dest / name
    if target.exists():
        if owner is None:
            raise SystemExit(f"error: refusing to replace unmanaged artifact {name}")
        owner_capture, owner_entry = owner
        owner_build = owner_capture.get("xcode", {}).get("build")
        if owner_build != os.environ["SDK_XCODE_BUILD"]:
            raise SystemExit(
                f"error: refusing cross-build replacement of {name} "
                f"({owner_build or 'unknown'} -> {os.environ['SDK_XCODE_BUILD']})"
            )
        comparisons = (
            ("macOS SDK version", owner_capture.get("sdks", {}).get("macosx", {}).get("version"),
             os.environ["SDK_MACOS_VERSION"]),
            ("macOS SDK build", owner_capture.get("sdks", {}).get("macosx", {}).get("build"),
             os.environ["SDK_MACOS_BUILD"]),
            ("iPhoneOS SDK version", owner_capture.get("sdks", {}).get("iphoneos", {}).get("version"),
             os.environ["SDK_IPHONEOS_VERSION"]),
            ("iPhoneOS SDK build", owner_capture.get("sdks", {}).get("iphoneos", {}).get("build"),
             os.environ["SDK_IPHONEOS_BUILD"]),
            ("Metal Toolchain identifier", owner_capture.get("metal_toolchain", {}).get("identifier")
             if owner_capture.get("metal_toolchain") else None, os.environ["SDK_METAL_IDENTIFIER"]),
            ("Metal Toolchain component build", owner_capture.get("metal_toolchain", {}).get("component_build")
             if owner_capture.get("metal_toolchain") else None, os.environ["SDK_METAL_COMPONENT_BUILD"]),
        )
        for label, previous, current in comparisons:
            if previous is not None and previous != current:
                raise SystemExit(f"error: refusing cross-build replacement of {name}: {label} differs")
        if sha256(target) != owner_entry.get("sha256"):
            raise SystemExit(f"error: manifest hash mismatch for {name}")
        if digest != owner_entry.get("sha256"):
            raise SystemExit(f"error: fresh capture differs from managed artifact {name}")
        continue
    if owner is not None:
        raise SystemExit(f"error: manifest-managed artifact is missing: {name}")
    kind, framework = kind_and_framework(name)
    entry = {
        "path": name,
        "kind": kind,
        "sha256": digest,
        "size_bytes": source.stat().st_size,
        "line_count": source.read_bytes().count(b"\n"),
        "source": sources[name],
        "captured_at": os.environ["SDK_CAPTURED_AT"],
    }
    if framework:
        entry["framework_or_tool"] = framework
    additions.append(name)
    new_entries.append(entry)

if new_entries:
    if current_capture is None:
        current_capture = current_metadata
        manifest["captures"].append(current_capture)
    current_capture.setdefault("files", []).extend(new_entries)
    current_capture["files"].sort(key=lambda item: item["path"])

manifest["captures"].sort(key=lambda item: item["capture_id"])
manifest_out.write_text(json.dumps(manifest, indent=2, sort_keys=False) + "\n", encoding="utf-8")
for name in additions:
    print(name)
PY

# No destination write occurs until the capture, sanitization, and merge checks
# above have all succeeded. Existing files are never overwritten.
mkdir -p "$DEST"
while IFS= read -r name; do
  [ -n "$name" ] || continue
  tmp_target="$DEST/.${name}.capture.$$"
  cp "$CAPTURE_DIR/$name" "$tmp_target"
  mv "$tmp_target" "$DEST/$name"
done < "$ADDITIONS"

if [ ! -f "$DEST/capture-manifest.json" ] || ! cmp -s "$MERGED_MANIFEST" "$DEST/capture-manifest.json"; then
  tmp_manifest="$DEST/.capture-manifest.json.capture.$$"
  cp "$MERGED_MANIFEST" "$tmp_manifest"
  mv "$tmp_manifest" "$DEST/capture-manifest.json"
fi

ADDED_COUNT="$(wc -l < "$ADDITIONS" | tr -d ' ')"
printf '\nCapture verified: %s new artifact(s); manifest: capture-manifest.json\n' "$ADDED_COUNT"
