#!/usr/bin/env python3
"""Extract every ⚠️ callout from the guides into TSV rows:
file<TAB>line<TAB>anchor<TAB>kind<TAB>title<TAB>excerpt<TAB>callout_id<TAB>content_hash

kind: SILENT-FAILURE (explicit marker), CALLOUT (blockquote ⚠️), INLINE (⚠️ in prose/list),
      HEADING (⚠️ in a section heading)
anchor: GitHub-style slug of the nearest preceding heading.
excerpt: the callout's own text, up to ~400 chars, newlines flattened.

The TSV is strictly tab-delimited: no csv quoting or escaping, double quotes
are literal characters. flatten() guarantees no field contains a tab or newline.
"""
import os, re, sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mdslug import slugify, unique_slug
from mdlinks import is_site_only_guide, iter_lines, valid_fence_opener
from stable_identity import content_hash, semantic_id

ROOT = sys.argv[1] if len(sys.argv) > 1 else "guides"

# CommonMark-ish fence delimiter: up to 3 leading spaces, then 3+ backticks or
# tildes. A backtick opener's info string may not contain a backtick; a closer
# must use the same character, be bare, and be at least as long as its opener.
# Blockquote-wrapped fences ('> ```') never match — every line inside them is
# '>'-prefixed, so nothing there can match the column-anchored heading regex.
FENCE_RE = re.compile(r'^ {0,3}(`{3,}|~{3,})(.*)$')
IDENTITY_MARKER = re.compile(
    r'^\s*<!--\s*callout-id:\s*([^\s]+)(?:\s+occurrence:(\d+))?\s*-->\s*$', re.I,
)
WARNING_START = re.compile(
    r'^ {0,3}(?:(?:#{1,6}|[-*+]|\d+[.)])\s+)?(?:\*{1,2}|_{1,2}|["“])?⚠️',
)

def flatten(text, limit=400):
    t = re.sub(r'\s+', ' ', text).strip()
    return t[:limit]

rows = []
for dirpath, dirnames, filenames in os.walk(ROOT):
    dirnames.sort()
    for fn in sorted(filenames):
        if not fn.endswith('.md') or fn in ('SILENT-FAILURES.md', 'API-INDEX.md'):
            continue  # never index the generated index pages themselves
        path = os.path.join(dirpath, fn)
        rel = os.path.relpath(path, ROOT)
        # Only the top-level deployment-workflow collection is website-only.
        # A same-named directory nested elsewhere remains part of the corpus.
        if is_site_only_guide(rel):
            continue
        with open(path, encoding='utf-8') as f:
            lines = f.readlines()
        heading_anchor = ''
        used_slugs = set()
        next_suffix = defaultdict(int)
        fence_character = ''
        fence_len = 0
        fence_line = 0
        i = 0
        n = len(lines)
        pending_explicit_id = [None]
        pending_marker_line = [None]
        pending_occurrence = [1]
        marker_applies_in_fence = [False]
        seen_ids = {}

        def append_row(lineno, anchor, kind, title, raw_text, inside_fence=False,
                       display_text=None):
            excerpt = flatten(raw_text if display_text is None else display_text)
            # Identity stays normalized and display text stays bounded, but the
            # review hash covers the complete callout rather than its excerpt.
            digest = content_hash(kind, title, raw_text)
            explicit_id = None
            if pending_explicit_id[0] is not None:
                if inside_fence and marker_applies_in_fence[0]:
                    if pending_occurrence[0] > 1:
                        pending_occurrence[0] -= 1
                    else:
                        explicit_id = pending_explicit_id[0]
                elif not inside_fence:
                    if pending_occurrence[0] != 1:
                        sys.exit(
                            f"{path}:{pending_marker_line[0]}: occurrence is only valid "
                            "for an in-fence callout"
                        )
                    explicit_id = pending_explicit_id[0]
            try:
                callout_id = semantic_id(
                    "callout", rel, anchor, kind, title, excerpt,
                    explicit=explicit_id,
                )
            except ValueError as error:
                sys.exit(f"{path}:{lineno}: invalid callout-id: {error}")
            prior = seen_ids.get(callout_id)
            if prior is not None:
                sys.exit(
                    f"{path}:{lineno}: duplicate callout id {callout_id!r}; "
                    f"first seen at line {prior}; add a unique hidden "
                    f"{'<!-- callout-id: slug occurrence:N --> marker before the fence' if inside_fence else '<!-- callout-id: slug --> marker before one callout (prefix it with > inside a blockquote)'}"
                )
            seen_ids[callout_id] = lineno
            rows.append((rel, lineno, anchor, kind, title, excerpt, callout_id, digest))
            if explicit_id is not None:
                pending_explicit_id[0] = None
                pending_marker_line[0] = None
                pending_occurrence[0] = 1
                marker_applies_in_fence[0] = False

        def unused_marker(lineno):
            sys.exit(
                f"{path}:{pending_marker_line[0]}: callout-id marker is not followed "
                f"by its designated callout before line {lineno}"
            )

        while i < n:
            line = lines[i]
            fm = FENCE_RE.match(line)
            if fence_len:
                if (fm and fm.group(1)[0] == fence_character
                        and len(fm.group(1)) >= fence_len and not fm.group(2).strip()):
                    if pending_explicit_id[0] is not None and marker_applies_in_fence[0]:
                        unused_marker(i + 1)
                    fence_character = ''
                    fence_len = 0
                    i += 1
                    continue
            elif valid_fence_opener(line, fm):
                fence_character = fm.group(1)[0]
                fence_len = len(fm.group(1))
                fence_line = i + 1
                if pending_explicit_id[0] is not None:
                    marker_applies_in_fence[0] = True
                i += 1
                continue
            # Inside a fence a '#' line is code, not a heading, and never mints
            # an anchor; in-fence ⚠️ lines still extract below as INLINE,
            # anchored to the nearest real heading.
            if fence_len and re.match(r'^\s*(?://|#)\s*callout-id:', line, re.IGNORECASE):
                sys.exit(
                    f"{path}:{i + 1}: callout-id metadata must not appear inside "
                    "a published code fence; use a hidden Markdown marker before the fence"
                )
            identity_marker = None if fence_len else IDENTITY_MARKER.match(line)
            if identity_marker:
                if pending_explicit_id[0] is not None:
                    sys.exit(f"{path}:{i + 1}: callout-id marker replaces an unused marker")
                pending_explicit_id[0] = identity_marker.group(1)
                pending_marker_line[0] = i + 1
                pending_occurrence[0] = int(identity_marker.group(2) or "1")
                if pending_occurrence[0] < 1:
                    sys.exit(f"{path}:{i + 1}: callout-id occurrence must be at least 1")
                i += 1
                continue

            if not fence_len and line.lstrip().startswith('>'):
                # Consume from the start of the blockquote so the review hash
                # covers context that appears before the warning line too.
                start = i
                block = []
                # An unquoted blank separates blocks. A quoted blank ('>') is
                # a paragraph boundary within this same block and stays hashed.
                while i < n and lines[i].lstrip().startswith('>'):
                    block.append(re.sub(r'^[ \t]*>[ \t]?', '', lines[i]))
                    i += 1
                # Inspect quote-stripped source for fences and structural warning
                # starts, while preserving the original text for identity/hash.
                visible = [re.sub(r'^(?: {0,3}>[ \t]?)+', '', body) for body in block]
                warning_indexes, annotation_indexes, markers = [], [], {}
                for index, (body, _, fenced) in enumerate(iter_lines(''.join(visible))):
                    if fenced and re.match(r'^\s*(?:(?://|#)\s*|<!--\s*)?callout-id:', body, re.I):
                        sys.exit(f"{path}:{start + index + 1}: callout-id metadata must not appear "
                                 "inside a published code fence; use a hidden Markdown marker")
                    marker = None if fenced else IDENTITY_MARKER.match(body)
                    if marker:
                        if marker.group(2) is not None:
                            sys.exit(f"{path}:{start + index + 1}: occurrence is only valid for an in-fence callout")
                        markers[index] = marker.group(1)
                        continue
                    if '⚠️' in body:
                        annotation_indexes.append(index)
                        if not fenced and WARNING_START.match(body):
                            warning_indexes.append(index)
                prose_warnings = bool(warning_indexes)
                if not prose_warnings:
                    warning_indexes = annotation_indexes
                marker_targets = {}
                for marker_index, explicit_id in markers.items():
                    target = next((index for index in warning_indexes if index > marker_index), None)
                    if target is None or any(visible[index].strip() for index in range(marker_index + 1, target)):
                        sys.exit(f"{path}:{start + marker_index + 1}: callout-id marker is not followed "
                                 "by its designated callout")
                    if target in marker_targets:
                        sys.exit(f"{path}:{start + marker_index + 1}: callout-id marker replaces an unused marker")
                    marker_targets[target] = (explicit_id, start + marker_index + 1)
                if not warning_indexes:
                    if pending_explicit_id[0] is not None:
                        unused_marker(start + 1)
                    continue
                if pending_explicit_id[0] is not None and pending_occurrence[0] != 1:
                    sys.exit(
                        f"{path}:{pending_marker_line[0]}: occurrence is only valid "
                        "for an in-fence callout"
                    )
                for position, warning_index in enumerate(warning_indexes):
                    if warning_index in marker_targets:
                        if pending_explicit_id[0] is not None:
                            sys.exit(f"{path}:{marker_targets[warning_index][1]}: callout-id marker replaces an unused marker")
                        pending_explicit_id[0], pending_marker_line[0] = marker_targets[warning_index]
                    end = (warning_indexes[position + 1]
                           if position + 1 < len(warning_indexes) else len(block))
                    # Only the first warning owns the preceding context. Quoted
                    # blank lines belong to the explanation, not a new warning.
                    begin = 0 if position == 0 else warning_index
                    raw_text = ''.join(body for index, body in enumerate(block[begin:end], begin)
                                       if index not in markers) if prose_warnings else block[warning_index]
                    display_text = ''.join(body for index, body in enumerate(block[warning_index:end], warning_index)
                                           if index not in markers) if prose_warnings else raw_text
                    marker_text = display_text[display_text.find('⚠️'):]
                    tm = re.match(r'(?:⚠️\s*)+\*\*([^*]+)\*\*', marker_text)
                    title = flatten(tm.group(1), 160) if tm else ''
                    kind = 'INLINE' if not prose_warnings else (
                        'SILENT-FAILURE'
                        if re.search(r'SILENT FAILURE', display_text, re.I)
                        else 'CALLOUT'
                    )
                    append_row(
                        start + warning_index + 1,
                        heading_anchor,
                        kind,
                        title,
                        raw_text,
                        display_text=display_text,
                    )
                continue

            if (
                pending_explicit_id[0] is not None
                and line.strip()
                and '⚠️' not in line
                and not fence_len
            ):
                unused_marker(i + 1)

            m = None if fence_len else re.match(r'^(#{1,6})\s+(.*)', line)
            if m:
                heading = m.group(2).strip()
                heading_anchor = unique_slug(slugify(heading), used_slugs, next_suffix)
                if '⚠️' in line:
                    title = flatten(re.sub(r'^#+\s*', '', line))
                    append_row(i + 1, heading_anchor, 'HEADING', title, line,
                               display_text='')
                i += 1
                continue
            if '⚠️' not in line:
                i += 1
                continue
            # inline occurrence (prose, list item, table row)
            tm = re.search(r'⚠️\s*\*\*([^*]+)\*\*', line)
            title = flatten(tm.group(1), 160) if tm else ''
            append_row(i + 1, heading_anchor, 'INLINE', title, line,
                       inside_fence=bool(fence_len))
            i += 1
        if fence_len:
            sys.exit(
                f"{path}:{fence_line}: unterminated "
                f"{fence_character * fence_len} fence"
            )
        if pending_explicit_id[0] is not None:
            unused_marker(n + 1)

for r in rows:
    print('\t'.join(str(field) for field in r))
print(f"# total rows: {len(rows)}", file=sys.stderr)
kinds = {}
for r in rows:
    kinds[r[3]] = kinds.get(r[3], 0) + 1
print(f"# by kind: {kinds}", file=sys.stderr)
