import subprocess
import sys
import unittest
from pathlib import Path

from scripts.coreai_examples import contract_errors, optimizer_calls, python_fences, section
from scripts.mdlinks import iter_lines

ROOT = Path(__file__).resolve().parents[2]


class CoreAIExampleTests(unittest.TestCase):
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
        ):
            with self.subTest(text=text):
                self.assertTrue(contract_errors(text, "overwrite"))
        for text in ("Note: b3 will overwrite the destination", "It does not merge. It overwrites.",
                     "It will fail during conversion. The asset already exists.",
                     "- Do not optimize the program\n- save_asset overwrites an existing destination",
                     "1. Do not optimize the program\n2. save_asset overwrites an existing destination",
                     "The program is not optimized; the destination is overwritten"):
            with self.subTest(text=text):
                self.assertEqual([], contract_errors(text, "overwrite"))

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
