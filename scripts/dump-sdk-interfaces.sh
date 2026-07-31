#!/usr/bin/env bash
# Dump every Apple framework .swiftinterface relevant to this guide series into
# notes/sdk-interfaces/, and probe for the toolchain CLIs. Safe to run repeatedly.
#
#   ./scripts/dump-sdk-interfaces.sh
#
# Run it now to snapshot the CURRENT SDK (26.5). Run it again after installing
# Xcode 27 and `sudo xcode-select -s /Applications/Xcode-beta.app` — it will
# then capture the 27 surfaces (CoreAI, the LanguageModel protocol, PCC,
# DynamicProfile, the real LanguageModelError cases, BarcodeReaderTool/OCRTool
# associated types, the 27 Evaluations/Speech APIs) that close the largest
# cluster of 🔴 gaps in the guides. Output filenames embed the SDK version, so
# a 26.5 run and a 27.0 run coexist and can be diffed.

set -uo pipefail
cd "$(dirname "$0")/.."
DEST="notes/sdk-interfaces"
mkdir -p "$DEST"

SDKPATH="$(xcrun --sdk macosx --show-sdk-path 2>/dev/null)"
SDKVER="$(xcrun --sdk macosx --show-sdk-version 2>/dev/null)"
XCODE="$(xcode-select -p 2>/dev/null)"
echo "Xcode:   $XCODE"
echo "macOS SDK: $SDKVER  ($SDKPATH)"
echo "Writing to: $DEST"
echo

# Frameworks whose Swift interface the guides depend on. CoreAI/Evaluations are
# 27.0+, so on a 26.x SDK they will simply be reported absent — that is expected.
# NOTE: CoreAI.framework is an umbrella — its interface is one @_exported import
# line. The real API lives in SubFrameworks/ (CoreAIDelegates, CoreAIRuntime,
# CoreAIAsset, CoreAICache, CoreAICommon, CoreAICompiler), scanned below.
# _Vision_FoundationModels / _CoreSpotlight_FoundationModels are cross-import
# overlays: they hold OCRTool/BarcodeReaderTool and SpotlightSearchTool, which
# appear in NO parent framework's interface.
FRAMEWORKS=(FoundationModels CoreAI CoreAIDelegates CoreAIRuntime CoreAIAsset CoreAICache CoreAICommon CoreAICompiler Vision _Vision_FoundationModels Evaluations Speech CoreSpotlight _CoreSpotlight_FoundationModels AppIntents MetalPerformancePrimitives)

for fw in "${FRAMEWORKS[@]}"; do
  # A framework can live in Frameworks/ or SubFrameworks/ (Apple's split
  # umbrella layout, new in the 26/27 SDKs), or — like XCTest/Swift Testing —
  # ship inside Xcode itself rather than the OS SDK (Evaluations does this).
  fwdir="$SDKPATH/System/Library/Frameworks/$fw.framework"
  [ -d "$fwdir" ] || fwdir="$SDKPATH/System/Library/SubFrameworks/$fw.framework"
  [ -d "$fwdir" ] || fwdir="$XCODE/Platforms/MacOSX.platform/Developer/Library/Frameworks/$fw.framework"
  # Prefer the arm64e macOS slice; fall back to any slice present.
  iface="$(find "$fwdir" \
            -name '*.swiftinterface' 2>/dev/null | grep -E 'arm64e-apple-macos' | head -1)"
  [ -z "$iface" ] && iface="$(find "$fwdir" -name '*.swiftinterface' 2>/dev/null | head -1)"
  if [ -n "$iface" ]; then
    out="$DEST/${fw}-${SDKVER}-macos.swiftinterface"
    cp "$iface" "$out"
    printf "  ✓ %-28s %6s lines  -> %s\n" "$fw" "$(wc -l < "$out" | tr -d ' ')" "$(basename "$out")"
  else
    # Some ML frameworks ship as ObjC/headers, not Swift — note that, still useful.
    hdr="$fwdir/Headers"
    if [ -d "$hdr" ]; then
      printf "  ~ %-28s no .swiftinterface; C/ObjC headers at %s\n" "$fw" "$hdr"
    else
      printf "  ✗ %-28s absent from this SDK (expected if it is 27.0+ and SDK is %s)\n" "$fw" "$SDKVER"
    fi
  fi
done

echo
echo "=== toolchain CLIs (blank = absent) ==="
for t in fm coreai-build; do
  # --no-cache: xcrun caches negative lookups, which hides tools installed
  # mid-session (the Metal Toolchain component adds coreai-build this way).
  p="$(xcrun --no-cache --find "$t" 2>/dev/null)"
  printf "  %-14s %s\n" "$t" "${p:-ABSENT}"
  # If present, capture --help so the guide can cite the real flag surface.
  # Invoke via the resolved path — the bare name is not on PATH for
  # component-installed tools.
  if [ -n "$p" ]; then
    "$p" --help > "$DEST/${t}-help-sdk${SDKVER}.txt" 2>&1 && \
      echo "                 -> saved $DEST/${t}-help-sdk${SDKVER}.txt"
  fi
done

echo
echo "Done. If you just switched to Xcode 27, commit the new *-27.*-macos.swiftinterface"
echo "files and tell the assistant — the 27-only gaps can then be closed with ✅ evidence."
