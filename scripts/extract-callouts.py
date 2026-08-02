#!/usr/bin/env python3
"""Extract every ⚠️ callout from the guides into TSV rows:
file<TAB>line<TAB>anchor<TAB>kind<TAB>title<TAB>excerpt

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

ROOT = sys.argv[1] if len(sys.argv) > 1 else "guides"

# CommonMark-ish fence delimiter: up to 3 leading spaces, then 3+ backticks or
# tildes. A backtick opener's info string may not contain a backtick; a closer
# must use the same character, be bare, and be at least as long as its opener.
# Blockquote-wrapped fences ('> ```') never match — every line inside them is
# '>'-prefixed, so nothing there can match the column-anchored heading regex.
FENCE_RE = re.compile(r'^ {0,3}(`{3,}|~{3,})(.*)$')

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
        while i < n:
            line = lines[i]
            fm = FENCE_RE.match(line)
            if fence_len:
                if (fm and fm.group(1)[0] == fence_character
                        and len(fm.group(1)) >= fence_len and not fm.group(2).strip()):
                    fence_character = ''
                    fence_len = 0
                    i += 1
                    continue
            elif fm and (fm.group(1)[0] == '~' or '`' not in fm.group(2)):
                fence_character = fm.group(1)[0]
                fence_len = len(fm.group(1))
                fence_line = i + 1
                i += 1
                continue
            # Inside a fence a '#' line is code, not a heading, and never mints
            # an anchor; in-fence ⚠️ lines still extract below as INLINE,
            # anchored to the nearest real heading.
            m = None if fence_len else re.match(r'^(#{1,6})\s+(.*)', line)
            if m:
                heading = m.group(2).strip()
                heading_anchor = unique_slug(slugify(heading), used_slugs, next_suffix)
                if '⚠️' in line:
                    rows.append((rel, i + 1, heading_anchor, 'HEADING',
                                 flatten(re.sub(r'^#+\s*', '', line)), ''))
                i += 1
                continue
            if '⚠️' not in line:
                i += 1
                continue
            if not fence_len and line.lstrip().startswith('>'):
                # blockquote callout: swallow the whole contiguous blockquote
                start = i
                block = []
                while i < n and (lines[i].lstrip().startswith('>') or lines[i].strip() == ''):
                    if lines[i].strip() == '' and not (i + 1 < n and lines[i + 1].lstrip().startswith('>')):
                        break
                    block.append(re.sub(r'^\s*>\s?', '', lines[i]))
                    i += 1
                text = ''.join(block)
                tm = re.search(r'⚠️\s*\*\*([^*]+)\*\*', text)
                title = flatten(tm.group(1), 160) if tm else ''
                kind = 'SILENT-FAILURE' if re.search(r'SILENT FAILURE', text, re.I) else 'CALLOUT'
                rows.append((rel, start + 1, heading_anchor, kind, title, flatten(text)))
                continue
            # inline occurrence (prose, list item, table row)
            tm = re.search(r'⚠️\s*\*\*([^*]+)\*\*', line)
            title = flatten(tm.group(1), 160) if tm else ''
            rows.append((rel, i + 1, heading_anchor, 'INLINE', title, flatten(line)))
            i += 1
        if fence_len:
            sys.exit(
                f"{path}:{fence_line}: unterminated "
                f"{fence_character * fence_len} fence"
            )

for r in rows:
    print('\t'.join(str(field) for field in r))
print(f"# total rows: {len(rows)}", file=sys.stderr)
kinds = {}
for r in rows:
    kinds[r[3]] = kinds.get(r[3], 0) + 1
print(f"# by kind: {kinds}", file=sys.stderr)
