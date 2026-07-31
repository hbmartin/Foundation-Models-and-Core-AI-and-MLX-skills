#!/usr/bin/env python3
"""Extract every ⚠️ callout from the guides into TSV rows:
file<TAB>line<TAB>anchor<TAB>kind<TAB>title<TAB>excerpt

kind: SILENT-FAILURE (explicit marker), CALLOUT (blockquote ⚠️), INLINE (⚠️ in prose/list),
      HEADING (⚠️ in a section heading)
anchor: GitHub-style slug of the nearest preceding heading.
excerpt: the callout's own text, up to ~400 chars, newlines flattened.
"""
import os, re, sys, csv

ROOT = sys.argv[1] if len(sys.argv) > 1 else "guides"

def slugify(h):
    h = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', h)  # [text](url) -> text, as GitHub slugs do
    h = re.sub(r'[`*_]', '', h).strip()
    h = h.lower()
    out = []
    for ch in h:
        if ch.isalnum():
            out.append(ch)
        elif ch in ' -':
            out.append('-' if ch == ' ' else ch)
        # everything else dropped (github slug rule approximation)
    return re.sub(r'-{2,}', '-', ''.join(out)).strip('-')

def flatten(text, limit=400):
    t = re.sub(r'\s+', ' ', text).strip()
    return t[:limit]

rows = []
for dirpath, dirnames, filenames in os.walk(ROOT):
    for fn in sorted(filenames):
        if not fn.endswith('.md') or fn in ('SILENT-FAILURES.md', 'API-INDEX.md'):
            continue  # never index the generated index pages themselves
        path = os.path.join(dirpath, fn)
        rel = os.path.relpath(path, ROOT)
        with open(path, encoding='utf-8') as f:
            lines = f.readlines()
        heading = ''
        i = 0
        n = len(lines)
        while i < n:
            line = lines[i]
            m = re.match(r'^(#{1,6})\s+(.*)', line)
            if m:
                heading = m.group(2).strip()
                if '⚠️' in line:
                    rows.append((rel, i + 1, slugify(heading), 'HEADING',
                                 flatten(re.sub(r'^#+\s*', '', line)), ''))
                i += 1
                continue
            if '⚠️' not in line:
                i += 1
                continue
            if line.lstrip().startswith('>'):
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
                rows.append((rel, start + 1, slugify(heading), kind, title, flatten(text)))
                continue
            # inline occurrence (prose, list item, table row)
            tm = re.search(r'⚠️\s*\*\*([^*]+)\*\*', line)
            title = flatten(tm.group(1), 160) if tm else ''
            rows.append((rel, i + 1, slugify(heading), 'INLINE', title, flatten(line)))
            i += 1

w = csv.writer(sys.stdout, delimiter='\t', lineterminator='\n')
for r in rows:
    w.writerow(r)
print(f"# total rows: {len(rows)}", file=sys.stderr)
kinds = {}
for r in rows:
    kinds[r[3]] = kinds.get(r[3], 0) + 1
print(f"# by kind: {kinds}", file=sys.stderr)
