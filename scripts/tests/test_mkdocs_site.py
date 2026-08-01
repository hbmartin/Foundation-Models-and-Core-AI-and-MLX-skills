import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from scripts import mdslug, mkdocs_hooks


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

        self.assertEqual(80, len(paths))
        self.assertEqual(source_paths, sorted(paths))
        self.assertEqual(len(paths), len(set(paths)))
        self.assertEqual("Overview", next(iter(navigation[0])))
        self.assertEqual("Parts", next(iter(navigation[1])))
        self.assertEqual("Cross-cutting indexes", next(iter(navigation[2])))

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
        self.assertNotIn("The `Tool` protocol, calling modes, and the required-mode loop", titles)

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
        self.assertEqual(80, len(flatten_nav_paths(config["nav"])))

    def test_slugger_accepts_markdown_separator_callback(self):
        self.assertEqual("the-tool-protocol", mdslug.slugify("The `Tool` protocol", "-"))
        self.assertEqual("️-trap", mdslug.slugify("⚠️ Trap", "-"))


if __name__ == "__main__":
    unittest.main()
