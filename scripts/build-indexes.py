#!/usr/bin/env python3
"""Assemble the two index pages from classified callout TSVs and the symbol TSV.

Usage: build_indexes.py <classified_dir> <symbols_tsv> <guides_dir> <out_dir>
Writes <out_dir>/SILENT-FAILURES.md and <out_dir>/API-INDEX.md
"""
import os, re, sys, time
from collections import defaultdict, Counter

classified_dir, symbols_tsv, guides_dir, out_dir = sys.argv[1:5]

TODAY = time.strftime('%Y-%m-%d')
TAXONOMY_MD = 'notes/synthesis/SYMPTOM-TAXONOMY.md'

SYMPTOMS = [
    ("garbage-output",      "Wrong output",           "Runs and returns output that is wrong — wrong numbers, garbled or wrong-language text, corrupted tensors."),
    ("empty-output",        "Empty output / no-op",   "Runs and returns nothing where content is expected — nil, empty results, operations that quietly do nothing."),
    ("silent-truncation",   "Truncation & limits",    "Input or output silently truncated or capped — context windows, response sizes, token budgets."),
    ("ignored-input",       "Ignored input",          "A parameter, flag, option, file or annotation is silently ignored, dropped, or overridden."),
    ("stale-state",         "Stale state",            "Stale or cached data served; invalidation that did not happen (or happened unexpectedly)."),
    ("data-loss",           "Data & artifact loss",   "Silent loss or overwrite of data or build artifacts — purged assets, dead bookmarks, unrebuildable builds."),
    ("runtime-unavailable", "Compiles but unavailable","Builds fine, then fails or degrades at runtime for some users — OS floors, device eligibility, missing assets, entitlements."),
    ("perf-cliff",          "Performance cliffs",     "Silent slowdowns — CPU/GPU fallback, ANE ineligibility, cache misses, respecialization, sync stalls."),
    ("resource-growth",     "Resource growth",        "Silent memory or disk growth, leaks, quota consumption."),
    ("precision-loss",      "Precision loss",         "Silent numeric precision or dtype changes — TF32, quantization side-effects, accumulation regimes."),
    ("misleading-signal",   "Misleading signals",     "Errors, logs or metrics that name the wrong cause; swallowed errors; observation APIs that emit nothing."),
    ("version-drift",       "Version drift",          "The same code or artifact behaves differently across OS/SDK/tool versions with no signal."),
    ("docs-vs-reality",     "Docs vs reality",        "Documented behavior differs from what ships — samples that don't compile, wrong signatures, naming mismatches."),
    ("footgun-api",         "API footguns",           "API shapes that invite silent misuse — surprising defaults, order-dependence, overload traps."),
    ("caution-note",        "General cautions",       "Warnings and considerations that are not themselves silent failures."),
]
SYMPTOM_TITLE = {k: t for k, t, _ in SYMPTOMS}

# The taxonomy doc is the classification contract; refuse to build against a
# drifted copy of it (ids only — presentation titles/descriptions may differ).
if os.path.exists(TAXONOMY_MD):
    doc_ids = set(re.findall(r'^\| ([a-z][a-z-]+) \|', open(TAXONOMY_MD, encoding='utf-8').read(), re.M)) - {'id'}
    if doc_ids != set(SYMPTOM_TITLE):
        sys.exit(f"symptom ids in {TAXONOMY_MD} disagree with SYMPTOMS in this script: "
                 f"doc-only={sorted(doc_ids - set(SYMPTOM_TITLE))} "
                 f"script-only={sorted(set(SYMPTOM_TITLE) - doc_ids)}")

def load_rows():
    rows = []
    for fn in sorted(os.listdir(classified_dir)):
        if not fn.endswith('.tsv'):
            continue
        with open(os.path.join(classified_dir, fn), encoding='utf-8') as f:
            for line in f:
                line = line.rstrip('\n')
                if not line or line.startswith('#'):
                    continue
                parts = line.split('\t')
                if len(parts) < 6:
                    continue
                file, lineno, anchor, kind, symptom, blurb = parts[:6]
                rows.append(dict(file=file, line=int(lineno), anchor=anchor,
                                 kind=kind, symptom=symptom.strip(), blurb=blurb.strip()))
    return rows

def part_of(path):
    m = re.match(r'(part-\d+)[^/]*', path)
    return m.group(1) if m else 'root'

def part_num(path):
    m = re.match(r'part-(\d+)', path)
    return int(m.group(1)) if m else 0

def guide_label(path):
    # part-07-coreai-swift-runtime/references/02-specialization... -> "7.2"
    p = part_num(path)
    m = re.search(r'references/(\d+)-', path)
    if m:
        return f"{p}.{int(m.group(1))}"
    if path.endswith('README.md') and p:
        return f"{p}.README"
    return "root"

def link(row):
    target = row['file']
    if row['anchor']:
        target += '#' + row['anchor']
    return target

rows = load_rows()
bad = [r for r in rows if r['symptom'] not in SYMPTOM_TITLE]
if bad:
    print(f"WARNING: {len(bad)} rows with unknown symptom ids: "
          f"{Counter(r['symptom'] for r in bad)}", file=sys.stderr)

by_symptom = defaultdict(list)
for r in rows:
    if r['symptom'] in SYMPTOM_TITLE:
        by_symptom[r['symptom']].append(r)
for v in by_symptom.values():
    v.sort(key=lambda r: (part_num(r['file']), r['file'], r['line']))

# ---------- SILENT-FAILURES.md ----------
n_total = len(rows)
n_fail = sum(len(v) for k, v in by_symptom.items() if k != 'caution-note')
out = []
out.append("# The silent-failure index\n")
out.append(f"**Every ⚠️ callout in the series — {n_total} of them, {n_fail} describing a "
           "concrete silent failure — in one place, sorted by the symptom you would observe.**\n")
out.append("The defining property of this stack is that most defects *do not throw*. Each entry "
           "below links to the guide section that documents the failure, its trigger, and the "
           "safe default. Entries are classified by **what you see** (or fail to see), not by "
           "which API is at fault, because the symptom is what you start from at 2 a.m.\n")
out.append(f"> Generated from the guides on {TODAY} by `scripts/` tooling; regenerate after "
           "editing guides rather than editing this file by hand.\n")
out.append("\n## How to use this page\n")
out.append("Start from the symptom column that matches what you observe. Within each section, "
           "entries run in part order — Foundation Models first (parts 1–6), Core AI (7–10), "
           "Metal (11), MLX (12–13), then bridges, shipping, adjacent capabilities and "
           "migration (14–17).\n")
out.append("\n## The symptoms\n")
out.append("| Symptom | Entries | What it means |")
out.append("|---|---:|---|")
for key, title, desc in SYMPTOMS:
    n = len(by_symptom.get(key, []))
    if n:
        out.append(f"| [{title}](#{re.sub(r'[^a-z0-9- ]', '', title.lower()).replace(' ', '-')}) | {n} | {desc} |")
out.append("")
for key, title, desc in SYMPTOMS:
    entries = by_symptom.get(key, [])
    if not entries:
        continue
    out.append(f"\n## {title}\n")
    out.append(f"*{desc}*\n")
    cur_part = None
    for r in entries:
        p = part_of(r['file'])
        if p != cur_part:
            cur_part = p
            pretty = f"Part {part_num(r['file'])}" if p != 'root' else 'Series'
            out.append(f"\n**{pretty}**\n")
        marker = ' 🔇' if r['kind'] == 'SILENT-FAILURE' else ''
        out.append(f"- [{r['blurb']}]({link(r)}) — {guide_label(r['file'])}{marker}")
    out.append("")
out.append("\n---\n\n🔇 = the guide marks this as an explicit **SILENT FAILURE** callout.\n")
with open(os.path.join(out_dir, 'SILENT-FAILURES.md'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))
print(f"SILENT-FAILURES.md: {n_total} entries ({n_fail} failures) "
      f"across {len([1 for s in SYMPTOMS if by_symptom.get(s[0])])} symptoms")

# ---------- API-INDEX.md ----------
FW_ORDER = ["FoundationModels", "CoreAI", "Evaluations", "MLX", "Speech", "AppIntents",
            "CoreSpotlight", "Vision", "Metal/MPP", "SwiftUI", "Media/Core*",
            "Swift/Foundation", "other"]
syms = []
with open(symbols_tsv, encoding='utf-8') as f:
    for line in f:
        if line.startswith('#') or not line.strip():
            continue
        p = line.rstrip('\n').split('\t')
        if len(p) < 7:
            continue
        sym, fw, total, nguides, in26, in27, guides = p[:7]
        syms.append(dict(sym=sym, fw=fw, total=int(total), nguides=int(nguides),
                         in26=in26, in27=in27, guides=guides))
# keep signal: in >=2 guides, or >=4 mentions, or SDK-present
keep = [s for s in syms if s['nguides'] >= 2 or s['total'] >= 4 or s['in26'] or s['in27']]
by_fw = defaultdict(list)
for s in keep:
    by_fw[s['fw']].append(s)
for v in by_fw.values():
    v.sort(key=lambda s: s['sym'].lstrip('@.').lower())

out = []
out.append("# API & symbol index\n")
out.append(f"**{len(keep)} symbols referenced across the series, by framework — with where each "
           "is covered and whether it exists in the captured 26.5 / 27.0 beta SDK interfaces.**\n")
out.append("> `26.5` / `27.0` = the bare symbol name appears in the corresponding captured "
           "`.swiftinterface` in `notes/sdk-interfaces/` (a presence check, not a full signature "
           "match — the guides carry the signature-level citations). Package types (MLX, "
           "`ChatCompletionsLanguageModel`, …) and C/ObjC-only API legitimately show neither. "
           f"Generated {TODAY}; regenerate rather than hand-edit.\n")
for fw in FW_ORDER:
    entries = by_fw.get(fw, [])
    if not entries:
        continue
    out.append(f"\n## {fw}  <sub>{len(entries)} symbols</sub>\n")
    out.append("| Symbol | 26.5 | 27.0 | Covered in |")
    out.append("|---|:-:|:-:|---|")
    for s in entries:
        gl = []
        for chunk in s['guides'].split(';')[:4]:
            path, _, cnt = chunk.rpartition(':')
            if not path:
                continue
            gl.append(f"[{guide_label(path)}]({path})")
        more = s['nguides'] - len(gl)
        tail = f" +{more} more" if more > 0 else ""
        out.append(f"| `{s['sym']}` | {'✓' if s['in26'] else ''} | {'✓' if s['in27'] else ''} | "
                   f"{', '.join(gl)}{tail} |")
out.append("")
with open(os.path.join(out_dir, 'API-INDEX.md'), 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))
print(f"API-INDEX.md: {len(keep)} symbols kept of {len(syms)}")
