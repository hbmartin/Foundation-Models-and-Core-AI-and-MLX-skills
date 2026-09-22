import ast
import argparse
import json
import os
import re
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path
from types import SimpleNamespace


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from scripts import mdlinks, mdslug, mkdocs_hooks


def flatten_nav_paths(items):
    paths = []
    for item in items:
        value = next(iter(item.values()))
        if isinstance(value, str):
            paths.append(value)
        else:
            paths.extend(flatten_nav_paths(value))
    return paths


class FakeConfig(dict):
    def __init__(self, *args, config_file_path, **kwargs):
        super().__init__(*args, **kwargs)
        self.config_file_path = config_file_path
        self.mdx_configs = {"toc": {}}


class MkDocsHookTests(unittest.TestCase):
    def test_navigation_covers_the_corpus_once(self):
        docs_dir = REPOSITORY_ROOT / "guides"
        navigation = mkdocs_hooks.build_navigation(docs_dir)
        paths = flatten_nav_paths(navigation)
        source_paths = sorted(
            path.relative_to(docs_dir).as_posix() for path in docs_dir.rglob("*.md")
        )

        self.assertEqual(82, len(paths))
        self.assertEqual(source_paths, sorted(paths))
        self.assertEqual(len(paths), len(set(paths)))
        self.assertEqual("Overview", next(iter(navigation[0])))
        self.assertEqual("Parts", next(iter(navigation[1])))
        self.assertEqual("Deployment workflows", next(iter(navigation[2])))
        self.assertEqual("Cross-cutting indexes", next(iter(navigation[3])))
        self.assertEqual(1, paths.count("workflows/README.md"))
        self.assertEqual(1, paths.count("workflows/remote-training-to-ios.md"))

    def test_navigation_titles_strip_inline_code(self):
        navigation = mkdocs_hooks.build_navigation(REPOSITORY_ROOT / "guides")
        titles = []

        def collect(items):
            for item in items:
                title, value = next(iter(item.items()))
                titles.append(title)
                if isinstance(value, list):
                    collect(value)

        collect(navigation)
        self.assertIn("The Tool protocol, calling modes, and the required-mode loop", titles)
        self.assertIn(
            "Remote GPU training to an iOS app: hosted CUDA, MLX, and Core AI",
            titles,
        )
        self.assertNotIn("The `Tool` protocol, calling modes, and the required-mode loop", titles)

    def test_navigation_uses_every_shared_site_only_prefix(self):
        with tempfile.TemporaryDirectory() as directory:
            docs = Path(directory)
            (docs / "README.md").write_text("# Overview\n", encoding="utf-8")
            (docs / "API-INDEX.md").write_text("# API index\n", encoding="utf-8")
            (docs / "SILENT-FAILURES.md").write_text("# Failures\n", encoding="utf-8")
            part = docs / "part-01-test"
            part.mkdir()
            (part / "README.md").write_text("# Part one\n", encoding="utf-8")
            for name, title in (("workflows", "Deployment workflows"), ("labs", "Labs")):
                section = docs / name
                section.mkdir()
                (section / "README.md").write_text(f"# {title}\n", encoding="utf-8")
                (section / "example.md").write_text(f"# {title} example\n", encoding="utf-8")

            with mock.patch.object(
                mkdocs_hooks,
                "SITE_ONLY_GUIDE_PREFIXES",
                ("workflows/", "labs/"),
            ):
                navigation = mkdocs_hooks.build_navigation(docs)

        paths = flatten_nav_paths(navigation)
        self.assertIn("workflows/example.md", paths)
        self.assertIn("labs/example.md", paths)
        self.assertIn("Deployment workflows", [next(iter(item)) for item in navigation])
        self.assertIn("Labs", [next(iter(item)) for item in navigation])

    def test_workflow_pages_carry_evidence_markers(self):
        workflows = REPOSITORY_ROOT / "guides" / "workflows"
        markers = ("✅ **VERIFIED**", "🟡 **RECONSTRUCTED**", "🔴 **GAP")
        pages = sorted(path for path in workflows.glob("*.md") if path.name != "README.md")

        self.assertTrue(pages)
        for page in pages:
            contents = page.read_text(encoding="utf-8")
            self.assertTrue(
                any(marker in contents for marker in markers),
                f"{page.relative_to(REPOSITORY_ROOT)} lacks an evidence-state marker",
            )

    def test_remote_training_python_fences_parse(self):
        workflow = REPOSITORY_ROOT / "guides/workflows/remote-training-to-ios.md"
        contents = workflow.read_text(encoding="utf-8")
        blocks = re.findall(r"^```python[^\n]*\n(.*?)^```[ \t]*$", contents, re.M | re.S)

        self.assertTrue(blocks)
        for index, block in enumerate(blocks, start=1):
            compile(block, f"{workflow} Python fence {index}", "exec")

    def test_remote_training_publication_contract(self):
        workflow = REPOSITORY_ROOT / "guides/workflows/remote-training-to-ios.md"
        contents = workflow.read_text(encoding="utf-8")
        python_blocks = re.findall(
            r"^```python[^\n]*\n(.*?)^```[ \t]*$", contents, re.M | re.S
        )
        trainer = next(block for block in python_blocks if "def main()" in block)
        smoke_launches = [block for block in python_blocks if '"--max-steps", "20"' in block]

        self.assertEqual(2, len(smoke_launches))
        for launch in smoke_launches:
            self.assertIn('"--save-steps", "10"', launch)
            self.assertIn('"--eval-steps", "10"', launch)

        first_upload = trainer.index("api.upload_folder(")
        self.assertLess(trainer.index("write_json(manifest_path, manifest)"), first_upload)
        self.assertLess(trainer.index("shutil.copy2(manifest_path"), first_upload)
        self.assertLess(trainer.index("shutil.copy2(eval_path"), first_upload)
        self.assertLess(
            trainer.index("adapter_commit = api.upload_folder"), trainer.index("del trainer")
        )
        self.assertGreater(
            trainer.index("merged_commit = api.upload_folder"), trainer.index("del trainer")
        )
        self.assertIn("logging_nan_inf_filter=False", trainer)
        self.assertIn('require_finite_metrics("training log"', trainer)
        self.assertIn("require_private_repo(api, args.adapter_repo)", trainer)
        main_body = trainer.split("def main()", 1)[1]
        self.assertLess(
            main_body.index("resume = get_last_checkpoint("),
            main_body.index("load_publication_receipt("),
        )
        self.assertLess(
            main_body.index("load_publication_receipt("),
            main_body.index("trainer.train("),
        )

        self.assertEqual(
            2,
            contents.count("coreai.llm.export ../artifacts/qwen3-ios-v1-hf"),
        )
        self.assertNotIn("coreai.llm.export <ORG>/qwen3-ios-v1-hf", contents)
        self.assertNotIn("hf upload ", contents)
        self.assertNotIn("exit 1", contents)
        self.assertIn("--model /outputs/mlx-run/base-model", contents)
        self.assertIn("--dataset-revision <DATASET_COMMIT_SHA>", contents)

    def test_remote_training_receipt_enforces_immutable_input_binding(self):
        workflow = REPOSITORY_ROOT / "guides/workflows/remote-training-to-ios.md"
        contents = workflow.read_text(encoding="utf-8")
        blocks = re.findall(r"^```python[^\n]*\n(.*?)^```[ \t]*$", contents, re.M | re.S)
        trainer = next(block for block in blocks if "def load_publication_receipt" in block)
        tree = ast.parse(trainer)
        function = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "load_publication_receipt"
        )

        def write_json(path, value):
            path.write_text(json.dumps(value), encoding="utf-8")

        namespace = {"json": json, "Path": Path, "write_json": write_json}
        exec(compile(ast.Module(body=[function], type_ignores=[]), "receipt", "exec"), namespace)
        load_receipt = namespace["load_publication_receipt"]
        inputs = {"immutable": "inputs"}

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "publication-receipt.json"
            fresh = {
                "schema_version": 1,
                "inputs": inputs,
                "artifacts": {},
                "events": [],
            }
            self.assertEqual(fresh, load_receipt(path, inputs, None))
            self.assertEqual(fresh, json.loads(path.read_text(encoding="utf-8")))

            path.unlink()
            with self.assertRaisesRegex(
                ValueError, "missing beside existing checkpoints.*new output directory"
            ):
                load_receipt(path, inputs, str(Path(directory) / "checkpoint-10"))
            self.assertFalse(path.exists())

            legacy = {
                "adapter": {"repo": "org/adapter", "commit_sha": "abc123"},
                "merged": {"repo": "org/merged", "commit_sha": None},
            }
            path.write_text(json.dumps(legacy), encoding="utf-8")
            before = path.read_bytes()
            with self.assertRaisesRegex(
                ValueError,
                r"preserve this output directory and start a new one.*"
                r"binding both its checkpoints and old publications",
            ):
                load_receipt(path, inputs, str(Path(directory) / "checkpoint-10"))
            self.assertEqual(before, path.read_bytes())
            self.assertNotIn("rename only `publication-receipt.json`", contents)

            receipt = {
                "schema_version": 1,
                "inputs": inputs,
                "artifacts": {
                    "adapter": {
                        "kind": "hugging_face",
                        "publications": [
                            {"repo": "org/adapter", "commit_sha": "abc123"}
                        ],
                    }
                },
            }
            path.write_text(json.dumps(receipt), encoding="utf-8")
            self.assertEqual(
                receipt,
                load_receipt(path, inputs, str(Path(directory) / "checkpoint-10")),
            )

            with self.assertRaisesRegex(ValueError, "different model or dataset inputs"):
                load_receipt(path, {"immutable": "different-inputs"}, None)

            invalid_events = {**receipt, "events": {}}
            path.write_text(json.dumps(invalid_events), encoding="utf-8")
            before = path.read_bytes()
            with self.assertRaisesRegex(ValueError, "events must be an array"):
                load_receipt(path, inputs, None)
            self.assertEqual(before, path.read_bytes())

    def test_remote_training_records_unresolved_upload_identity_before_raising(self):
        workflow = REPOSITORY_ROOT / "guides/workflows/remote-training-to-ios.md"
        contents = workflow.read_text(encoding="utf-8")
        blocks = re.findall(r"^```python[^\n]*\n(.*?)^```[ \t]*$", contents, re.M | re.S)
        trainer = next(block for block in blocks if "def record_hub_publication" in block)
        tree = ast.parse(trainer)
        function = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "record_hub_publication"
        )

        def write_json(path, value):
            path.write_text(json.dumps(value), encoding="utf-8")

        namespace = {"Path": Path, "write_json": write_json}
        exec(compile(ast.Module(body=[function], type_ignores=[]), "receipt", "exec"), namespace)
        record = namespace["record_hub_publication"]

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "publication-receipt.json"
            receipt = {"schema_version": 1, "inputs": {}, "artifacts": {}}
            path.write_text(json.dumps(receipt), encoding="utf-8")
            for invalid in (None, "", "   "):
                with self.assertRaisesRegex(ValueError, "may have succeeded"):
                    record(
                        path,
                        receipt,
                        "adapter",
                        "org/model",
                        invalid,
                        " https://huggingface.co/org/model/commit/unknown ",
                    )

            event = {
                "kind": "hub_upload_identity_unresolved",
                "artifact": "adapter",
                "repo": "org/model",
                "commit_url": "https://huggingface.co/org/model/commit/unknown",
            }
            self.assertEqual([event, event, event], receipt["events"])
            self.assertEqual(
                [event, event, event],
                json.loads(path.read_text(encoding="utf-8"))["events"],
            )
            self.assertEqual({}, receipt["artifacts"])

            record(
                path,
                receipt,
                "adapter",
                "org/model",
                "  abc123  ",
                "https://huggingface.co/org/model/commit/abc123",
            )
            self.assertEqual(
                "abc123",
                receipt["artifacts"]["adapter"]["publications"][0]["commit_sha"],
            )

    def test_remote_publication_helper_is_append_only_and_failure_safe(self):
        workflow = REPOSITORY_ROOT / "guides/workflows/remote-training-to-ios.md"
        contents = workflow.read_text(encoding="utf-8")
        blocks = re.findall(r"^```python[^\n]*\n(.*?)^```[ \t]*$", contents, re.M | re.S)
        helper = next(block for block in blocks if "def append_publication" in block)
        wanted = {
            "atomic_write",
            "load_receipt",
            "nonblank_identity",
            "normalize_publication",
            "append_event",
            "append_publication",
            "upload_hub",
        }
        functions = [
            node
            for node in ast.parse(helper).body
            if isinstance(node, ast.FunctionDef) and node.name in wanted
        ]
        namespace = {
            "argparse": argparse,
            "json": json,
            "os": os,
            "Path": Path,
        }
        exec(compile(ast.Module(body=functions, type_ignores=[]), "publisher", "exec"), namespace)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "publication-receipt.json"
            path.write_text(
                json.dumps({"schema_version": 1, "inputs": {}, "artifacts": {}}),
                encoding="utf-8",
            )
            publication = {"repo": "org/model", "commit_sha": "abc123"}
            namespace["append_publication"](path, "mlx_4bit", "hugging_face", publication)
            namespace["append_publication"](path, "mlx_4bit", "hugging_face", publication)
            receipt = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(
                [publication], receipt["artifacts"]["mlx_4bit"]["publications"]
            )

            before = path.read_bytes()
            for invalid in (None, "", "   "):
                with self.assertRaisesRegex(ValueError, "nonblank string"):
                    namespace["append_publication"](
                        path,
                        "invalid",
                        "hugging_face",
                        {"repo": "org/model", "commit_sha": invalid},
                    )
                self.assertEqual(before, path.read_bytes())

            namespace["append_publication"](
                path,
                "normalized",
                "hugging_face",
                {"repo": "org/model", "commit_sha": "  def456  "},
            )
            normalized = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(
                "def456",
                normalized["artifacts"]["normalized"]["publications"][0]["commit_sha"],
            )

            source_bound = {
                "repo": "org/model",
                "commit_sha": " abc123 ",
                "source_commit_sha": " source123 ",
            }
            namespace["append_publication"](
                path, "source_bound", "hugging_face", source_bound
            )
            namespace["append_publication"](
                path,
                "source_bound",
                "hugging_face",
                {
                    "repo": "org/model",
                    "commit_sha": "abc123",
                    "source_commit_sha": "source123",
                },
            )
            source_bound_receipt = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(
                [
                    {
                        "repo": "org/model",
                        "commit_sha": "abc123",
                        "source_commit_sha": "source123",
                    }
                ],
                source_bound_receipt["artifacts"]["source_bound"]["publications"],
            )

            release = {
                "release_url": "https://example.com/model.bin",
                "sha256": "digest",
                "source_commit_sha": " source123 ",
                "exporter_commit_sha": " exporter123 ",
            }
            namespace["append_publication"](path, "release", "release_file", release)
            namespace["append_publication"](
                path,
                "release",
                "release_file",
                {
                    **release,
                    "source_commit_sha": "source123",
                    "exporter_commit_sha": "exporter123",
                },
            )
            release_receipt = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(
                1, len(release_receipt["artifacts"]["release"]["publications"])
            )
            self.assertEqual(
                "exporter123",
                release_receipt["artifacts"]["release"]["publications"][0][
                    "exporter_commit_sha"
                ],
            )

            before_invalid_identity = path.read_bytes()
            for kind, invalid_publication in (
                (
                    "hugging_face",
                    {
                        "repo": "org/model",
                        "commit_sha": "abc123",
                        "source_commit_sha": "   ",
                    },
                ),
                (
                    "release_file",
                    {
                        "release_url": "https://example.com/model.bin",
                        "sha256": "digest",
                        "source_commit_sha": "source123",
                        "exporter_commit_sha": None,
                    },
                ),
            ):
                with self.assertRaisesRegex(ValueError, "must be a nonblank string"):
                    namespace["append_publication"](
                        path, "invalid_identity", kind, invalid_publication
                    )
                self.assertEqual(before_invalid_identity, path.read_bytes())
            before = path.read_bytes()

            class PublicApi:
                def create_repo(self, *args, **kwargs):
                    return None

                def repo_info(self, *args, **kwargs):
                    return SimpleNamespace(private=False)

            namespace["HfApi"] = PublicApi
            arguments = SimpleNamespace(
                repo="org/public",
                folder=Path(directory),
                message="test",
                source_commit_sha=None,
                receipt=path,
                artifact="mlx_fused",
            )
            with self.assertRaisesRegex(RuntimeError, "public repository"):
                namespace["upload_hub"](arguments)
            self.assertEqual(before, path.read_bytes())

            class BlankOidApi:
                def create_repo(self, *args, **kwargs):
                    return None

                def repo_info(self, *args, **kwargs):
                    return SimpleNamespace(private=True)

                def upload_folder(self, *args, **kwargs):
                    return SimpleNamespace(
                        oid="   ",
                        commit_url="https://huggingface.co/org/model/commit/unknown",
                    )

            namespace["HfApi"] = BlankOidApi
            arguments.repo = "org/model"
            arguments.artifact = "mlx_fused"
            with self.assertRaisesRegex(ValueError, "may have succeeded"):
                namespace["upload_hub"](arguments)
            unresolved = json.loads(path.read_text(encoding="utf-8"))["events"]
            self.assertEqual(
                [
                    {
                        "kind": "hub_upload_identity_unresolved",
                        "artifact": "mlx_fused",
                        "repo": "org/model",
                        "commit_url": "https://huggingface.co/org/model/commit/unknown",
                    }
                ],
                unresolved,
            )

    def test_remote_training_mlx_normalizer_rejects_malformed_completion(self):
        workflow = REPOSITORY_ROOT / "guides/workflows/remote-training-to-ios.md"
        contents = workflow.read_text(encoding="utf-8")
        blocks = re.findall(r"^```python[^\n]*\n(.*?)^```[ \t]*$", contents, re.M | re.S)
        preparation = next(block for block in blocks if "def normalize(row" in block)
        tree = ast.parse(preparation)
        function = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "normalize"
        )
        namespace = {}
        exec(compile(ast.Module(body=[function], type_ignores=[]), "normalize", "exec"), namespace)
        normalize = namespace["normalize"]

        normalized = normalize(
            {
                "prompt": [{"role": "user", "content": "Question"}],
                "completion": [{"role": "assistant", "content": "Answer"}],
            }
        )
        self.assertEqual(["user", "assistant"], [item["role"] for item in normalized["messages"]])
        with self.assertRaisesRegex(ValueError, "exactly one assistant"):
            normalize(
                {
                    "prompt": [{"role": "user", "content": "Question"}],
                    "completion": [
                        {"role": "assistant", "content": "First"},
                        {"role": "assistant", "content": "Second"},
                    ],
                }
            )

    def test_global_header_targets_workflows_landing_page(self):
        config = (REPOSITORY_ROOT / "mkdocs.yml").read_text(encoding="utf-8")
        header_entry = re.search(
            r"^[ ]{4}- title: Workflows\n[ ]{6}url: workflows/$",
            config,
            re.M,
        )
        self.assertIsNotNone(header_entry)
        self.assertEqual(1, config.count("- title: Workflows\n"))

    def test_normalizes_verifier_metadata_on_swift_fences(self):
        markdown = (
            "```swift compile:27 imports:FoundationModels\nlet value = 1\n```\n\n"
            "> ```swift prelude:guide-context\n> let quoted = true\n> ```\n\n"
            "```python linenums=1\nprint('kept')\n```\n"
        )
        result = mkdocs_hooks.transform_markdown(
            markdown,
            REPOSITORY_ROOT / "guides" / "README.md",
            REPOSITORY_ROOT / "guides",
            REPOSITORY_ROOT,
            "https://github.com/example/project",
        )
        self.assertIn("```swift\n", result)
        self.assertIn("> ```swift\n", result)
        self.assertIn("```python linenums=1\n", result)
        self.assertNotIn("compile:27", result)
        self.assertNotIn("prelude:guide-context", result)

    def test_rewrites_repository_files_and_directories_but_not_guides(self):
        source = REPOSITORY_ROOT / "guides" / "README.md"
        markdown = (
            "[runbook](../notes/FRESHNESS-RUNBOOK.md#daily-sweep)\n"
            "[scripts](../scripts/)\n"
            "[guide](part-01-orientation-and-gating/)\n"
        )
        result = mkdocs_hooks.transform_markdown(
            markdown,
            source,
            REPOSITORY_ROOT / "guides",
            REPOSITORY_ROOT,
            "https://github.com/example/project",
        )
        self.assertIn(
            "https://github.com/example/project/blob/main/notes/"
            "FRESHNESS-RUNBOOK.md#daily-sweep",
            result,
        )
        self.assertIn("https://github.com/example/project/tree/main/scripts", result)
        self.assertIn("](part-01-orientation-and-gating/README.md)", result)

    def test_rewrites_frozen_noema_note_to_its_immutable_ref(self):
        source = (
            REPOSITORY_ROOT
            / "guides/part-02-foundation-models-everyday-api/references/03-tools-and-tool-calling.md"
        )
        result = mkdocs_hooks.transform_markdown(
            "[Noema](../../../notes/repos/noema-ios.md)\n",
            source,
            REPOSITORY_ROOT / "guides",
            REPOSITORY_ROOT,
            "https://github.com/example/project",
        )
        snapshot = mdlinks.REPOSITORY_PATH_SNAPSHOTS["notes/repos/noema-ios.md"]
        self.assertIn(
            "https://github.com/example/project/blob/"
            f"{snapshot.ref}/notes/repos/noema-ios.md",
            result,
        )

    def test_does_not_rewrite_links_inside_code(self):
        markdown = (
            "`[inline](../notes/FRESHNESS-RUNBOOK.md)`\n\n"
            "```text\n[block](../notes/FRESHNESS-RUNBOOK.md)\n```\n"
        )
        result = mkdocs_hooks.transform_markdown(
            markdown,
            REPOSITORY_ROOT / "guides" / "README.md",
            REPOSITORY_ROOT / "guides",
            REPOSITORY_ROOT,
            "https://github.com/example/project",
        )
        self.assertEqual(markdown, result)

    def test_known_upstream_pseudo_link_has_an_explicit_target(self):
        source = (
            REPOSITORY_ROOT
            / "guides/part-13-mlx-swift/references/01-mlx-swift-lm-in-an-app.md"
        )
        result = mkdocs_hooks.transform_markdown(
            "[MLXHuggingFace](MLXHuggingFace)\n",
            source,
            REPOSITORY_ROOT / "guides",
            REPOSITORY_ROOT,
            "https://github.com/example/project",
        )
        self.assertIn(
            "https://github.com/ml-explore/mlx-swift-lm/tree/main/"
            "Libraries/MLXHuggingFace",
            result,
        )

    def test_reference_definition_is_rewritten(self):
        markdown = "[runbook]: ../notes/FRESHNESS-RUNBOOK.md \"Freshness\"\n"
        result = mkdocs_hooks.transform_markdown(
            markdown,
            REPOSITORY_ROOT / "guides" / "README.md",
            REPOSITORY_ROOT / "guides",
            REPOSITORY_ROOT,
            "https://github.com/example/project",
        )
        self.assertIn("/blob/main/notes/FRESHNESS-RUNBOOK.md \"Freshness\"", result)

    def test_footnote_prose_links_are_rewritten(self):
        markdown = (
            "[^proof]: The evidence is in "
            "[the runbook](../notes/FRESHNESS-RUNBOOK.md).\n"
        )
        result = mkdocs_hooks.transform_markdown(
            markdown,
            REPOSITORY_ROOT / "guides" / "README.md",
            REPOSITORY_ROOT / "guides",
            REPOSITORY_ROOT,
            "https://github.com/example/project",
        )
        self.assertIn("/blob/main/notes/FRESHNESS-RUNBOOK.md", result)

    def test_duplicate_headings_receive_github_suffixes(self):
        markdown = "# Page\n\n## ⚠️ The silent failure\n\n## ⚠️ The silent failure\n"
        result = mkdocs_hooks.transform_markdown(
            markdown,
            REPOSITORY_ROOT / "guides" / "README.md",
            REPOSITORY_ROOT / "guides",
            REPOSITORY_ROOT,
            "https://github.com/example/project",
        )
        self.assertIn("## ⚠️ The silent failure {#️-the-silent-failure-1}", result)

    def test_transform_does_not_modify_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            docs = root / "guides"
            notes = root / "notes"
            docs.mkdir()
            notes.mkdir()
            source = docs / "README.md"
            source.write_text("# Test\n\n[proof](../notes/proof.md)\n", encoding="utf-8")
            (notes / "proof.md").write_text("proof\n", encoding="utf-8")
            before = source.read_bytes()

            mkdocs_hooks.transform_markdown(
                source.read_text(encoding="utf-8"),
                source,
                docs,
                root,
                "https://github.com/example/project",
            )

            self.assertEqual(before, source.read_bytes())

    def test_on_config_installs_navigation_and_shared_slugger(self):
        config = FakeConfig(
            {
                "docs_dir": str(REPOSITORY_ROOT / "guides"),
                "repo_url": "https://github.com/example/project",
            },
            config_file_path=str(REPOSITORY_ROOT / "mkdocs.yml"),
        )
        result = mkdocs_hooks.on_config(config)
        self.assertIs(result, config)
        self.assertEqual(mkdocs_hooks.slugify, config.mdx_configs["toc"]["slugify"])
        self.assertEqual(
            mkdocs_hooks.build_navigation(REPOSITORY_ROOT / "guides"),
            config["nav"],
        )

    def test_slugger_accepts_markdown_separator_callback(self):
        self.assertEqual("the-tool-protocol", mdslug.slugify("The `Tool` protocol", "-"))
        self.assertEqual("️-trap", mdslug.slugify("⚠️ Trap", "-"))
        self.assertEqual("foo_-_bar", mdslug.slugify("Foo - Bar", "_"))


if __name__ == "__main__":
    unittest.main()
