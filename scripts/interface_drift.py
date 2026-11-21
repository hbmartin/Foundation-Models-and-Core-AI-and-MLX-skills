"""Compare scoped Swift interface declarations, including requirements and client bodies.

Raw captures are immutable. This diagnostic normalizes module separators, whitespace,
and attribute order; it does not discard availability or serialized implementation.
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re

TYPE = re.compile(r"\b(struct|enum|class|protocol|actor|extension)\s+(?!func\b|var\b|subscript\b)([\w.]+)")
MEMBER = re.compile(r"\b(var|let|func|init|subscript|case|associatedtype|typealias)\b")
SURFACE = re.compile(r"\b(import|macro|operator|precedencegroup)\s+([^\s({:]+)")
TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|[^"{}]+|[{}]')


def normalize(text):
    return "".join(token if token.startswith('"') else re.sub(r"\s+", " ", token.replace("::", "."))
                   for token in re.findall(r'"(?:\\.|[^"\\])*"|[^"\n]+|\n', text)).strip()


def attribute_prefix(text):
    """Consume one attribute, balancing parentheses outside escaped string literals."""
    match = re.match(r"@[\w.]+", text)
    if not match:
        raise ValueError("invalid Swift attribute")
    end = match.end()
    if end < len(text) and text[end] == "(":
        depth, quoted, escaped = 0, False, False
        for index in range(end, len(text)):
            char = text[index]
            if quoted:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    quoted = False
            elif char == '"':
                quoted = True
            elif char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    end = index + 1
                    break
        else:
            raise ValueError("unterminated Swift attribute")
    return text[:end], text[end:].strip()


def braces(text):
    return sum(1 if token == "{" else -1 if token == "}" else 0 for token in TOKEN.findall(text))


def syntax(text):
    return re.sub(r'"(?:\\.|[^"\\])*"', lambda match: " " * len(match[0]), text)


def declarations(text):
    records = {}
    scopes = []
    attributes = []
    depth = 0
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        index += 1
        if not line or line.startswith(("//", "#")):
            continue
        # Attributes preceding a declaration can be printed in either order.
        while line.startswith("@"):
            while True:
                try:
                    attribute, remainder = attribute_prefix(line)
                    break
                except ValueError:
                    if index == len(lines):
                        raise
                    line += "\n" + lines[index].strip()
                    index += 1
            attributes.append(normalize(attribute))
            line = remainder
        if not line:
            continue
        line = normalize(line)
        code = syntax(line)
        surface = SURFACE.search(code)
        kind = TYPE.search(code) if not surface else None
        member = MEMBER.search(code)
        inherited = [a for scope in scopes for a in scope["availability"]]
        owner = scopes[-1]["owner"] if scopes else "<module>"
        if kind and (member is None or kind.start() < member.start()):
            while "{" not in line and index < len(lines):
                line += " " + normalize(lines[index])
                index += 1
            name = kind[2]
            qualified = name if kind[1] == "extension" or owner == "<module>" else f"{owner}.{name}"
            header = normalize(line.split("{", 1)[0])
            record = {"owner": owner, "declaration": header,
                      "attributes": sorted(set(inherited + attributes)), "body": ""}
            records[json.dumps(record, sort_keys=True)] = record
            depth += braces(line)
            scopes.append({"owner": qualified, "depth": depth,
                           "availability": [a for a in attributes if a.startswith("@available")]})
            attributes = []
            if braces(line) == 0:
                scopes.pop()
            continue
        if member or surface:
            header, opening, body = line.partition("{")
            balance = braces(line)
            while balance > 0 and index < len(lines):
                next_line = lines[index].strip()
                index += 1
                body += "\n" + next_line
                balance += braces(next_line)
            # A property with no accessor block is stored and therefore settable;
            # a subsequent get-only block is a meaningful payload change.
            record = {"owner": owner, "declaration": normalize(header),
                      "attributes": sorted(set(inherited + attributes)),
                      "body": normalize(body.rsplit("}", 1)[0]) if opening else ""}
            records[json.dumps(record, sort_keys=True)] = record
            attributes = []
            continue
        depth += braces(line)
        while scopes and depth < scopes[-1]["depth"]:
            scopes.pop()
        attributes = []
    return list(records.values())


def compare(before, after):
    def group(text):
        grouped = collections.defaultdict(list)
        for record in declarations(text):
            declaration = record["declaration"]
            code = syntax(declaration)
            surface = SURFACE.search(code)
            kind = surface or TYPE.search(code)
            identity = f"{kind[1]} {kind[2]}" if kind else declaration
            grouped[(record["owner"], identity)].append(record)
        return grouped
    old, new = group(before), group(after)
    changes = []
    for key in sorted(old.keys() | new.keys()):
        a = {json.dumps(r, sort_keys=True): r for r in old.get(key, [])}
        b = {json.dumps(r, sort_keys=True): r for r in new.get(key, [])}
        removed = [a[k] for k in sorted(a.keys() - b.keys())]
        added = [b[k] for k in sorted(b.keys() - a.keys())]
        while removed and added:
            changes.append({"kind": "modified", "owner": key[0], "before": removed.pop(0), "after": added.pop(0)})
        changes.extend({"kind": "removed", "owner": key[0], "before": r} for r in removed)
        changes.extend({"kind": "variant-added" if key in old else "added", "owner": key[0], "after": r} for r in added)
    return changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=pathlib.Path)
    parser.add_argument("after", type=pathlib.Path)
    parser.add_argument("--framework", default="interface")
    parser.add_argument("--examples", type=int, default=8)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    changes = compare(args.before.read_text(), args.after.read_text())
    if args.json:
        print(json.dumps({"framework": args.framework, "declarationsChanged": len(changes), "changes": changes}, indent=2))
    else:
        print(f"  {args.framework}: {len(changes)} changed declarations (scoped, order independent)")
        for change in changes[:args.examples]:
            record = change.get("after", change.get("before"))
            print(f"    {change['kind']} {record['owner']}: {record['declaration']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
