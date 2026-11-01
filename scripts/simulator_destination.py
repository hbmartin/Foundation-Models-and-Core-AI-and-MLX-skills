"""Choose the exact retained SIM-27 topology, with explicit destination overrides upstream."""

from __future__ import annotations

import json
import subprocess
import pathlib


def choose(devices: dict, runtimes: dict, minimum: int = 27, pinned: dict | None = None) -> dict:
    candidates = []
    for runtime in runtimes.get("runtimes", []):
        if not isinstance(runtime, dict) or runtime.get("isAvailable") is not True:
            continue
        identifier = runtime.get("identifier", "")
        if not identifier.startswith("com.apple.CoreSimulator.SimRuntime.iOS-"):
            continue
        try:
            version = tuple(int(piece) for piece in runtime["version"].split("."))
        except (KeyError, ValueError, AttributeError):
            continue
        if not version or version[0] < minimum:
            continue
        if pinned and (runtime.get("version") != pinned["osVersion"] or runtime.get("buildversion") != pinned["osBuild"]):
            continue
        for device in devices.get("devices", {}).get(identifier, []):
            if device.get("isAvailable") is not True or not device.get("udid"):
                continue
            name = device.get("name", "")
            if pinned and name != pinned["device"]:
                continue
            if not name.startswith(("iPhone", "iPad")):
                continue
            candidates.append((version, device.get("state") == "Booted",
                               name.startswith("iPhone"), name, device["udid"], identifier))
    if not candidates:
        raise ValueError(f"no available Simulator matching {pinned}" if pinned else f"no available iPhone or iPad Simulator with iOS {minimum} or newer")
    version, booted, _, name, udid, identifier = max(candidates)
    builds = sorted({r.get("buildversion") for r in runtimes["runtimes"]
                     if r.get("identifier") == identifier and r.get("isAvailable") is True
                     and r.get("buildversion")
                     and (not pinned or r.get("buildversion") == pinned["osBuild"])})
    return {"destination": f"platform=iOS Simulator,id={udid}", "device": name,
            "udid": udid, "version": ".".join(map(str, version)),
            "runtimeIdentifier": identifier, "runtimeBuild": builds[0] if len(builds) == 1 else None,
            "runtimeBuildCandidates": builds, "booted": booted}


def discover(timeout: float = 30) -> dict:
    def query(*arguments: str) -> dict:
        result = subprocess.run(["xcrun", "simctl", "list", *arguments, "--json"],
                                capture_output=True, text=True, timeout=timeout, check=False)
        if result.returncode:
            raise ValueError(result.stderr.strip() or "simctl query failed")
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as error:
            raise ValueError(f"simctl returned invalid JSON: {error}") from error
    baseline = json.loads((pathlib.Path(__file__).resolve().parents[1] / "notes/current-state.json").read_text())
    pinned = baseline["probeBaselines"]["tool-hosted-current-simulator"]
    return choose(query("devices", "available"), query("runtimes"), pinned=pinned)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--timeout", type=float, default=30)
    args = parser.parse_args()
    try:
        result = discover(args.timeout)
    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
        parser.exit(69, f"simulator discovery failed: {error}\n")
    print(json.dumps(result, sort_keys=True) if args.json else result["destination"])
