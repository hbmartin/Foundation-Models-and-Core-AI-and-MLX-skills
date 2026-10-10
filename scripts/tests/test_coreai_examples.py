import subprocess
import sys
import unittest
from pathlib import Path

from scripts.coreai_examples import (
    contract_errors, optimizer_calls, overwrite_contract_errors, python_fences, section,
)
from scripts.mdlinks import iter_lines

ROOT = Path(__file__).resolve().parents[2]
OVERWRITE_STATEMENT = (
    "AIProgram.save_asset in coreai-core 1.0.0b3 replaces an existing file or directory "
    "at the destination."
)


class CoreAIExampleTests(unittest.TestCase):
    def test_version_comparisons_do_not_exempt_current_claims(self):
        for claim in (
            'Unlike in coreai-core 1.0.0b2, save_asset does not overwrite the destination.',
            'save_asset does not overwrite the destination, as it did in coreai-core 1.0.0b2.',
            'The b3 converter does not overwrite the destination (it did in coreai-core 1.0.0b2).',
            'The destination is not overwritten, as in coreai-core 1.0.0b2.',
            'Unlike in coreai-core 1.0.0b2, the destination is not overwritten.',
            'save_asset writes a bundle, as in coreai-core 1.0.0b2. It does not overwrite the destination.',
            'In coreai-core 1.0.0b2, save_asset does not overwrite the destination, but save_asset does not overwrite the destination.',
            'save_asset in coreai-core 1.0.0b2 preserves files, and save_asset does not overwrite the destination.',
        ):
            with self.subTest(claim=claim):
                self.assertEqual(['b3 overwrite behavior incorrect'], contract_errors(claim, 'overwrite'))
                self.assertEqual(['b3 overwrite behavior incorrect'],
                                 overwrite_contract_errors(OVERWRITE_STATEMENT + '\n\n' + claim))
        for claim in (
            'In coreai-core 1.0.0b2, save_asset does not overwrite the destination.',
            'save_asset in coreai-core 1.0.0b2 does not overwrite the destination.',
            'The destination in coreai-core 1.0.0b2 is not overwritten.',
            'In coreai-core 1.0.0b2, save_asset writes a bundle. It does not overwrite the destination.',
            'save_asset in coreai-core 1.0.0b2 validates the destination but does not overwrite it.',
            'save_asset in coreai-core 1.0.0b2 preserves files. It raises FileExistsError.',
            'In coreai-core 1.0.0b2, save_asset preserves files. mlx_lm.convert writes a bundle. It does not overwrite the destination.',
        ):
            with self.subTest(claim=claim):
                self.assertEqual([], contract_errors(claim, 'overwrite'))

    def test_bold_callout_titles_and_bodies_keep_their_claims(self):
        for claim in (
            '> ⚠️ **SILENT FAILURE — The destination is not overwritten.**',
            '> ⚠️ **SILENT FAILURE — The destination\n> is not overwritten.**',
            '> ⚠️ **SILENT FAILURE — save_asset does not overwrite the destination.**',
            '> ⚠️ **The destination is not overwritten.** Later explanation.',
            '> ⚠️ **WARNING — The destination is not overwritten.** Later explanation.',
            '> ⚠️ **A descriptive title** — The destination is not overwritten.',
            '> ✅ **VERIFIED (b3 source)** — The destination is not overwritten.',
        ):
            with self.subTest(claim=claim):
                self.assertEqual(['b3 overwrite behavior incorrect'], contract_errors(claim, 'overwrite'))
                self.assertEqual([], contract_errors(claim.replace('not ', ''), 'overwrite'))

    def test_preservation_continuations_keep_their_explicit_agent(self):
        for verb in ('preserved', 'retained', 'kept'):
            for agent, rejected in (('', True), (' by save_asset', True),
                                    (' by mlx_lm.convert', False), (' by another_tool', False),
                                    (' by default', True)):
                claim = f'The destination is not overwritten but {verb}{agent}.'
                with self.subTest(claim=claim):
                    self.assertEqual(['b3 overwrite behavior incorrect'] if rejected else [],
                                     contract_errors(claim, 'overwrite'))

    def test_bare_file_exists_error_and_existence_word_orders(self):
        for claim in ('save_asset will fail with FileExistsError.',
                      'save_asset fails immediately with a FileExistsError.',
                      'save_asset raises FileExistsError.'):
            with self.subTest(claim=claim):
                self.assertEqual(['b3 overwrite behavior incorrect'], contract_errors(claim, 'overwrite'))
        for condition in ('the destination already exists', 'the destination exists already',
                          'the destination exists on disk', 'the destination exists on disk already',
                          'the destination already exists on disk',
                          'something exists at the destination already'):
            with self.subTest(condition=condition):
                self.assertEqual(['b3 overwrite behavior incorrect'], contract_errors(
                    f'save_asset will fail if {condition}.', 'overwrite'))
                self.assertEqual([], contract_errors(
                    f'save_asset will not fail if {condition}.', 'overwrite'))
        for claim in ('save_asset will not fail with FileExistsError.',
                      'mlx_lm.convert will fail with FileExistsError.',
                      'save_asset will fail with an error.',
                      'save_asset will fail with FileExistsError if the metadata record already exists.',
                      'save_asset will fail if the destination exists on disk already, and is read-only.'):
            with self.subTest(claim=claim):
                self.assertEqual([], contract_errors(claim, 'overwrite'))

    def test_reviewed_overwrite_regressions_and_coverage_gaps(self):
        claims = (
            'save_asset writes the bundle, but an existing destination is not overwritten.',
            'save_asset writes the bundle, while the destination directory is not overwritten.',
            'save_asset writes the bundle, whereas an existing destination is not overwritten.',
            'save_asset will fail if a file already exists at the destination.',
            'save_asset will fail if the destination exists on disk.',
            'save_asset will fail if the destination exists already.',
            'save_asset will fail with FileExistsError if the destination already exists.',
            'save_asset fails immediately when the destination already exists.',
            'If the destination exists, save_asset will fail with an error.',
            'save_asset will fail if the destination exists, and you must delete it first.',
            'save_asset will fail if the destination exists, but you should choose another name.',
            'The destination is not replaced but preserved.',
            'The destination is not overwritten by default.',
            'The destination is not overwritten, by default.',
            'The destination is not overwritten, which save_asset relies on.',
            '> ✅ **VERIFIED (b3 source)** — The destination is not overwritten.',
            '- ⚠️ **Warning** — The destination is not overwritten.',
            '> ⚠️ **SILENT FAILURE:** The destination is not overwritten.',
            'In coreai-core 1.0.0b3, the destination is not overwritten.',
            '| save_asset | does not overwrite the destination |',
            'save_asset saves the bundle, and it does not overwrite the destination.',
        )
        for claim in claims:
            with self.subTest(claim=claim):
                self.assertEqual(['b3 overwrite behavior incorrect'], contract_errors(claim, 'overwrite'))
                self.assertEqual(['b3 overwrite behavior incorrect'],
                                 overwrite_contract_errors(OVERWRITE_STATEMENT + '\n\n' + claim))
                affirmative = claim.replace('not ', '').replace('will fail', 'will not fail').replace('fails ', 'never fails ')
                self.assertEqual([], contract_errors(affirmative, 'overwrite'))

    def test_reviewed_false_positives_and_condition_ownership(self):
        for text in (
            'The destination is not overwritten, which mlx_lm.convert relies on.',
            'Save the tokenizer with save_pretrained(dir); it will not overwrite existing files.',
            'save_asset will fail validation if the destination already exists.',
            'save_asset will fail if the destination exists, and is read-only.',
            'save_asset will fail if the destination exists, and the destination is read-only.',
            'save_asset will fail if the destination exists, and the existing destination is read-only.',
            'save_asset will fail if the destination exists but is read-only.',
            'save_asset will not fail with FileExistsError if the destination already exists.',
            'mlx_lm.convert will fail with FileExistsError if the destination already exists.',
            'The destination is not overwritten by another_tool.',
            'In coreai-core 1.0.0b2, the destination is not overwritten.',
            '- save_asset saves the bundle.\n- It does not overwrite the destination.',
            '| save_asset | saves the bundle |\n| it | does not overwrite the destination |',
            '| mlx_lm.convert | does not overwrite the destination |',
            'save_asset writes the bundle, and mlx_lm.convert does not overwrite the destination.',
            'save_asset metadata writes a record. It does not overwrite the destination.',
        ):
            with self.subTest(text=text):
                self.assertEqual([], contract_errors(text, 'overwrite'))
                self.assertEqual([], overwrite_contract_errors(OVERWRITE_STATEMENT + '\n\n' + text))

    def test_call_argument_comments_retain_their_owner(self):
        for comment in ('save_asset will NOT overwrite the destination.',
                        'It will not overwrite the destination.',
                        'The destination is not overwritten.'):
            for owner, rejected in (('prog.save_asset', True), ('save_pretrained', False)):
                with self.subTest(comment=comment, owner=owner):
                    # An explicitly named save_asset claim remains attributable
                    # to that API even inside another call's comment.
                    expected = rejected or comment.startswith('save_asset')
                    text = f'```python\n{owner}(out,\n    # {comment}\n    metadata)\n```'
                    self.assertEqual(['b3 overwrite behavior incorrect'] if expected else [],
                                     contract_errors(text, 'overwrite'))

    def test_argument_masking_cannot_swallow_later_prose(self):
        for prefix in ("The save_asset (the converter's API) writes a bundle.",
                       "save_asset(unclosed, description='broken"):
            text = prefix + "\n\nThe destination is not overwritten.\n\nSee the maintainer's note)."
            with self.subTest(prefix=prefix):
                self.assertEqual(['b3 overwrite behavior incorrect'], contract_errors(text, 'overwrite'))
        self.assertEqual(['b3 overwrite behavior incorrect'], contract_errors(
            "save_asset (the converter's API) does not overwrite the destination.", 'overwrite'))
        for arguments in ('r"path_(copy)"', "'can\\'t )'", 'make_metadata(version())',
                          'description="""first\n\nsecond )"""'):
            text = f'```python\nprog.save_asset(out, {arguments}) does not overwrite the destination.\n```'
            with self.subTest(arguments=arguments):
                self.assertEqual(['b3 overwrite behavior incorrect'], contract_errors(text, 'overwrite'))

    def test_table_delimiters_do_not_split_code_or_escaped_pipes(self):
        for text in ('| `prog.save_asset("a|b")` | does not overwrite the destination |',
                     '| save_asset | does not overwrite the destination | notes \\| details |'):
            with self.subTest(text=text):
                self.assertEqual(['b3 overwrite behavior incorrect'], contract_errors(text, 'overwrite'))
        self.assertEqual([], contract_errors('| --- | :---: |', 'overwrite'))

    def calls(self, code, fence="```", prefix=""):
        text = f"{prefix}{fence}python\n" + "\n".join(prefix + x for x in code.splitlines())
        text += f"\n{prefix}{fence}\n"
        return optimizer_calls(python_fences(text)[0])

    def test_every_call_form(self):
        for code in ("program.optimize()", "x = program.optimize()", "await program.optimize()",
                     "return program.optimize()", "().to_coreai().optimize()",
                     "(converter.to_coreai().optimize())", "program.\\\n optimize ()",
                     "(program\n . optimize\n ())"):
            for fence in ("```", "~~~~"):
                for prefix in ("", "> ", "> > "):
                    with self.subTest(code=code, fence=fence, prefix=prefix):
                        self.assertEqual(1, len(self.calls(code, fence, prefix)))

    def test_missing_heading_has_context(self):
        with self.assertRaisesRegex(ValueError, "missing heading: ## Missing"):
            section("## Existing\nbody", "## Missing")
        self.assertEqual("## Existing\nbody", section("## Existing\nbody\n## Next", "## Existing"))

    def test_comments_and_strings(self):
        self.assertEqual([], self.calls('# program.optimize()\nx = "program.optimize()"'))

    def test_section_ignores_fenced_headings_and_preserves_body(self):
        for fence in ("```", "~~~~"):
            for prefix in ("", "> ", "> > "):
                body = f"{prefix}{fence}python\n{prefix}# Existing\n{prefix}## Peer\n{prefix}program.optimize()\n{prefix}{fence}\n"
                expected = "## Existing\n" + body + "### Child\ntext\n"
                with self.subTest(fence=fence, prefix=prefix):
                    self.assertTrue(all(fenced for _, _, fenced in iter_lines(body)))
                    self.assertFalse(list(iter_lines(body + "## After\n"))[-1][2])
                    self.assertEqual(expected, section(body + expected + "\n## Peer\nnext", "## Existing"))
                    self.assertIn("program.optimize()", section(expected + "## Peer\nnext", "## Existing"))

    def test_inline_backticks_do_not_open_fences(self):
        for prefix in ("", "> ", "> > "):
            prose = f"{prefix}```code``` is inline prose\n"
            text = prose + "## Existing\nbody\n" + prose + "## Peer\nnext"
            with self.subTest(prefix=prefix):
                self.assertFalse(list(iter_lines(prose))[0][2])
                self.assertEqual("## Existing\nbody\n" + prose.rstrip("\n"), section(text, "## Existing"))
                self.assertEqual([], python_fences(text))
        self.assertEqual(1, len(python_fences('```code```\n```python\nx = 1\n```')))

    def test_shape_predicates_belong_to_the_named_shape(self):
        for text in (
            "square inputs exposed the bug, while unequal (17×23) inputs hid it",
            "square inputs miscompiled; rectangular 17×23 inputs passed",
            "equal-length inputs failed, but unequal-length inputs were correct",
            "Square inputs did not hide the bug; rectangular inputs did not expose it",
            "The bug was exposed by square inputs and hidden by rectangular inputs",
            "The bug was not hidden by square inputs; it was not exposed by rectangular inputs",
            "square inputs were not correct; rectangular 17×23 inputs were correct",
        ):
            with self.subTest(text=text):
                self.assertEqual([], contract_errors(text, "issue49"))
        for text in (
            "square inputs were correct, while unequal (17×23) inputs exposed the bug",
            "square inputs hid the bug and rectangular 17x23 inputs failed",
            "equal-length inputs passed; unequal-length inputs miscompiled",
            "The bug was hidden by square inputs and exposed by rectangular inputs",
        ):
            with self.subTest(text=text):
                self.assertTrue(contract_errors(text, "issue49"))

    def test_overwrite_guard_handles_inflections_and_filename_dots(self):
        for text in (
            "save_asset never overwrites destinations",
            "the destination will not be overwritten",
            "save_asset cannot overwrite destinations",
            "save_asset can’t overwrite destinations",
            "save_asset will fail on an existing destination",
            "save_asset will fail if MyModel.aimodel already exists",
            "save_asset will not replace MyModel.aimodel because it cannot overwrite",
            "save_asset will not\noverwrite the destination",
            "Assets don't overwrite existing destinations",
            "The converter didn’t overwrite the asset",
            "Existing destinations aren't overwritten",
            "save_asset will not replace an existing destination",
            "save_asset cannot replace MyModel.aimodel",
            "save_asset never replaces existing destinations",
            "an existing destination will not be replaced",
            "Assets don't replace existing destinations",
            "The converter didn’t replace the asset",
            "Existing destinations aren't replaced",
            "save_asset will not be replacing an existing destination",
            "save_asset performs no overwriting of existing destinations",
            "save_asset never overwrote the file",
            "The destination is not being overwritten",
            "MyModel.aimodel was not replaced",
            "save_asset did not overwrite",
        ):
            with self.subTest(text=text):
                self.assertTrue(contract_errors(text, "overwrite"))
        for text in ("Note: b3 will overwrite the destination", "It does not merge. It overwrites.",
                     "It will fail during conversion. The asset already exists.",
                     "- Do not optimize the program\n- save_asset overwrites an existing destination",
                     "1. Do not optimize the program\n2. save_asset overwrites an existing destination",
                     "The program is not optimized; the destination is overwritten",
                     "save_asset will replace an existing destination",
                     "The destination is replaced",
                     "- Do not optimize the program\n- save_asset replaces an existing destination",
                     "1. Do not optimize the program\n2. save_asset replaces an existing destination",
                     "The program is not optimized; the destination is replaced"):
            with self.subTest(text=text):
                self.assertEqual([], contract_errors(text, "overwrite"))

    def test_overwrite_guard_ignores_unrelated_prose_in_same_section(self):
        correct_contract = "AIProgram.save_asset replaces an existing file or directory.\n"
        for advice in (
            "Metadata does not replace a parity gate.",
            "Asset metadata does not replace a parity gate.",
            "Parity checks cannot replace validation on production inputs.",
            "save_asset metadata does not replace validation.",
            "Metadata will fail validation if an existing author is missing.",
            "Asset validation will fail if an existing model is incompatible.",
            "save_asset will fail if an existing metadata field is invalid.",
            "save_asset will fail validation if the metadata record already exists.",
            "save_asset will fail if the existing asset metadata is invalid.",
            "save_asset will fail if the existing asset metadata path already exists.",
            "save_asset will fail if the existing destination is invalid.",
            "save_asset metadata does not overwrite it.",
            "save_asset does not overwrite metadata.",
            "The destination metadata is not overwritten.",
            "save_asset never will fail if the destination already exists.",
            "The destination is not optimized, but save_asset replaces the file.",
            "Metadata is not replaced; the asset is overwritten.",
            "- Metadata does not replace parity\n- save_asset overwrites the destination",
        ):
            with self.subTest(advice=advice):
                self.assertEqual([], contract_errors(correct_contract + advice, "overwrite"))
                self.assertEqual([], overwrite_contract_errors(OVERWRITE_STATEMENT + "\n" + advice))

    def test_overwrite_contract_requires_the_versioned_statement(self):
        for text in ("", "<!-- contract:b3-overwrite -->", "b3 replaces existing destinations.",
                     OVERWRITE_STATEMENT.replace("1.0.0b3", "1.0.0b2"),
                     OVERWRITE_STATEMENT.replace("replaces", "preserves"),
                     OVERWRITE_STATEMENT.replace("file or directory", "file")):
            with self.subTest(text=text):
                self.assertEqual(["b3 overwrite contract statement missing"], overwrite_contract_errors(text))
        for text in (OVERWRITE_STATEMENT,
                     "> ✅ **VERIFIED (b3 source)** — `AIProgram.save_asset` in `coreai-core` 1.0.0b3 replaces an\n"
                     "> existing file or directory at the destination.\n",
                     OVERWRITE_STATEMENT.replace("AIProgram.save_asset", "_AIProgram.save_asset_")
                     .replace("coreai-core", "**coreai-core**")):
            with self.subTest(text=text):
                self.assertEqual([], overwrite_contract_errors(text))

    def test_overwrite_contract_cannot_be_supplied_by_fences_or_comments(self):
        for text in (f"<!-- {OVERWRITE_STATEMENT} -->",
                     f"<!--\n{OVERWRITE_STATEMENT}\n-->",
                     f"<!-- {OVERWRITE_STATEMENT}",
                     f"```text\n{OVERWRITE_STATEMENT}\n```",
                     f"> ~~~~text\n> {OVERWRITE_STATEMENT}\n> ~~~~",
                     f"<!-- contract:b3-overwrite -->\n```text\n{OVERWRITE_STATEMENT}\n```"):
            with self.subTest(text=text):
                self.assertEqual(["b3 overwrite contract statement missing"], overwrite_contract_errors(text))
        self.assertEqual([], overwrite_contract_errors("<!-- ``` -->\n" + OVERWRITE_STATEMENT))

    def test_overwrite_contract_rejects_contradictions_even_with_the_statement(self):
        for claim in (
            "save_asset does not overwrite it.",
            "save_asset will not replace an existing path.",
            "Existing outputs are not overwritten.",
            "save_asset will fail if the output path already exists.",
            "save_asset will fail if the bundle already exists.",
            "save_asset will fail if the target path already exists.",
            "If the destination already exists, save_asset will fail.",
            "The destination and its contents are not overwritten.",
            "> > The destination and its contents are not\n> > overwritten.",
            "The file and directory are not replaced.",
            "save_asset does not replace or overwrite the destination.",
            "save_asset doesn’t replace them.",
            "AIProgram.save_asset() cannot overwrite that.",
            "```python\n# save_asset will NOT overwrite\n```",
        ):
            with self.subTest(claim=claim):
                self.assertEqual(["b3 overwrite behavior incorrect"], contract_errors(claim, "overwrite"))
                self.assertEqual(["b3 overwrite behavior incorrect"],
                                 overwrite_contract_errors(OVERWRITE_STATEMENT + "\n" + claim))
        self.assertEqual(["b3 overwrite contract statement missing", "b3 overwrite behavior incorrect"],
                         overwrite_contract_errors("save_asset does not overwrite it."))

    def test_overwrite_guard_checks_all_predicate_forms(self):
        for predicate in ("overwrite", "overwrites", "overwrote", "overwritten", "overwriting",
                          "replace", "replaces", "replaced", "replacing"):
            with self.subTest(predicate=predicate):
                self.assertTrue(contract_errors(f"save_asset never {predicate} the destination", "overwrite"))
                self.assertEqual([], contract_errors(f"Metadata never {predicate} a parity gate", "overwrite"))

    def test_overwrite_claims_survive_formatting_and_saving_subject_modifiers(self):
        for claim in (
            OVERWRITE_STATEMENT.replace('replaces', 'does not replace'),
            'save_asset by default does not overwrite the destination.',
            'save_asset also does not overwrite the destination.',
            'save_asset, unlike b2, does not overwrite the destination.',
            'save_asset validates the path but does not overwrite the destination.',
            'save_asset validates the path and does not overwrite the destination.',
            '> ⚠️ **SILENT FAILURE** — the destination is not overwritten.',
            'Note: the destination is not overwritten.',
            '- The destination is not overwritten.',
            '1. The destination is not overwritten.',
            '| The destination is not overwritten |',
            'AIProgram.save_asset(out) does not overwrite the destination.',
            'prog.save_asset(out, rt.AIModelAssetMetadata()) does not overwrite the destination.',
            'prog.save_asset(Path("model_(copy).aimodel"), metadata=make_metadata(version())) does not overwrite the destination.',
            'prog.save_asset(out, description="text. A sentence with )") does not overwrite the destination.',
            'prog.save_asset(out,\n# Save the supplied metadata.\nmetadata) does not overwrite the destination.',
            'The destination is not overwritten, so delete it first.',
            'The destination is not overwritten so delete it first.',
            'The destination is not overwritten, so delete it by hand.',
            'The saved bundle is not overwritten.',
            '* Metadata is unchanged\n* The destination is not overwritten',
        ):
            with self.subTest(claim=claim):
                self.assertEqual(['b3 overwrite behavior incorrect'], contract_errors(claim, 'overwrite'))
                self.assertEqual(['b3 overwrite behavior incorrect'],
                                 overwrite_contract_errors(OVERWRITE_STATEMENT + '\n\n' + claim))
                affirmative = claim.replace('does not', 'does').replace('is not', 'is')
                self.assertEqual([], contract_errors(affirmative, 'overwrite'))

    def test_overwrite_pronouns_need_a_saving_antecedent(self):
        for subject in ('save_asset', 'AIProgram.save_asset', 'prog.save_asset(out)', 'The converter'):
            with self.subTest(subject=subject):
                prefix = subject + ' writes the bundle. '
                self.assertEqual(['b3 overwrite behavior incorrect'],
                                 contract_errors(prefix + 'It will not overwrite the destination.', 'overwrite'))
                self.assertEqual([], contract_errors(prefix + 'It will overwrite the destination.', 'overwrite'))
        for text in (
            'It will not overwrite the destination.',
            'mlx_lm.convert writes a bundle. It will not overwrite the destination.',
            'save_asset writes a bundle. mlx_lm.convert writes another. It will not overwrite the destination.',
            'save_asset writes a bundle.\n\nIt will not overwrite the destination.',
            'AIProgram.save_asset in coreai-core 1.0.0b2 preserves files. It will not overwrite the destination.',
        ):
            with self.subTest(text=text):
                self.assertEqual([], contract_errors(text, 'overwrite'))

    def test_overwrite_failure_reason_is_destination_existence(self):
        for claim in (
            'save_asset will fail when writing to an existing destination.',
            'save_asset will fail if something already exists at the destination.',
            'save_asset raises a FileExistsError.',
            'prog.save_asset(out) raises FileExistsError if the destination already exists.',
        ):
            with self.subTest(claim=claim):
                self.assertEqual(['b3 overwrite behavior incorrect'], contract_errors(claim, 'overwrite'))
                negated = claim.replace('will fail', 'will not fail').replace('raises', 'does not raise')
                self.assertEqual([], contract_errors(negated, 'overwrite'))
        for predicate in ('fails', 'will fail'):
            for reason in (
                'if the path lacks the .aimodel suffix, even when the destination already exists',
                'if the destination exists but is read-only',
                'if the destination exists and is read-only',
                'if the destination exists, but is read-only',
            ):
                with self.subTest(predicate=predicate, reason=reason):
                    self.assertEqual([], contract_errors(f'save_asset {predicate} {reason}', 'overwrite'))

    def test_passive_explanation_does_not_inherit_an_unrelated_agent(self):
        self.assertEqual([], contract_errors(
            'The destination is not overwritten by another_tool, so delete it first.', 'overwrite'))
        self.assertEqual([], contract_errors(
            'AIProgram.save_asset in coreai-core 1.0.0b2 does not overwrite the destination.', 'overwrite'))

    def test_html_delimiters_in_code_do_not_hide_affirmative_prose(self):
        for code in ('```python\nmarker = "<!--"\n```', '`<!--`', '``<!--``'):
            with self.subTest(code=code):
                self.assertEqual([], overwrite_contract_errors(code + '\n\n' + OVERWRITE_STATEMENT))
        self.assertEqual([], overwrite_contract_errors('<!--\n```\n-->\n\n' + OVERWRITE_STATEMENT))

    def test_overwrite_guard_checks_comments_inside_call_arguments(self):
        text = ('```python\nprog.save_asset(out,\n'
                '    # save_asset will NOT overwrite\n'
                '    rt.AIModelAssetMetadata())\n```')
        self.assertEqual(['b3 overwrite behavior incorrect'], contract_errors(text, 'overwrite'))

    def test_html_delimiters_in_code_do_not_expose_fenced_statements(self):
        for text in (
            '```text\n<!--\n```\n\n-->\n\n```\n' + OVERWRITE_STATEMENT + '\n```',
            '`<!--`\n\n```text\n-->\n\n' + OVERWRITE_STATEMENT + '\n```',
        ):
            with self.subTest(text=text):
                self.assertEqual(['b3 overwrite contract statement missing'], overwrite_contract_errors(text))

    def test_overwrite_claim_boundaries_and_filesystem_noun_phrases(self):
        cases = (
            ("save_asset will fail if the destination directory already exists", True),
            ("save_asset will fail when the destination file exists", True),
            ("save_asset will fail on the existing destination", True),
            ("Loading will fail if the source is missing, and save_asset will fail if the destination already exists", True),
            ("save_asset does not overwrite the asset metadata file", True),
            ("save_asset does not overwrite the asset metadata record", False),
            ("save_asset replaces an existing destination, whereas mlx_lm.convert will fail if the output path already exists", False),
            ("save_asset replaces an existing destination, and mlx_lm.convert will fail if the output path already exists", False),
            ("save_asset will fail validation, mlx_lm.convert will fail if the destination already exists", False),
            ("save_asset does not replace the output path", True),
            ("Quantization does not replace the output dtype", False),
            ("save_asset does not replace the target path", True),
            ("Quantization does not replace the target device", False),
            ("Targets cannot replace validation", False),
            ("Existing targets cannot be replaced", True),
            ("Paths are not replaced by tildes", False),
            ("The existing path is not replaced by save_asset", True),
            ("The destination is not replaced by another_tool", False),
            ("save_asset does not overwrite that metadata", False),
            ("save_asset does not overwrite metadata", False),
            ("save_asset does not overwrite that", True),
            ("save_asset does not overwrite this metadata", False),
            ("save_asset does not overwrite this", True),
            ("save_asset neither replaces nor overwrites the destination", True),
            ("save_asset does not replace nor overwrite the destination", True),
            ("save_asset replaces and overwrites the destination", False),
            ("The file and directory are not replaced", True),
            ("The destination and its contents are not overwritten", True),
            ("Metadata neither replaces nor overwrites a parity gate", False),
        )
        for text, rejected in cases:
            with self.subTest(text=text):
                expected = ["b3 overwrite behavior incorrect"] if rejected else []
                self.assertEqual(expected, contract_errors(text, "overwrite"))
                self.assertEqual(expected, overwrite_contract_errors(OVERWRITE_STATEMENT + "\n" + text))

    def test_destination_failure_forms_keep_their_subject_and_condition(self):
        for predicate in ("will fail", "fails", "raises FileExistsError", "errors out"):
            for text in (
                f"save_asset {predicate} if the destination already exists",
                f"If the destination already exists, save_asset {predicate}",
                f"save_asset {predicate} on the existing destination",
            ):
                with self.subTest(text=text):
                    self.assertEqual(["b3 overwrite behavior incorrect"], contract_errors(text, "overwrite"))
            for text in (
                f"save_asset {predicate} if the metadata record already exists",
                f"save_asset saves the destination, whereas mlx_lm.convert {predicate} if the destination already exists",
                f"mlx_lm.convert {predicate} if the destination already exists",
            ):
                with self.subTest(text=text):
                    self.assertEqual([], contract_errors(text, "overwrite"))
        for text in (
            "save_asset will not fail if the destination already exists",
            "save_asset never fails if the destination already exists",
            "save_asset does not raise FileExistsError if the destination already exists",
            "save_asset does not error out if the destination already exists",
        ):
            with self.subTest(text=text):
                self.assertEqual([], contract_errors(text, "overwrite"))

    def test_required_overwrite_statement_is_affirmative_prose(self):
        for text in (
            "    " + OVERWRITE_STATEMENT,
            "\t" + OVERWRITE_STATEMENT,
            ">     " + OVERWRITE_STATEMENT,
            "~~" + OVERWRITE_STATEMENT + "~~",
            "`" + OVERWRITE_STATEMENT + "`",
            "It is false that " + OVERWRITE_STATEMENT,
            "Do not assume that " + OVERWRITE_STATEMENT,
            OVERWRITE_STATEMENT.replace("replaces an existing", "replaces an\n\nexisting"),
            OVERWRITE_STATEMENT.replace("replaces an existing", "replaces an\n>\n> existing"),
            OVERWRITE_STATEMENT.replace("replaces", "~~replaces~~"),
        ):
            with self.subTest(text=text):
                self.assertEqual(["b3 overwrite contract statement missing"], overwrite_contract_errors(text))
        for text in (
            OVERWRITE_STATEMENT.replace("replaces an existing", "replaces an\nexisting"),
            "> > ✅ **VERIFIED (b3 source)** — " + OVERWRITE_STATEMENT.replace("replaces an existing", "replaces an\n> > existing"),
            OVERWRITE_STATEMENT + " Redundant deletion is unnecessary.",
            "A separate paragraph.\n\n" + OVERWRITE_STATEMENT,
        ):
            with self.subTest(text=text):
                self.assertEqual([], overwrite_contract_errors(text))

    def test_invalid_identifiers_fail_across_tokenizer_versions(self):
        for code in ("x = …", "x = €", "program.…()"):
            with self.subTest(code=code), self.assertRaises(ValueError):
                python_fences(f"```python\n{code}\n```")
        self.assertEqual([], self.calls('π = 1\n名前 = "…"\n# …\ndef incomplete():\n    ...'))
        self.assertEqual([], self.calls('return program\n# intentionally incomplete fragment'))

    def test_valid_historical_exemption(self):
        metadata = '<!-- coreai-example: {"id":"old", "historical":{"coreai-torch":"0.4.1","coreai-core":"1.0.0b2"}} -->\n'
        example = python_fences(metadata + '```python\np.optimize()\n```')[0]
        self.assertEqual("0.4.1", example.historical["coreai-torch"])
        self.assertTrue(optimizer_calls(example))  # caller explicitly applies exemption

    def test_fail_closed(self):
        for text in ('```python\nx = (\n```', '```python\nx=1',
                     '```python extra\nx=1\n```',
                     '> ```python\n> x=1\n```',
                     '<!-- coreai-example: {"id":"bad", "historical":{"coreai-torch":"0.4.3","coreai-core":"1.0.0b3"}} -->\n```python\np.optimize()\n```',
                     '<!-- coreai-example: {"id":"same"} -->\n```python\nx=1\n```\n<!-- coreai-example: {"id":"same"} -->\n```python\nx=2\n```',
                     '<!-- coreai-example: nope -->\n```python\nx=1\n```',
                     '<!-- coreai-example: {"id":"bad", "historical":{}} -->\n```python\nx=1\n```',
                     '<!-- coreai-example: {"id":"bad"} -->\ntext\n```python\nx=1\n```',
                     '<!-- coreai-example: {"id":"bad"} -->\n```text\nx=1\n```'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                python_fences(text)

    def test_long_parenthesis_chain_finishes_in_subprocess(self):
        script = ("from scripts.coreai_examples import python_fences,optimizer_calls; "
                  "e=python_fences('```python\\nprogram'+'()'*800+'.save_asset()\\n```')[0]; "
                  "assert not optimizer_calls(e)")
        subprocess.run([sys.executable, "-c", script], cwd=ROOT, check=True, timeout=5)

    def test_previous_guide_fixtures_trigger_guards(self):
        # Exact previous guide text, not invented near-matches. Every fixture must fail.
        fixtures = (
            ("state", "### 9.5 State requires `optimize()`"),
            ("state", "coreai_program.optimize()                              # REQUIRED for stateful models"),
            ("rewrite", "The 0.4.3 converter now constructs `AIProgram(module)`, whose context-manager exit performs the\npre-compilation rewrite before `to_coreai()` returns."),
            ("overwrite", "shutil.rmtree(out, ignore_errors=True)      # save_asset will NOT overwrite"),
            ("issue49", "`coreai-torch#49`, where square inputs hid an `optimize()` bug and unequal (17×23) inputs exposed it"),
        )
        for contract, fixture in fixtures:
            with self.subTest(fixture=fixture):
                self.assertTrue(contract_errors(fixture, contract))

    def test_correct_current_and_historical_contracts(self):
        for contract, text in (
            ("state", "State requires the automatic module rewrite."),
            ("rewrite", "Exit from `with module:` runs rewriting before `AIProgram(module)`."),
            ("overwrite", "b3 replaces existing destinations."),
            ("overwrite", "Note: b3 will overwrite the destination."),
            ("issue49", "apple/coreai-torch#49 closed 2026-10-02; historical 0.4.1 failure."),
        ):
            self.assertEqual([], contract_errors(text, contract))


if __name__ == "__main__":
    unittest.main()
