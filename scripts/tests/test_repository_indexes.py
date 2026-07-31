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


REPO = Path(__file__).resolve().parents[2]
GUIDES = REPO / 'guides'
CLASSIFIED = REPO / 'notes' / 'synthesis' / 'callout-classifications'


class RepositoryIndexTests(unittest.TestCase):
    maxDiff = 2000

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
                self.assertEqual(len(fields), 6)
                extracted_keys.add((fields[0], fields[2]))
            for line in (output / 'SILENT-FAILURES.md').read_text(encoding='utf-8').splitlines():
                if not line.startswith('- ['):
                    continue
                link = re.search(r'\]\(([^)#]+)(?:#([^)]+))?\)', line)
                self.assertIsNotNone(link, line)
                self.assertIn((link.group(1), link.group(2) or ''), extracted_keys, line)

            part17 = 'part-17-migration-from-pre-ios-27/references/06-toolchain-and-asset-compatibility.md'
            rendered = (output / 'SILENT-FAILURES.md').read_text(encoding='utf-8')
            for suffix in ('', '-1', '-2', '-3'):
                self.assertIn(f'{part17}#the-silent-failure{suffix})', rendered)


if __name__ == '__main__':
    unittest.main()
