#!/usr/bin/env python3
"""Regression tests for the guide index extraction and validation tooling."""

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
ANCHOR_SECTION_LINKS = REPO / 'scripts' / 'anchor-section-links.py'


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
            rows = [line.split('\t') for line in result.stdout.splitlines()]
            self.assertEqual([row[2] for row in rows], ['repeated', 'repeated-1', 'repeated-2'])

    def test_fenced_hash_lines_are_not_headings(self):
        with tempfile.TemporaryDirectory() as directory:
            guides = Path(directory)
            (guides / 'guide.md').write_text(
                '# Real heading\n\n'
                '```python\n'
                '# fake heading in code\n'
                '```\n\n'
                '⚠️ after the fence\n',
                encoding='utf-8',
            )
            result = self.run_python(EXTRACT_CALLOUTS, guides)
            self.assertEqual(result.returncode, 0, result.stderr)
            rows = [line.split('\t') for line in result.stdout.splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][2], 'real-heading')

    def test_tilde_fences_match_character_and_length(self):
        with tempfile.TemporaryDirectory() as directory:
            guides = Path(directory)
            (guides / 'guide.md').write_text(
                '# Real heading\n\n'
                '~~~~markdown\n'
                '```\n'
                '~~~\n'
                '# fake heading in code\n'
                '~~~~\n\n'
                '⚠️ after the fence\n',
                encoding='utf-8',
            )
            result = self.run_python(EXTRACT_CALLOUTS, guides)
            self.assertEqual(result.returncode, 0, result.stderr)
            rows = [line.split('\t') for line in result.stdout.splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][2], 'real-heading')

    def test_heading_slug_preserves_double_hyphen_around_punctuation(self):
        with tempfile.TemporaryDirectory() as directory:
            guides = Path(directory)
            (guides / 'guide.md').write_text(
                '# Gate A — graph parity\n\n⚠️ warning\n',
                encoding='utf-8',
            )
            result = self.run_python(EXTRACT_CALLOUTS, guides)
            self.assertEqual(result.returncode, 0, result.stderr)
            rows = [line.split('\t') for line in result.stdout.splitlines()]
            self.assertEqual(rows[0][2], 'gate-a--graph-parity')

    def test_heading_slug_matches_github_for_emoji_and_snake_case(self):
        # GitHub keeps the emoji's variation selector (a Unicode mark), the
        # hyphen minted by the space after the dropped emoji, and underscores
        # inside code spans: ⚠️-headed sections anchor at #️-… on github.com.
        with tempfile.TemporaryDirectory() as directory:
            guides = Path(directory)
            (guides / 'guide.md').write_text(
                '# ⚠️ The chicken-and-egg\n\n'
                '## What `strip_debug_info` actually does\n\n'
                '⚠️ warning\n',
                encoding='utf-8',
            )
            result = self.run_python(EXTRACT_CALLOUTS, guides)
            self.assertEqual(result.returncode, 0, result.stderr)
            rows = [line.split('\t') for line in result.stdout.splitlines()]
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0][2], '️-the-chicken-and-egg')
            self.assertEqual(rows[1][2], 'what-strip_debug_info-actually-does')

    def test_fenced_warning_lines_extract_as_inline_with_outer_anchor(self):
        with tempfile.TemporaryDirectory() as directory:
            guides = Path(directory)
            (guides / 'guide.md').write_text(
                '# Real heading\n\n'
                '```swift\n'
                'var x: Int? // ⚠️ CONSUMING read\n'
                '# ⚠️ fake heading warning\n'
                '```\n',
                encoding='utf-8',
            )
            result = self.run_python(EXTRACT_CALLOUTS, guides)
            self.assertEqual(result.returncode, 0, result.stderr)
            rows = [line.split('\t') for line in result.stdout.splitlines()]
            self.assertEqual([(row[2], row[3]) for row in rows],
                             [('real-heading', 'INLINE'), ('real-heading', 'INLINE')])

    def test_blockquote_wrapped_fences_do_not_toggle_state(self):
        with tempfile.TemporaryDirectory() as directory:
            guides = Path(directory)
            (guides / 'guide.md').write_text(
                '# Top\n\n'
                '> ```swift\n'
                '> let a = 1\n'
                '> ```\n\n'
                '# After quote\n\n'
                '⚠️ anchored to the second heading\n',
                encoding='utf-8',
            )
            result = self.run_python(EXTRACT_CALLOUTS, guides)
            self.assertEqual(result.returncode, 0, result.stderr)
            rows = [line.split('\t') for line in result.stdout.splitlines()]
            self.assertEqual([row[2] for row in rows], ['after-quote'])

    def test_list_indented_fences_are_tracked(self):
        with tempfile.TemporaryDirectory() as directory:
            guides = Path(directory)
            (guides / 'guide.md').write_text(
                '# Real heading\n\n'
                '- item:\n'
                '  ```bash\n'
                '  # fake heading\n'
                '  ```\n\n'
                '⚠️ after the list fence\n',
                encoding='utf-8',
            )
            result = self.run_python(EXTRACT_CALLOUTS, guides)
            self.assertEqual(result.returncode, 0, result.stderr)
            rows = [line.split('\t') for line in result.stdout.splitlines()]
            self.assertEqual([row[2] for row in rows], ['real-heading'])

    def test_longer_fence_swallows_bare_backtick_fence(self):
        with tempfile.TemporaryDirectory() as directory:
            guides = Path(directory)
            (guides / 'guide.md').write_text(
                '# Real heading\n\n'
                '````markdown\n'
                '```\n'
                '# fake heading\n'
                '```\n'
                '````\n\n'
                '⚠️ after the outer fence\n',
                encoding='utf-8',
            )
            result = self.run_python(EXTRACT_CALLOUTS, guides)
            self.assertEqual(result.returncode, 0, result.stderr)
            rows = [line.split('\t') for line in result.stdout.splitlines()]
            self.assertEqual([row[2] for row in rows], ['real-heading'])

    def test_unterminated_fence_is_a_hard_error(self):
        with tempfile.TemporaryDirectory() as directory:
            guides = Path(directory)
            (guides / 'guide.md').write_text(
                '# Real heading\n\n'
                '```swift\n'
                'let a = 1\n',
                encoding='utf-8',
            )
            result = self.run_python(EXTRACT_CALLOUTS, guides)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('unterminated', result.stderr)
            self.assertIn('guide.md:3', result.stderr)

    def test_semantic_id_survives_line_movement_but_hash_tracks_text(self):
        with tempfile.TemporaryDirectory() as directory:
            guides = Path(directory)
            path = guides / 'guide.md'
            path.write_text('# Section\n\n⚠️ stable warning\n', encoding='utf-8')
            first = self.run_python(EXTRACT_CALLOUTS, guides)
            self.assertEqual(first.returncode, 0, first.stderr)
            path.write_text('# Section\n\nextra prose\n\n⚠️ stable warning\n', encoding='utf-8')
            moved = self.run_python(EXTRACT_CALLOUTS, guides)
            self.assertEqual(moved.returncode, 0, moved.stderr)
            path.write_text('# Section\n\nextra prose\n\n⚠️ changed warning\n', encoding='utf-8')
            changed = self.run_python(EXTRACT_CALLOUTS, guides)
            self.assertEqual(changed.returncode, 0, changed.stderr)
            first_row = first.stdout.strip().split('\t')
            moved_row = moved.stdout.strip().split('\t')
            changed_row = changed.stdout.strip().split('\t')
            self.assertNotEqual(first_row[1], moved_row[1])
            self.assertEqual(first_row[6:], moved_row[6:])
            self.assertNotEqual(moved_row[6:], changed_row[6:])

    def test_callout_hash_covers_text_beyond_the_display_excerpt(self):
        with tempfile.TemporaryDirectory() as directory:
            guides = Path(directory)
            path = guides / 'guide.md'
            prefix = '⚠️ ' + ('x' * 450)
            path.write_text(f'# Section\n\n{prefix} first\n', encoding='utf-8')
            first = self.run_python(EXTRACT_CALLOUTS, guides)
            self.assertEqual(first.returncode, 0, first.stderr)
            path.write_text(f'# Section\n\n{prefix} second\n', encoding='utf-8')
            changed = self.run_python(EXTRACT_CALLOUTS, guides)
            self.assertEqual(changed.returncode, 0, changed.stderr)
            first_row = first.stdout.strip().split('\t')
            changed_row = changed.stdout.strip().split('\t')
            self.assertEqual(first_row[5], changed_row[5])
            self.assertEqual(first_row[6], changed_row[6])
            self.assertNotEqual(first_row[7], changed_row[7])

    def test_blockquote_hash_covers_context_before_warning_line(self):
        with tempfile.TemporaryDirectory() as directory:
            guides = Path(directory)
            path = guides / 'guide.md'
            path.write_text(
                '# Section\n\n> first context\n> ⚠️ **Warning** — stable text\n',
                encoding='utf-8',
            )
            first = self.run_python(EXTRACT_CALLOUTS, guides)
            self.assertEqual(first.returncode, 0, first.stderr)
            path.write_text(
                '# Section\n\n> changed context\n> ⚠️ **Warning** — stable text\n',
                encoding='utf-8',
            )
            changed = self.run_python(EXTRACT_CALLOUTS, guides)
            self.assertEqual(changed.returncode, 0, changed.stderr)
            first_row = first.stdout.strip().split('\t')
            changed_row = changed.stdout.strip().split('\t')
            self.assertEqual(first_row[5:7], changed_row[5:7])
            self.assertNotEqual(first_row[7], changed_row[7])

    def test_duplicate_semantic_callout_requires_explicit_override(self):
        with tempfile.TemporaryDirectory() as directory:
            guides = Path(directory)
            path = guides / 'guide.md'
            path.write_text('# Section\n\n⚠️ duplicate\n\n⚠️ duplicate\n', encoding='utf-8')
            duplicate = self.run_python(EXTRACT_CALLOUTS, guides)
            self.assertNotEqual(duplicate.returncode, 0)
            self.assertIn('duplicate callout id', duplicate.stderr)
            path.write_text(
                '# Section\n\n⚠️ duplicate\n\n<!-- callout-id: second-duplicate -->\n⚠️ duplicate\n',
                encoding='utf-8',
            )
            explicit = self.run_python(EXTRACT_CALLOUTS, guides)
            self.assertEqual(explicit.returncode, 0, explicit.stderr)
            self.assertEqual(explicit.stdout.splitlines()[1].split('\t')[6], 'second-duplicate')

    def test_duplicate_inside_fence_uses_hidden_occurrence_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            guides = Path(directory)
            path = guides / 'guide.md'
            path.write_text(
                '# Section\n\n```text\n⚠️ duplicate\n⚠️ duplicate\n```\n', encoding='utf-8'
            )
            result = self.run_python(EXTRACT_CALLOUTS, guides)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('<!-- callout-id: slug occurrence:N -->', result.stderr)
            path.write_text(
                '# Section\n\n<!-- callout-id: second occurrence:2 -->\n'
                '```text\n⚠️ duplicate\n⚠️ duplicate\n```\n',
                encoding='utf-8',
            )
            explicit = self.run_python(EXTRACT_CALLOUTS, guides)
            self.assertEqual(explicit.returncode, 0, explicit.stderr)
            self.assertEqual(explicit.stdout.splitlines()[1].split('\t')[6], 'second')

    def test_unconsumed_and_reader_visible_callout_markers_are_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            guides = Path(directory)
            path = guides / 'guide.md'
            path.write_text(
                '<!-- callout-id: unused -->\nordinary prose\n', encoding='utf-8'
            )
            unused = self.run_python(EXTRACT_CALLOUTS, guides)
            self.assertNotEqual(unused.returncode, 0)
            self.assertIn('not followed by its designated callout', unused.stderr)
            path.write_text(
                '```swift\n// callout-id: visible\n// ⚠️ warning\n```\n',
                encoding='utf-8',
            )
            visible = self.run_python(EXTRACT_CALLOUTS, guides)
            self.assertNotEqual(visible.returncode, 0)
            self.assertIn('must not appear inside a published code fence', visible.stderr)

    def test_callout_marker_cannot_cross_heading_or_use_occurrence_outside_fence(self):
        with tempfile.TemporaryDirectory() as directory:
            guides = Path(directory)
            path = guides / 'guide.md'
            path.write_text(
                '<!-- callout-id: misplaced -->\n# Heading\n\n⚠️ warning\n',
                encoding='utf-8',
            )
            heading = self.run_python(EXTRACT_CALLOUTS, guides)
            self.assertNotEqual(heading.returncode, 0)
            self.assertIn('not followed by its designated callout', heading.stderr)
            path.write_text(
                '<!-- callout-id: misplaced occurrence:2 -->\n⚠️ warning\n',
                encoding='utf-8',
            )
            occurrence = self.run_python(EXTRACT_CALLOUTS, guides)
            self.assertNotEqual(occurrence.returncode, 0)
            self.assertIn('occurrence is only valid for an in-fence callout', occurrence.stderr)

    def test_fenced_fake_heading_does_not_consume_slug_suffixes(self):
        with tempfile.TemporaryDirectory() as directory:
            guides = Path(directory)
            (guides / 'guide.md').write_text(
                '# Repeated\n\n⚠️ first\n\n'
                '```python\n'
                '# Repeated\n'
                '```\n\n'
                '# Repeated\n\n⚠️ second\n',
                encoding='utf-8',
            )
            result = self.run_python(EXTRACT_CALLOUTS, guides)
            self.assertEqual(result.returncode, 0, result.stderr)
            rows = [line.split('\t') for line in result.stdout.splitlines()]
            self.assertEqual([row[2] for row in rows], ['repeated', 'repeated-1'])

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
            groups = {row[0]: row[1] for row in
                      (line.split('\t') for line in result.stdout.splitlines())}
            self.assertEqual(groups['FoundationModels'], 'FoundationModels')
            self.assertEqual(groups['CoreAI'], 'CoreAI')
            self.assertEqual(groups['CoreAILanguageModel'], 'FoundationModels')
            self.assertEqual(groups['Evaluator'], 'Evaluations')
            self.assertNotIn('PoisonSymbol', groups)
            self.assertNotIn('OtherPoison', groups)

    def test_symbol_presence_checks_every_type_level_component(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            guides, interfaces = root / 'guides', root / 'interfaces'
            guides.mkdir()
            interfaces.mkdir()
            (guides / 'guide.md').write_text(
                '`Transcript.CustomSegment` `Transcript.CustomSegment`\n'
                '`Transcript.Entry` `Transcript.Entry`\n'
                '`Transcript.entries(in:)` `Transcript.entries(in:)`\n',
                encoding='utf-8',
            )
            (interfaces / 'FM-27.0-macos.swiftinterface').write_text(
                'public struct Transcript {\n  public struct Entry {}\n}\n',
                encoding='utf-8',
            )
            result = self.run_python(EXTRACT_SYMBOLS, guides, interfaces)
            self.assertEqual(result.returncode, 0, result.stderr)
            in27 = {row[0]: row[5] for row in
                    (line.split('\t') for line in result.stdout.splitlines())}
            self.assertEqual(in27['Transcript.Entry'], 'Y')
            # parent presence must not vouch for a vanished nested type
            self.assertEqual(in27['Transcript.CustomSegment'], '')
            # lowercase members still resolve via the type component
            self.assertEqual(in27['Transcript.entries(in:)'], 'Y')

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
                for row in (line.split('\t') for line in result.stdout.splitlines())
            }
            self.assertEqual(
                rows['TieSymbol'][6],
                'a-first.md:2;m-middle.md:2;z-last.md:2',
            )

    def test_symbol_extractor_ignores_fences_and_non_symbol_literals(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            guides, interfaces = root / 'guides', root / 'interfaces'
            guides.mkdir()
            interfaces.mkdir()
            (guides / 'guide.md').write_text(
                '`RealSymbol` `RealSymbol`\n'
                '`ArchiveName.zip` `ArchiveName.zip`\n'
                '`J0hn` `J0hn`\n'
                '```swift\n'
                '`FencedSymbol` `FencedSymbol`\n'
                '```\n\n'
                '> ~~~python\n'
                '> `QuotedFenceSymbol` `QuotedFenceSymbol`\n'
                '> ~~~\n',
                encoding='utf-8',
            )
            result = self.run_python(EXTRACT_SYMBOLS, guides, interfaces)
            self.assertEqual(result.returncode, 0, result.stderr)
            symbols = {line.split('\t')[0] for line in result.stdout.splitlines()}
            self.assertEqual(symbols, {'RealSymbol'})

    def test_section_link_tool_adds_and_verifies_github_fragments(self):
        with tempfile.TemporaryDirectory() as directory:
            guides = Path(directory) / 'guides'
            part = guides / 'part-01-example'
            references = part / 'references'
            references.mkdir(parents=True)
            readme = part / 'README.md'
            readme.write_text(
                '# Part 1\n\n[Read 1.1 §2.1](references/01-guide.md)\n\n'
                '```markdown\n[Example §2.1](references/01-guide.md)\n```\n',
                encoding='utf-8',
            )
            (references / '01-guide.md').write_text(
                '# Guide\n\n```markdown\n### 2.1 Fake section\n```\n\n'
                '### 2.1 Real section\n',
                encoding='utf-8',
            )
            written = self.run_python(ANCHOR_SECTION_LINKS, guides, '--write')
            self.assertEqual(written.returncode, 0, written.stderr)
            self.assertIn(
                '(references/01-guide.md#21-real-section)',
                readme.read_text(encoding='utf-8'),
            )
            self.assertIn(
                '[Example §2.1](references/01-guide.md)',
                readme.read_text(encoding='utf-8'),
            )
            verified = self.run_python(ANCHOR_SECTION_LINKS, guides)
            self.assertEqual(verified.returncode, 0, verified.stderr)

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
        (classified / 'root.tsv').write_text(
            ''.join('\t'.join(str(field) for field in row) + '\n' for row in classification_rows),
            encoding='utf-8',
        )
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

    def test_source_date_epoch_is_timezone_independent(self):
        row = ['guide.md', '3', 'section', 'CALLOUT', 'caution-note', 'A warning']
        honolulu, honolulu_result = self.run_builder(
            [row], env={'SOURCE_DATE_EPOCH': '0', 'TZ': 'Pacific/Honolulu'}
        )
        kiritimati, kiritimati_result = self.run_builder(
            [row], env={'SOURCE_DATE_EPOCH': '0', 'TZ': 'Pacific/Kiritimati'}
        )
        self.addCleanup(honolulu[0].cleanup)
        self.addCleanup(kiritimati[0].cleanup)
        self.assertEqual(honolulu_result.returncode, 0, honolulu_result.stderr)
        self.assertEqual(kiritimati_result.returncode, 0, kiritimati_result.stderr)
        for filename in ('SILENT-FAILURES.md', 'API-INDEX.md'):
            self.assertEqual(
                (honolulu[-1] / filename).read_bytes(),
                (kiritimati[-1] / filename).read_bytes(),
            )

    def test_quotes_in_blurbs_stay_literal(self):
        blurb = 'The README\'s .package(from:"1.0.0") can never resolve'
        fixture, result = self.run_builder(
            [['guide.md', '3', 'section', 'CALLOUT', 'docs-vs-reality', blurb]]
        )
        self.addCleanup(fixture[0].cleanup)
        self.assertEqual(result.returncode, 0, result.stderr)
        rendered = (fixture[-1] / 'SILENT-FAILURES.md').read_text(encoding='utf-8')
        self.assertIn(f'[{blurb}]', rendered)

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

    def test_v2_classification_survives_line_only_movement(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            guides, classified, output = root / 'guides', root / 'classified', root / 'output'
            guides.mkdir(); classified.mkdir(); output.mkdir()
            guide = guides / 'guide.md'
            guide.write_text('# Section\n\n> ⚠️ **A warning.** Details.\n', encoding='utf-8')
            extracted = self.run_python(EXTRACT_CALLOUTS, guides)
            self.assertEqual(extracted.returncode, 0, extracted.stderr)
            row = extracted.stdout.strip().split('\t')
            classification = [row[0], row[6], row[7], row[2], row[3],
                              'caution-note', 'A warning']
            (classified / 'root.tsv').write_text(
                '# schema-version: 2\n' + '\t'.join(classification) + '\n', encoding='utf-8'
            )
            guide.write_text('# Section\n\nInserted prose.\n\n> ⚠️ **A warning.** Details.\n',
                             encoding='utf-8')
            moved = self.run_python(EXTRACT_CALLOUTS, guides)
            self.assertEqual(moved.returncode, 0, moved.stderr)
            callouts = root / 'callouts.tsv'; callouts.write_text(moved.stdout, encoding='utf-8')
            symbols = root / 'symbols.tsv'
            symbols.write_text('FoundationModels\tFoundationModels\t2\t1\tY\tY\tguide.md:2\n',
                               encoding='utf-8')
            result = self.run_python(BUILD_INDEXES, classified, callouts, symbols, guides, output)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
