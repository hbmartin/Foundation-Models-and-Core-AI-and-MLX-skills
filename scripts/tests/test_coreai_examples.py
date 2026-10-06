import subprocess
import sys
import unittest
from pathlib import Path

from scripts.coreai_examples import contract_errors, optimizer_calls, python_fences

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

    def test_comments_and_strings(self):
        self.assertEqual([], self.calls('# program.optimize()\nx = "program.optimize()"'))

    def test_valid_historical_exemption(self):
        metadata = '<!-- coreai-example: {"id":"old", "historical":{"coreai-torch":"0.4.1","coreai-core":"1.0.0b2"}} -->\n'
        example = python_fences(metadata + '```python\np.optimize()\n```')[0]
        self.assertEqual("0.4.1", example.historical["coreai-torch"])
        self.assertTrue(optimizer_calls(example))  # caller explicitly applies exemption

    def test_fail_closed(self):
        for text in ('```python\nx = (\n```', '```python\nx=1',
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
            ("issue49", "`coreai-torch` issue **#49** (open"),
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
            ("issue49", "apple/coreai-torch#49 closed 2026-10-02; historical 0.4.1 failure."),
        ):
            self.assertEqual([], contract_errors(text, contract))


if __name__ == "__main__":
    unittest.main()
