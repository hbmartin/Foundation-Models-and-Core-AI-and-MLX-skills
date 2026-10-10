#!/usr/bin/env python3
"""Slow integration checks for the committed generated guide indexes."""

import datetime
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

from scripts.mdlinks import fence_closer, fence_opener, is_site_only_guide

REPO = Path(__file__).resolve().parents[2]
GUIDES = REPO / 'guides'
CLASSIFIED = REPO / 'notes' / 'synthesis' / 'callout-classifications'
LEGACY_CLASSIFIED = REPO / 'notes' / 'synthesis' / 'callout-classification'
ANCHOR_SECTION_LINKS = REPO / 'scripts' / 'anchor-section-links.py'


class RepositoryIndexTests(unittest.TestCase):
    maxDiff = 2000

    def test_non_fenced_quoted_warnings_have_extracted_rows(self):
        result = self.run_command(sys.executable, 'scripts/extract-callouts.py', 'guides')
        self.assertEqual(0, result.returncode, result.stderr)
        locations = {(row[0], int(row[1])) for row in
                     (line.split('\t') for line in result.stdout.splitlines())}
        expected = set()
        for path in GUIDES.rglob('*.md'):
            relative = path.relative_to(GUIDES).as_posix()
            if path.name in ('SILENT-FAILURES.md', 'API-INDEX.md') or is_site_only_guide(relative):
                continue
            fence, quoted_fence = None, False
            with path.open(encoding='utf-8') as source:
                for lineno, line in enumerate(source, 1):
                    quoted = line.lstrip().startswith('>')
                    visible = re.sub(r'^(?: {0,3}>[ \t]?)+', '', line) if quoted else line
                    if fence:
                        self.assertTrue(not quoted_fence or quoted, f'{relative}:{lineno}: unclosed quoted fence')
                        if fence_closer(visible if quoted_fence else line, fence):
                            fence = None
                        continue
                    opener = fence_opener(visible)
                    if opener:
                        fence, quoted_fence = opener[1], quoted
                        continue
                    if not quoted:
                        continue
                    for warning in re.finditer('⚠️', visible):
                        prefix, suffix = visible[:warning.start()], visible[warning.end():]
                        # Check the readable label independently of the extractor's regex.
                        label_words = suffix.strip().replace('*', '').replace('_', '').split()
                        label = label_words[0].rstrip('),.;:!?') if label_words else ''
                        standalone = not prefix.strip('*_#-+ 0123456789.)"“')
                        if standalone or label.lower() not in ('community', 'community-reported', 'community-published'):
                            expected.add((relative, lineno))
                            break
        self.assertFalse(expected - locations, f'quoted warnings missing rows: {sorted(expected - locations)}')
        self.assertIn(('part-09-coreai-compression-numerics/references/03-numeric-formats-across-the-stack.md', 2182), locations)
        self.assertIn(('part-10-coreai-hardware-authoring-debugging/references/03-llm-export-end-to-end.md', 3782), locations)

    def test_only_canonical_classification_directory_has_files(self):
        self.assertTrue(CLASSIFIED.is_dir())
        self.assertFalse(
            any(path.is_file() for path in LEGACY_CLASSIFIED.rglob('*')),
            'remove the stale singular classification directory; use callout-classifications',
        )

    def test_section_scoped_links_have_verified_fragments(self):
        result = self.run_command(sys.executable, ANCHOR_SECTION_LINKS, GUIDES)
        self.assertEqual(result.returncode, 0, result.stderr)

    def run_command(self, *arguments, env=None):
        return subprocess.run(
            [str(argument) for argument in arguments],
            cwd=REPO,
            env={**os.environ, **(env or {})},
            text=True,
            capture_output=True,
            check=False,
        )

    def test_committed_indexes_match_clean_generation_and_links(self):
        committed_silent = (GUIDES / 'SILENT-FAILURES.md').read_text(encoding='utf-8')
        match = re.search(r'Generated from the guides on (\d{4}-\d{2}-\d{2})', committed_silent)
        self.assertIsNotNone(match, 'generated date is missing from SILENT-FAILURES.md')
        generated_date = datetime.date.fromisoformat(match.group(1))
        epoch = int(datetime.datetime.combine(
            generated_date, datetime.time(12), tzinfo=datetime.timezone.utc
        ).timestamp())

        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            callouts, symbols, output = temporary / 'callouts.tsv', temporary / 'symbols.tsv', temporary / 'out'
            output.mkdir()

            extracted_callouts = self.run_command(sys.executable, 'scripts/extract-callouts.py', 'guides')
            self.assertEqual(extracted_callouts.returncode, 0, extracted_callouts.stderr)
            callouts.write_text(extracted_callouts.stdout, encoding='utf-8')

            extracted_symbols = self.run_command(sys.executable, 'scripts/extract-symbols.py')
            self.assertEqual(extracted_symbols.returncode, 0, extracted_symbols.stderr)
            symbols.write_text(extracted_symbols.stdout, encoding='utf-8')

            built = self.run_command(
                sys.executable,
                'scripts/build-indexes.py',
                CLASSIFIED,
                callouts,
                symbols,
                'guides',
                output,
                env={'SOURCE_DATE_EPOCH': str(epoch)},
            )
            self.assertEqual(built.returncode, 0, built.stderr)

            for filename in ('SILENT-FAILURES.md', 'API-INDEX.md'):
                self.assertEqual(
                    (output / filename).read_bytes(),
                    (GUIDES / filename).read_bytes(),
                    f'{filename} is stale; run ./scripts/build-indexes.sh',
                )

            api_index = (output / 'API-INDEX.md').read_text(encoding='utf-8')
            self.assertNotIn('](API-INDEX.md', api_index)

            extracted_keys = set()
            for row in extracted_callouts.stdout.splitlines():
                fields = row.split('\t')
                self.assertEqual(len(fields), 8)
                extracted_keys.add((fields[0], fields[2]))
            for line in (output / 'SILENT-FAILURES.md').read_text(encoding='utf-8').splitlines():
                if not line.startswith('- ['):
                    continue
                link = re.search(r'\]\(([^)#]+)(?:#([^)]+))?\)', line)
                self.assertIsNotNone(link, line)
                self.assertIn((link.group(1), link.group(2) or ''), extracted_keys, line)

            part17 = 'part-17-migration-from-pre-ios-27/references/06-toolchain-and-asset-compatibility.md'
            rendered = (output / 'SILENT-FAILURES.md').read_text(encoding='utf-8')
            # The ⚠️ headings anchor at #️-… on github.com: the warning sign is
            # dropped but its variation selector U+FE0F survives as a mark.
            for suffix in ('', '-1', '-2', '-3'):
                self.assertIn(f'{part17}#️-the-silent-failure{suffix})', rendered)


if __name__ == '__main__':
    unittest.main()
