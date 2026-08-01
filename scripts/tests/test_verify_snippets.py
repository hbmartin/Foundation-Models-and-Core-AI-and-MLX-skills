"""Unit tests for scripts/verify-snippets.py.

Pure Python, no swiftc: the script's test-only --stub-compiler flag substitutes
a fixed result for every compile, which makes extraction, marker parsing,
wrapper synthesis, guess mode, xfail semantics, and --write-markers testable on
the Linux CI runner (same pattern as test_index_tooling.py).
"""

import os
import subprocess
import sys
import tempfile
import unittest

SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(SCRIPTS_DIR, "verify-snippets.py")


def run_script(args, cwd=None):
    return subprocess.run([sys.executable, SCRIPT] + args,
                          capture_output=True, text=True, cwd=cwd)


def write_guide(root, rel, text):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def tsv_rows(stdout):
    lines = [l for l in stdout.splitlines() if l]
    header = lines[0].split("\t")
    return [dict(zip(header, l.split("\t"))) for l in lines[1:]]


class ExtractionTests(unittest.TestCase):
    def test_column0_and_indented_fences_extracted(self):
        with tempfile.TemporaryDirectory() as td:
            write_guide(td, "g.md", (
                "# T\n\n```swift\nlet a = 1\n```\n\n"
                "1. item\n\n   ```swift\n   let b = 2\n   ```\n"))
            r = run_script(["--guides", td, "--stub-compiler", "pass"])
            rows = tsv_rows(r.stdout)
            self.assertEqual(len(rows), 2)
            # indented fence body had its indent stripped -> same wrap decision
            self.assertEqual({row["line"] for row in rows}, {"3", "9"})

    def test_unterminated_fence_reports_parse_error_and_exit_2(self):
        with tempfile.TemporaryDirectory() as td:
            write_guide(td, "g.md", "```swift\nlet a = 1\n")
            r = run_script(["--guides", td, "--stub-compiler", "pass"])
            self.assertEqual(r.returncode, 2)
            self.assertIn("PARSE-ERROR", r.stdout)

    def test_generated_pages_skipped(self):
        with tempfile.TemporaryDirectory() as td:
            write_guide(td, "SILENT-FAILURES.md", "```swift\nlet a = 1\n```\n")
            write_guide(td, "g.md", "```swift\nlet a = 1\n```\n")
            r = run_script(["--guides", td, "--stub-compiler", "pass"])
            self.assertEqual(len(tsv_rows(r.stdout)), 1)

    def test_heading_inside_code_fence_not_an_anchor(self):
        with tempfile.TemporaryDirectory() as td:
            write_guide(td, "g.md", (
                "# Real Heading\n\n```bash\n# not a heading\n```\n\n"
                "```swift\nlet a = 1\n```\n"))
            rows = tsv_rows(run_script(["--guides", td, "--stub-compiler", "pass"]).stdout)
            self.assertEqual(rows[0]["anchor"], "real-heading")

    def test_duplicate_heading_slugs_deduplicated(self):
        with tempfile.TemporaryDirectory() as td:
            write_guide(td, "g.md", (
                "# Setup\n\n## Setup\n\n```swift\nlet a = 1\n```\n"))
            rows = tsv_rows(run_script(["--guides", td, "--stub-compiler", "pass"]).stdout)
            self.assertEqual(rows[0]["anchor"], "setup-1")


class MarkerTests(unittest.TestCase):
    def _one(self, info, body="let a = 1\n"):
        with tempfile.TemporaryDirectory() as td:
            write_guide(td, "g.md", f"```swift {info}\n{body}```\n")
            r = run_script(["--guides", td, "--stub-compiler", "pass"])
            return tsv_rows(r.stdout)[0], r.returncode

    def test_unknown_marker_key_rejected(self):
        row, code = self._one("compyle:27")
        self.assertEqual(row["status"], "MARKER-ERROR")
        self.assertEqual(code, 2)

    def test_target_in_both_compile_and_xfail_rejected(self):
        row, code = self._one("compile:27 xfail:27")
        self.assertEqual(row["status"], "MARKER-ERROR")

    def test_illustrative_excludes_other_markers(self):
        row, _ = self._one("illustrative compile:27")
        self.assertEqual(row["status"], "MARKER-ERROR")

    def test_mainactor_isolation_marker_is_accepted(self):
        row, code = self._one("compile:27 isolation:mainactor")
        self.assertEqual(row["status"], "VERIFIED")
        self.assertEqual(code, 0)

    def test_illustrative_never_invokes_compiler(self):
        # stub 'fail' would make any compile FAIL; illustrative must stay green.
        with tempfile.TemporaryDirectory() as td:
            write_guide(td, "g.md", "```swift illustrative\ntotal nonsense !!\n```\n")
            r = run_script(["--guides", td, "--stub-compiler", "fail:boom"])
            self.assertEqual(tsv_rows(r.stdout)[0]["status"], "ILLUSTRATIVE")
            self.assertEqual(r.returncode, 0)

    def test_compile26_with_coreai_import_rejected(self):
        row, _ = self._one("compile:26,27", body="import CoreAI\nlet a = 1\n")
        self.assertEqual(row["status"], "MARKER-ERROR")

    def test_prelude_reported_not_compiled(self):
        with tempfile.TemporaryDirectory() as td:
            write_guide(td, "g.md", "```swift prelude:foo\nuses(guideLocal)\n```\n")
            r = run_script(["--guides", td, "--stub-compiler", "fail:boom"])
            self.assertEqual(tsv_rows(r.stdout)[0]["status"], "PRELUDE-NEEDED")
            self.assertEqual(r.returncode, 0)


class SynthesisTests(unittest.TestCase):
    def test_midsnippet_import_hoisted_and_deduped(self):
        sys.path.insert(0, SCRIPTS_DIR)
        vs = __import__("importlib").machinery.SourceFileLoader(
            "verify_snippets", SCRIPT).load_module()
        mods, imps, rest, _ = vs.hoist_imports(
            ["let a = 1", "import FoundationModels", "import FoundationModels", "let b = 2"])
        self.assertEqual(mods, ["FoundationModels"])
        self.assertEqual(imps, ["import FoundationModels"])
        self.assertEqual(rest, ["let a = 1", "let b = 2"])

    def test_expression_snippet_gets_body_wrap_and_decl_snippet_stays_top(self):
        sys.path.insert(0, SCRIPTS_DIR)
        vs = __import__("importlib").machinery.SourceFileLoader(
            "verify_snippets", SCRIPT).load_module()
        self.assertEqual(vs.choose_wrap(["session.respond()"]), "body")
        self.assertEqual(vs.choose_wrap(["struct S {}"]), "top")

    def test_linemap_maps_generated_lines_back_to_guide_lines(self):
        sys.path.insert(0, SCRIPTS_DIR)
        vs = __import__("importlib").machinery.SourceFileLoader(
            "verify_snippets", SCRIPT).load_module()
        fence = vs.Fence("g.md", 10, 0, "swift", "",
                         ["let a = 1", "import Foo", "let b = 2"], "a")
        source, linemap, _ = vs.synthesize(fence, [], "body")
        lines = source.splitlines()
        # import hoisted to line 0 (synthesized position), func wrapper next
        self.assertEqual(lines[0], "import Foo")
        self.assertIsNone(linemap[0])
        self.assertIsNone(linemap[1])  # func __verify_snippet...
        self.assertEqual(linemap[2], 11)  # 'let a = 1' was guide line 11
        self.assertEqual(linemap[3], 13)  # 'let b = 2' was guide line 13

    def test_mixed_wrap_keeps_macro_type_top_level_and_wraps_usage(self):
        sys.path.insert(0, SCRIPTS_DIR)
        vs = __import__("importlib").machinery.SourceFileLoader(
            "verify_snippets_mixed", SCRIPT).load_module()
        fence = vs.Fence("g.md", 20, 0, "swift", "", [
            "import FoundationModels",
            "@Generable",
            "struct Answer {",
            "    var value: String",
            "}",
            "",
            "let session = LanguageModelSession()",
            "let answer = try await session.respond(to: \"Hi\", generating: Answer.self)",
        ], "mixed")
        source, linemap, _ = vs.synthesize(fence, [], "mixed")
        self.assertLess(source.index("struct Answer"), source.index("func __verify_snippet"))
        self.assertGreater(source.index("let session"), source.index("func __verify_snippet"))
        self.assertEqual(linemap[source.splitlines().index("let session = LanguageModelSession()")], 27)

    def test_mixed_wrap_does_not_add_empty_function_after_declarations_only(self):
        sys.path.insert(0, SCRIPTS_DIR)
        vs = __import__("importlib").machinery.SourceFileLoader(
            "verify_snippets_decls_only", SCRIPT).load_module()
        fence = vs.Fence("g.md", 1, 0, "swift", "", [
            "@main struct App { static func main() {} }",
        ], "main")
        source, _, _ = vs.synthesize(fence, [], "mixed")
        self.assertNotIn("__verify_snippet", source)

    def test_stub_and_elided_autodetected_but_range_operator_is_not(self):
        sys.path.insert(0, SCRIPTS_DIR)
        vs = __import__("importlib").machinery.SourceFileLoader(
            "verify_snippets", SCRIPT).load_module()
        stub = vs.Fence("g.md", 1, 0, "swift", "", ["var x: Int { get }"], "")
        self.assertIn("stub", vs.autodetect(stub))
        elided = vs.Fence("g.md", 1, 0, "swift", "", ["let a = f(", "...", ")"], "")
        self.assertIn("elided", vs.autodetect(elided))
        ranged = vs.Fence("g.md", 1, 0, "swift", "", ["for i in 0...10 { print(i) }"], "")
        self.assertNotIn("elided", vs.autodetect(ranged))


class GuessAndXfailTests(unittest.TestCase):
    def test_guess_pass_and_fail_statuses(self):
        with tempfile.TemporaryDirectory() as td:
            write_guide(td, "g.md", "```swift\nlet a = 1\n```\n")
            r = run_script(["--guides", td, "--stub-compiler", "pass", "--guess"])
            self.assertEqual(tsv_rows(r.stdout)[0]["status"], "UNCLASSIFIED-PASS")
            r = run_script(["--guides", td, "--stub-compiler", "fail:no such thing", "--guess"])
            row = tsv_rows(r.stdout)[0]
            self.assertEqual(row["status"], "UNCLASSIFIED-FAIL")
            self.assertEqual(r.returncode, 0)  # backlog, not failure

    def test_unmarked_without_guess_is_unclassified_and_uncompiled(self):
        with tempfile.TemporaryDirectory() as td:
            write_guide(td, "g.md", "```swift\nlet a = 1\n```\n")
            r = run_script(["--guides", td, "--stub-compiler", "fail:boom"])
            self.assertEqual(tsv_rows(r.stdout)[0]["status"], "UNCLASSIFIED")
            self.assertEqual(r.returncode, 0)

    def test_xfail_semantics(self):
        with tempfile.TemporaryDirectory() as td:
            write_guide(td, "g.md", "```swift xfail:27\nPrivateThing()\n```\n")
            r = run_script(["--guides", td, "--stub-compiler", "fail:cannot find"])
            self.assertEqual(tsv_rows(r.stdout)[0]["status"], "XFAIL-PROVEN")
            self.assertEqual(r.returncode, 0)
            r = run_script(["--guides", td, "--stub-compiler", "pass"])
            self.assertEqual(tsv_rows(r.stdout)[0]["status"], "XFAIL-ERR")
            self.assertEqual(r.returncode, 1)

    def test_compile_marker_failure_exits_1_with_flattened_error(self):
        with tempfile.TemporaryDirectory() as td:
            write_guide(td, "g.md", "```swift compile:27\nlet a = 1\n```\n")
            r = run_script(["--guides", td, "--stub-compiler", "fail:multi\tline\terror"])
            row = tsv_rows(r.stdout)[0]
            self.assertEqual(row["status"], "FAILED")
            self.assertNotIn("\t", row["first_error"])
            self.assertEqual(r.returncode, 1)


class WriteMarkersTests(unittest.TestCase):
    def _fixture(self, td):
        write_guide(td, "g.md", (
            "# H\n\n```swift\nlet a = 1\n```\n\n"
            "```swift\nvar x: Int { get }\n```\n"))

    def test_write_markers_edits_only_info_strings_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            self._fixture(td)
            r = run_script(["--guides", td, "--stub-compiler", "pass",
                            "--guess", "--write-markers"])
            self.assertEqual(r.returncode, 0, r.stderr)
            with open(os.path.join(td, "g.md")) as handle:
                text = handle.read()
            self.assertIn("```swift compile:27\n", text)
            self.assertIn("```swift illustrative\n", text)
            self.assertIn("let a = 1", text)
            self.assertIn("var x: Int { get }", text)
            # Idempotent: second run has nothing unmarked to write.
            before = text
            run_script(["--guides", td, "--stub-compiler", "pass",
                        "--guess", "--write-markers"])
            with open(os.path.join(td, "g.md")) as handle:
                self.assertEqual(handle.read(), before)

    def test_write_markers_requires_guess(self):
        with tempfile.TemporaryDirectory() as td:
            self._fixture(td)
            r = run_script(["--guides", td, "--stub-compiler", "pass", "--write-markers"])
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("requires --guess", r.stderr)

    def test_marked_fences_reverify_after_write(self):
        with tempfile.TemporaryDirectory() as td:
            self._fixture(td)
            run_script(["--guides", td, "--stub-compiler", "pass",
                        "--guess", "--write-markers"])
            r = run_script(["--guides", td, "--stub-compiler", "pass"])
            statuses = sorted(row["status"] for row in tsv_rows(r.stdout))
            self.assertEqual(statuses, ["ILLUSTRATIVE", "VERIFIED"])

    def test_triage_markers_classify_context_and_syntax_but_not_type_errors(self):
        sys.path.insert(0, SCRIPTS_DIR)
        vs = __import__("importlib").machinery.SourceFileLoader(
            "verify_snippets_triage", SCRIPT).load_module()
        base = {"flags": set()}
        self.assertEqual(vs.triage_marker_for_row(
            dict(base, first_error="cannot find 'session' in scope")),
            "prelude:guide-context")
        self.assertEqual(vs.triage_marker_for_row(
            dict(base, first_error="no such module 'MLXLMCommon'")),
            "prelude:external-module")
        self.assertEqual(vs.triage_marker_for_row(
            dict(base, first_error="expected '{' in struct")),
            "illustrative")
        self.assertIsNone(vs.triage_marker_for_row(
            dict(base, first_error="cannot assign value of type A to type B")))
        self.assertIsNone(vs.triage_marker_for_row(
            {"flags": {"wrongness"}, "first_error": "cannot find 'user' in scope"}))


class ReportTests(unittest.TestCase):
    def test_out_dir_writes_tsv_and_report(self):
        with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as out:
            write_guide(td, "g.md", "```swift compile:27\nlet a = 1\n```\n")
            r = run_script(["--guides", td, "--stub-compiler", "pass", "--out", out])
            self.assertEqual(r.returncode, 0)
            results_path = os.path.join(out, "results.tsv")
            self.assertTrue(os.path.exists(results_path))
            with open(results_path) as handle:
                result_lines = handle.read().splitlines()
            self.assertTrue(all(not line.endswith((" ", "\t")) for line in result_lines))
            with open(os.path.join(out, "report.md")) as handle:
                report = handle.read()
            self.assertIn("Per-guide rollup", report)
            self.assertIn("UNCLASSIFIED backlog", report)


if __name__ == "__main__":
    unittest.main()
