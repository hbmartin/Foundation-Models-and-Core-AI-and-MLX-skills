#!/usr/bin/env python3
"""Add explicitly supplied environment variables to every .xctestrun target."""

from __future__ import annotations

import argparse
import pathlib
import plistlib
import re


PROBE_VARIABLE = re.compile(r"PROBE_[A-Z0-9_]+\Z")


def parse_assignment(value: str) -> tuple[str, str]:
    name, separator, assigned_value = value.partition("=")
    if not separator or not PROBE_VARIABLE.fullmatch(name):
        raise argparse.ArgumentTypeError(
            f"expected PROBE_NAME=value, got {value!r}"
        )
    return name, assigned_value


def inject_environment(
    document: dict[str, object], environment: dict[str, str]
) -> int:
    configurations = document.get("TestConfigurations")
    if not isinstance(configurations, list):
        raise ValueError("xctestrun has no TestConfigurations array")

    target_count = 0
    for configuration in configurations:
        if not isinstance(configuration, dict):
            continue
        targets = configuration.get("TestTargets")
        if not isinstance(targets, list):
            continue
        for target in targets:
            if not isinstance(target, dict):
                continue
            target_environment = target.setdefault("EnvironmentVariables", {})
            if not isinstance(target_environment, dict):
                raise ValueError("xctestrun target EnvironmentVariables is not a dictionary")
            target_environment.update(environment)
            target_count += 1

    if target_count == 0:
        raise ValueError("xctestrun has no test targets")
    return target_count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("xctestrun", type=pathlib.Path)
    parser.add_argument("assignments", nargs="+", type=parse_assignment)
    arguments = parser.parse_args()

    with arguments.xctestrun.open("rb") as source:
        document = plistlib.load(source)
    if not isinstance(document, dict):
        parser.error("xctestrun root is not a dictionary")

    environment = dict(arguments.assignments)
    try:
        target_count = inject_environment(document, environment)
    except ValueError as error:
        parser.error(str(error))

    with arguments.xctestrun.open("wb") as destination:
        plistlib.dump(document, destination, sort_keys=False)
    print(
        f"Injected {len(environment)} probe variables into "
        f"{target_count} xctestrun target(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
