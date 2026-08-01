"""Unit tests for scripts/verify-snippets.py.

Pure Python, no swiftc: the script's test-only --stub-compiler flag substitutes
a fixed result for every compile, which makes extraction, marker parsing,
wrapper synthesis, guess mode, xfail semantics, and --write-markers testable on
the Linux CI runner (same pattern as test_index_tooling.py).
"""

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(SCRIPTS_DIR, "verify-snippets.py")


def load_verifier():
    spec = importlib.util.spec_from_file_location("verify_snippets", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


VS = load_verifier()


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
    def test_missing_and_empty_guides_roots_fail_fast(self):
        with tempfile.TemporaryDirectory() as td:
            missing = run_script(["--guides", os.path.join(td, "missing"),
                                  "--stub-compiler", "pass"])
            self.assertNotEqual(missing.returncode, 0)
            self.assertIn("guides root does not exist", missing.stderr)
            empty = run_script(["--guides", td, "--stub-compiler", "pass"])
            self.assertNotEqual(empty.returncode, 0)
            self.assertIn("contains no Swift fences", empty.stderr)

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

    def test_heading_slug_uses_visible_link_text_and_canonical_punctuation(self):
        self.assertEqual(
            VS.slugify("[Visible *Text*](https://example.com) — setup?!"),
            "visible-text--setup",
        )


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
        self.assertEqual(code, 2)

    def test_illustrative_excludes_other_markers(self):
        row, code = self._one("illustrative compile:27")
        self.assertEqual(row["status"], "MARKER-ERROR")
        self.assertEqual(code, 2)

    def test_duplicate_marker_keys_are_rejected(self):
        for info in ("compile:26 compile:27", "illustrative illustrative",
                     "compile:27 wrap:body wrap:mixed", "xfail:26 xfail:27"):
            row, code = self._one(info)
            self.assertEqual(row["status"], "MARKER-ERROR", info)
            self.assertIn("duplicate marker", row["first_error"], info)
            self.assertEqual(code, 2, info)

    def test_prelude_excludes_compile_and_xfail(self):
        for info in ("prelude:ctx compile:27", "xfail:27 prelude:ctx"):
            row, code = self._one(info)
            self.assertEqual(row["status"], "MARKER-ERROR", info)
            self.assertEqual(code, 2, info)

    def test_illustrative_excludes_lang(self):
        row, code = self._one("illustrative lang:5")
        self.assertEqual(row["status"], "MARKER-ERROR")
        self.assertEqual(code, 2)

    def test_changed_with_empty_ref_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            write_guide(td, "g.md", "```swift compile:27\nlet a = 1\n```\n")
            r = run_script(["--guides", td, "--stub-compiler", "pass", "--changed="])
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("--changed requires a non-empty ref", r.stderr)

    def test_mainactor_isolation_marker_is_accepted(self):
        row, code = self._one("compile:27 isolation:mainactor")
        self.assertEqual(row["status"], "VERIFIED")
        self.assertEqual(code, 0)

    def test_empty_imports_and_prelude_values_are_rejected(self):
        self.assertEqual(self._one("compile:27 imports:")[0]["status"], "MARKER-ERROR")
        self.assertEqual(self._one("prelude:")[0]["status"], "MARKER-ERROR")

    def test_wrap_none_rejects_injected_imports(self):
        row, code = self._one("compile:27 wrap:none imports:Foundation")
        self.assertEqual(row["status"], "MARKER-ERROR")
        self.assertEqual(code, 2)

    def test_comment_only_compile_marker_is_rejected(self):
        row, code = self._one("compile:27", body="// documentation only\n")
        self.assertEqual(row["status"], "MARKER-ERROR")
        self.assertEqual(code, 2)

    def test_nested_block_comment_only_compile_marker_is_rejected(self):
        body = "/* outer /* nested */ still outer */\n"
        row, code = self._one("compile:27", body=body)
        self.assertEqual(row["status"], "MARKER-ERROR")
        self.assertEqual(code, 2)

    def test_custom_condition_requires_declared_define(self):
        body = "#if FEATURE\nlet a = 1\n#endif\n"
        row, _ = self._one("compile:27", body=body)
        self.assertEqual(row["status"], "MARKER-ERROR")
        row, code = self._one("compile:27 defines:FEATURE", body=body)
        self.assertEqual(row["status"], "VERIFIED")
        self.assertEqual(code, 0)

    def test_defined_condition_cannot_compile_the_entire_body_out(self):
        body = "#if !FEATURE\nlet a = 1\n#endif\n"
        row, code = self._one("compile:27 defines:FEATURE", body=body)
        self.assertEqual(row["status"], "MARKER-ERROR")
        self.assertIn("entirely inactive", row["first_error"])
        self.assertEqual(code, 2)

    def test_illustrative_never_invokes_compiler(self):
        # stub 'fail' would make any compile FAIL; illustrative must stay green.
        with tempfile.TemporaryDirectory() as td:
            write_guide(td, "g.md", "```swift illustrative\ntotal nonsense !!\n```\n")
            r = run_script(["--guides", td, "--stub-compiler", "fail:boom"])
            self.assertEqual(tsv_rows(r.stdout)[0]["status"], "ILLUSTRATIVE")
            self.assertEqual(r.returncode, 0)

    def test_compile26_with_coreai_import_rejected(self):
        row, code = self._one("compile:26,27", body="import CoreAI\nlet a = 1\n")
        self.assertEqual(row["status"], "MARKER-ERROR")
        self.assertEqual(code, 2)

    def test_prelude_reported_not_compiled(self):
        with tempfile.TemporaryDirectory() as td:
            write_guide(td, "g.md", "```swift prelude:foo\nuses(guideLocal)\n```\n")
            r = run_script(["--guides", td, "--stub-compiler", "fail:boom"])
            self.assertEqual(tsv_rows(r.stdout)[0]["status"], "PRELUDE-NEEDED")
            self.assertEqual(r.returncode, 0)


class SynthesisTests(unittest.TestCase):
    def test_midsnippet_import_hoisted_and_deduped(self):
        mods, imps, rest, _ = VS.hoist_imports(
            ["let a = 1", "import FoundationModels", "import FoundationModels", "let b = 2"])
        self.assertEqual(mods, ["FoundationModels"])
        self.assertEqual(imps, ["import FoundationModels"])
        self.assertEqual(rest, ["let a = 1", "let b = 2"])

    def test_expression_snippet_gets_body_wrap_and_decl_snippet_stays_top(self):
        self.assertEqual(VS.choose_wrap(["session.respond()"]), "body")
        self.assertEqual(VS.choose_wrap(["struct S {}"]), "top")

    def test_linemap_maps_generated_lines_back_to_guide_lines(self):
        fence = VS.Fence("g.md", 10, 0, "swift", "",
                         ["let a = 1", "import Foo", "let b = 2"], "a")
        source, linemap, _ = VS.synthesize(fence, [], "body")
        lines = source.splitlines()
        # import hoisted to line 0 (synthesized position), func wrapper next
        self.assertEqual(lines[0], "import Foo")
        self.assertIsNone(linemap[0])
        self.assertIsNone(linemap[1])  # func __verify_snippet...
        self.assertEqual(linemap[2], 11)  # 'let a = 1' was guide line 11
        self.assertEqual(linemap[3], 13)  # 'let b = 2' was guide line 13

    def test_mixed_wrap_keeps_macro_type_top_level_and_wraps_usage(self):
        fence = VS.Fence("g.md", 20, 0, "swift", "", [
            "import FoundationModels",
            "@Generable",
            "struct Answer {",
            "    var value: String",
            "}",
            "",
            "let session = LanguageModelSession()",
            "let answer = try await session.respond(to: \"Hi\", generating: Answer.self)",
        ], "mixed")
        source, linemap, _ = VS.synthesize(fence, [], "mixed")
        self.assertLess(source.index("struct Answer"), source.index("func __verify_snippet"))
        self.assertGreater(source.index("let session"), source.index("func __verify_snippet"))
        self.assertEqual(linemap[source.splitlines().index("let session = LanguageModelSession()")], 27)

    def test_mixed_wrap_does_not_add_empty_function_after_declarations_only(self):
        fence = VS.Fence("g.md", 1, 0, "swift", "", [
            "@main struct App { static func main() {} }",
        ], "main")
        source, _, _ = VS.synthesize(fence, [], "mixed")
        self.assertNotIn("__verify_snippet", source)

    def test_mixed_wrap_ignores_braces_inside_strings(self):
        fence = VS.Fence("g.md", 1, 0, "swift", "", [
            "struct Example {",
            "    let text = \"{\"",
            "}",
            "let example = Example()",
            "print(example.text)",
        ], "mixed")
        source, _, _ = VS.synthesize(fence, [], "mixed")
        self.assertLess(source.index("struct Example"), source.index("func __verify_snippet"))
        self.assertGreater(source.index("let example"), source.index("func __verify_snippet"))

    def test_wrap_none_omits_parse_as_library(self):
        fence = VS.Fence("g.md", 1, 0, "swift", "", ["print(\"hello\")"], "")
        opts = mock.Mock(cache_root="/tmp/cache", timeout=1, stub_compiler=None)
        with mock.patch.object(
                VS, "typecheck", return_value=VS.CompileResult("pass")) as checker:
            VS.compile_variants(
                fence, VS.Markers(wrap="none"), [], object(), opts, False)
        self.assertFalse(checker.call_args.kwargs["parse_as_library"])

    def test_stub_and_elided_autodetected_but_range_operator_is_not(self):
        stub = VS.Fence("g.md", 1, 0, "swift", "", ["var x: Int { get }"], "")
        self.assertIn("stub", VS.autodetect(stub))
        elided = VS.Fence("g.md", 1, 0, "swift", "", ["let a = f(", "...", ")"], "")
        self.assertIn("elided", VS.autodetect(elided))
        ranged = VS.Fence("g.md", 1, 0, "swift", "", ["for i in 0...10 { print(i) }"], "")
        self.assertNotIn("elided", VS.autodetect(ranged))

    def test_deployment_targets_separate_sdk_from_minimum_os(self):
        self.assertEqual(VS.TARGETS["27-on-26"].sdk_generation, "27")
        self.assertEqual(VS.TARGETS["27-on-26"].deployment_version, "26.0")
        self.assertEqual(VS.TARGETS["sim27-on-26"].column, "vsim27on26")


class ToolchainDiscoveryTests(unittest.TestCase):
    def test_command_failure_becomes_clear_system_exit(self):
        failure = subprocess.CalledProcessError(
            1, ["xcrun"], stderr="requested SDK is not installed"
        )
        with mock.patch.object(VS.os.path, "isdir", return_value=True), \
                mock.patch.object(VS.subprocess, "run", side_effect=failure):
            with self.assertRaisesRegex(
                SystemExit,
                "toolchain discovery for target 27 failed.*requested SDK is not installed",
            ):
                VS.discover_toolchain("27")

    def test_missing_executable_becomes_clear_system_exit(self):
        with mock.patch.object(VS.os.path, "isdir", return_value=True), \
                mock.patch.object(
                    VS.subprocess, "run", side_effect=FileNotFoundError("missing xcrun")
                ):
            with self.assertRaisesRegex(
                SystemExit,
                "toolchain discovery for target 27 failed.*missing xcrun",
            ):
                VS.discover_toolchain("27")


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

    def test_simulator_fallback_retries_mainactor_isolation(self):
        fence = VS.Fence("g.md", 1, 0, "swift", "", ["UIKitExample()"], "")
        toolchains = {"27": object(), "sim27": object()}
        opts = mock.Mock(guess=True, guess_target="27")
        with mock.patch.object(VS, "compile_variants", side_effect=[
                ("fail", "body", VS.CompileResult("fail", first_error="no such module 'UIKit'")),
                ("fail", "body", VS.CompileResult(
                    "fail", first_error="call to main actor-isolated initializer")),
                ("pass", "body", VS.CompileResult("pass")),
        ]):
            row = VS.verify_fence(fence, toolchains, opts)
        self.assertEqual(row["status"], "UNCLASSIFIED-PASS")
        self.assertEqual(row["vsim27"], "pass")
        self.assertEqual(row["_guess_isolation"], "mainactor")

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

    def test_mixed_compile_and_xfail_is_migration_proven(self):
        fence = VS.Fence("g.md", 1, 0, "swift", "xfail:26 compile:27",
                         ["let a = 1"], "")
        toolchains = {name: object() for name in ("26", "27")}
        opts = mock.Mock()
        with mock.patch.object(VS, "compile_variants", side_effect=[
                ("pass", "top", VS.CompileResult("pass")),
                ("xfail-pass", "top", VS.CompileResult("fail")),
        ]):
            row = VS.verify_fence(fence, toolchains, opts)
        self.assertEqual(row["status"], "MIGRATION-PROVEN")
        self.assertEqual(row["v27"], "pass")
        self.assertEqual(row["v26"], "xfail-pass")

    def test_sdk_argument_is_additive_not_a_filter(self):
        with tempfile.TemporaryDirectory() as td:
            write_guide(td, "g.md", "```swift compile:26\nlet a = 1\n```\n")
            r = run_script(["--guides", td, "--stub-compiler", "pass", "--sdk", "27"])
            row = tsv_rows(r.stdout)[0]
            self.assertEqual(row["status"], "VERIFIED")
            self.assertEqual(row["v26"], "pass")
            self.assertEqual(row["v27"], "-")


class ChangedFilesTests(unittest.TestCase):
    def git(self, repo, *args):
        return subprocess.run(["git", "-C", repo, *args], check=True,
                              capture_output=True, text=True)

    def make_repo(self):
        td = tempfile.TemporaryDirectory()
        repo = td.name
        self.git(repo, "init", "-q")
        self.git(repo, "config", "user.email", "tests@example.com")
        self.git(repo, "config", "user.name", "Verifier Tests")
        write_guide(repo, "guides/old name.md", "```swift\nlet old = 1\n```\n")
        write_guide(repo, "guides/bad.md", "```swift\nlet broken = 1\n")
        self.git(repo, "add", "guides")
        self.git(repo, "commit", "-qm", "base")
        self.git(repo, "branch", "base")
        self.git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
        self.git(repo, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
        os.makedirs(os.path.join(repo, "subdir"))
        return td, repo

    def test_changed_handles_rename_spaces_subdirectory_and_filters_parse_errors(self):
        td, repo = self.make_repo()
        with td:
            self.git(repo, "mv", "guides/old name.md", "guides/new name.md")
            self.git(repo, "commit", "-qam", "rename")
            r = run_script(["--guides", "../guides", "--stub-compiler", "pass",
                            "--changed", "base"], cwd=os.path.join(repo, "subdir"))
            self.assertEqual(r.returncode, 0, r.stderr)
            rows = tsv_rows(r.stdout)
            self.assertEqual([row["file"] for row in rows], ["new name.md"])
            self.assertNotIn("PARSE-ERROR", r.stdout)

    def test_changed_detects_untracked_file_and_bare_mode_uses_remote_head(self):
        td, repo = self.make_repo()
        with td:
            write_guide(repo, "guides/new file.md", "```swift\nlet newValue = 1\n```\n")
            r = run_script(["--guides", "guides", "--stub-compiler", "pass",
                            "--changed"], cwd=repo)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual([row["file"] for row in tsv_rows(r.stdout)], ["new file.md"])

    def test_changed_invalid_ref_fails_instead_of_reporting_zero(self):
        td, repo = self.make_repo()
        with td:
            r = run_script(["--guides", "guides", "--stub-compiler", "pass",
                            "--changed", "not-a-ref"], cwd=repo)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("rev-parse", r.stderr)


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
        base = {"flags": set()}
        self.assertEqual(VS.triage_marker_for_row(
            dict(base, first_error="cannot find 'session' in scope")),
            "prelude:guide-context")
        self.assertEqual(VS.triage_marker_for_row(
            dict(base, first_error="no such module 'MLXLMCommon'")),
            "prelude:external-module")
        self.assertEqual(VS.triage_marker_for_row(
            dict(base, first_error="expected '{' in struct")),
            "illustrative")
        self.assertIsNone(VS.triage_marker_for_row(
            dict(base, first_error="cannot assign value of type A to type B")))
        self.assertIsNone(VS.triage_marker_for_row(
            dict(base, first_error="type A does not conform to protocol B")))
        self.assertIsNone(VS.triage_marker_for_row(
            dict(base, first_error="value of type A has no member b")))
        self.assertIsNone(VS.triage_marker_for_row(
            {"flags": {"wrongness"}, "first_error": "cannot find 'user' in scope"}))
        self.assertIsNone(VS.triage_marker_for_row(
            dict(base, first_error="missing argument for parameter 'label' in call")))
        self.assertEqual(VS.triage_marker_for_row(
            dict(base, first_error="missing return in global function 'f'")),
            "illustrative")
        self.assertIsNone(VS.triage_marker_for_row(
            dict(base, first_error="cannot find 'Foo' in this odd phrasing")))


class ReportTests(unittest.TestCase):
    def test_out_dir_writes_tsv_and_report(self):
        with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as out:
            write_guide(td, "g.md", "```swift compile:27\nlet a = 1\n```\n")
            r = run_script(["--guides", td, "--stub-compiler", "pass", "--out", out])
            self.assertEqual(r.returncode, 0)
            results_path = os.path.join(out, "results.tsv")
            self.assertTrue(os.path.exists(results_path))
            with open(results_path, encoding="utf-8") as handle:
                result_lines = handle.read().splitlines()
            self.assertTrue(all(not line.endswith((" ", "\t")) for line in result_lines))
            self.assertIn("v27on26", result_lines[0])
            self.assertIn("vsim27on26", result_lines[0])
            with open(os.path.join(out, "report.md"), encoding="utf-8") as handle:
                report = handle.read()
            self.assertIn("Per-guide rollup", report)
            self.assertIn("UNCLASSIFIED backlog", report)
            self.assertNotIn("jobs=", report)

    def test_output_is_deterministic_across_job_counts(self):
        with tempfile.TemporaryDirectory() as td, \
                tempfile.TemporaryDirectory() as out1, \
                tempfile.TemporaryDirectory() as out8:
            write_guide(td, "b.md", "```swift compile:27\nlet b = 2\n```\n")
            write_guide(td, "a.md", "```swift compile:27\nlet a = 1\n```\n")
            for jobs, out in (("1", out1), ("8", out8)):
                result = run_script(["--guides", td, "--stub-compiler", "pass",
                                     "--jobs", jobs, "--out", out])
                self.assertEqual(result.returncode, 0, result.stderr)
            for filename in ("results.tsv", "report.md"):
                with open(os.path.join(out1, filename), "rb") as first, \
                        open(os.path.join(out8, filename), "rb") as second:
                    self.assertEqual(first.read(), second.read())


if __name__ == "__main__":
    unittest.main()
