#!/usr/bin/env python3
"""Regression tests for the guide index extraction and validation tooling."""

import csv
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
EXTRACT_CALLOUTS = REPO / 'scripts' / 'extract-callouts.py'
EXTRACT_SYMBOLS = REPO / 'scripts' / 'extract-symbols.py'
BUILD_INDEXES = REPO / 'scripts' / 'build-indexes.py'


class IndexToolingTests(unittest.TestCase):
    def run_python(self, script, *arguments, env=None):
        return subprocess.run(
            [sys.executable, str(script), *(str(argument) for argument in arguments)],
            cwd=REPO,
            env={**os.environ, **(env or {})},
            text=True,
            capture_output=True,
            check=False,
        )

    def test_duplicate_heading_slugs_are_unique(self):
        with tempfile.TemporaryDirectory() as directory:
            guides = Path(directory)
            (guides / 'guide.md').write_text(
                '# Repeated\n\n⚠️ first\n\n'
                '# Repeated\n\n⚠️ second\n\n'
                '# Repeated\n\n⚠️ third\n',
                encoding='utf-8',
            )
            result = self.run_python(EXTRACT_CALLOUTS, guides)
            self.assertEqual(result.returncode, 0, result.stderr)
            rows = list(csv.reader(result.stdout.splitlines(), delimiter='\t'))
            self.assertEqual([row[2] for row in rows], ['repeated', 'repeated-1', 'repeated-2'])

    def test_symbol_extractor_excludes_generated_indexes_and_groups_literals(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            guides, interfaces = root / 'guides', root / 'interfaces'
            guides.mkdir()
            interfaces.mkdir()
            (guides / 'guide.md').write_text(
                '`FoundationModels` `FoundationModels`\n'
                '`CoreAI` `CoreAI`\n'
                '`CoreAILanguageModel` `CoreAILanguageModel`\n'
                '`Evaluator` `Evaluator`\n',
                encoding='utf-8',
            )
            (guides / 'API-INDEX.md').write_text('`PoisonSymbol` ' * 20, encoding='utf-8')
            (guides / 'SILENT-FAILURES.md').write_text('`OtherPoison` ' * 20, encoding='utf-8')
            result = self.run_python(EXTRACT_SYMBOLS, guides, interfaces)
            self.assertEqual(result.returncode, 0, result.stderr)
            groups = {row[0]: row[1] for row in csv.reader(result.stdout.splitlines(), delimiter='\t')}
            self.assertEqual(groups['FoundationModels'], 'FoundationModels')
            self.assertEqual(groups['CoreAI'], 'CoreAI')
            self.assertEqual(groups['CoreAILanguageModel'], 'FoundationModels')
            self.assertEqual(groups['Evaluator'], 'Evaluations')
            self.assertNotIn('PoisonSymbol', groups)
            self.assertNotIn('OtherPoison', groups)

    def test_symbol_extractor_breaks_equal_count_ties_by_guide_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            guides, interfaces = root / 'guides', root / 'interfaces'
            guides.mkdir()
            interfaces.mkdir()
            for name in ('z-last.md', 'a-first.md', 'm-middle.md'):
                (guides / name).write_text('`TieSymbol` `TieSymbol`\n', encoding='utf-8')
            result = self.run_python(EXTRACT_SYMBOLS, guides, interfaces)
            self.assertEqual(result.returncode, 0, result.stderr)
            rows = {
                row[0]: row
                for row in csv.reader(result.stdout.splitlines(), delimiter='\t')
            }
            self.assertEqual(
                rows['TieSymbol'][6],
                'a-first.md:2;m-middle.md:2;z-last.md:2',
            )

    def build_fixture(self, classification_rows):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        guides, classified, output = root / 'guides', root / 'classified', root / 'output'
        guides.mkdir()
        classified.mkdir()
        output.mkdir()
        (guides / 'guide.md').write_text('# Section\n\n> ⚠️ **A warning.** Details.\n', encoding='utf-8')
        callouts = root / 'callouts.tsv'
        extracted = self.run_python(EXTRACT_CALLOUTS, guides)
        self.assertEqual(extracted.returncode, 0, extracted.stderr)
        callouts.write_text(extracted.stdout, encoding='utf-8')
        symbols = root / 'symbols.tsv'
        symbols.write_text('FoundationModels\tFoundationModels\t2\t1\tY\tY\tguide.md:2\n', encoding='utf-8')
        with (classified / 'root.tsv').open('w', encoding='utf-8', newline='') as stream:
            csv.writer(stream, delimiter='\t', lineterminator='\n').writerows(classification_rows)
        return temporary, guides, classified, callouts, symbols, output

    def run_builder(self, classification_rows, env=None):
        fixture = self.build_fixture(classification_rows)
        temporary, guides, classified, callouts, symbols, output = fixture
        result = self.run_python(
            BUILD_INDEXES, classified, callouts, symbols, guides, output, env=env
        )
        return fixture, result

    def test_valid_classification_builds_with_reproducible_date(self):
        fixture, result = self.run_builder(
            [['guide.md', '3', 'section', 'CALLOUT', 'caution-note', 'A warning']],
            env={'SOURCE_DATE_EPOCH': '0'},
        )
        self.addCleanup(fixture[0].cleanup)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('1970-01-01', (fixture[-1] / 'SILENT-FAILURES.md').read_text(encoding='utf-8'))

    def test_unknown_symptom_fails(self):
        fixture, result = self.run_builder(
            [['guide.md', '3', 'section', 'CALLOUT', 'not-a-symptom', 'A warning']]
        )
        self.addCleanup(fixture[0].cleanup)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('unknown symptom id', result.stderr)

    def test_malformed_row_fails(self):
        fixture, result = self.run_builder([['guide.md', '3', 'section']])
        self.addCleanup(fixture[0].cleanup)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('expected 6 TSV columns', result.stderr)

    def test_duplicate_classification_fails(self):
        row = ['guide.md', '3', 'section', 'CALLOUT', 'caution-note', 'A warning']
        fixture, result = self.run_builder([row, row])
        self.addCleanup(fixture[0].cleanup)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('duplicate classification key', result.stderr)

    def test_missing_or_stale_classification_fails(self):
        fixture, result = self.run_builder(
            [['guide.md', '3', 'wrong-anchor', 'CALLOUT', 'caution-note', 'A warning']]
        )
        self.addCleanup(fixture[0].cleanup)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('do not exactly match a fresh extraction', result.stderr)


if __name__ == '__main__':
    unittest.main()
