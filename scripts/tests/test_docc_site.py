#!/usr/bin/env python3
"""Tests for immutable guide-to-DocC staging and archive verification."""

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


REPO = Path(__file__).resolve().parents[2]


def load_script(name, filename):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


builder = load_script("build_docc_site", "build-docc-site.py")
verifier = load_script("verify_docc_site", "verify-docc-site.py")
canonicalizer = load_script(
    "canonicalize_docc_links", "canonicalize-docc-links.py"
)


class DocCSiteTests(unittest.TestCase):
    def make_fixture(self):
        temporary = tempfile.TemporaryDirectory()
        repository = Path(temporary.name)
        guides = repository / "guides"
        references = guides / "part-01-start" / "references"
        scripts = repository / "scripts"
        references.mkdir(parents=True)
        scripts.mkdir()

        (scripts / "helper.sh").write_text("#!/bin/sh\n", encoding="utf-8")
        (guides / "README.md").write_text(
            "# Fixture guides\n\n[Part one](part-01-start/)\n",
            encoding="utf-8",
        )
        (guides / "API-INDEX.md").write_text("# API index\n", encoding="utf-8")
        (guides / "SILENT-FAILURES.md").write_text(
            "# Silent failures\n", encoding="utf-8"
        )
        (guides / "part-01-start" / "README.md").write_text(
            "# Part one\n\n[Guide](references/01-guide.md)\n",
            encoding="utf-8",
        )
        (references / "01-guide.md").write_text(
            "# Guide one\n\n"
            "[Series](../../README.md#fixture-guides)\n\n"
            "[Helper](../../../scripts/helper.sh#L1)\n\n"
            "> # Quoted upstream title\n\n"
            "> Plain quotation: **bold continuation**\n\n"
            "> Note: Keep this as an intentional aside.\n\n"
            "Use ``SymbolName`` as code.\n\n"
            "Use ``An error with\n"
            "`nested` code`` across lines.\n\n"
            "Quoting <doc:Prose> in prose.\n\n"
            "Keep `<doc:InSingle>` and ``<doc:InDouble>`` verbatim.\n\n"
            "Keep `<doc:SingleAcross>\n"
            "<doc:SingleContinuation>` verbatim.\n\n"
            "Keep ```<doc:TripleAcross>\n"
            "<doc:TripleContinuation>``` verbatim.\n\n"
            "An unmatched ` marker stays literal.\n\n"
            "Escape <doc:AfterUnmatched> after the paragraph.\n\n"
            "> ```cpp\n"
            "> operator[](thread_index_type idx)\n"
            "> ```\n",
            encoding="utf-8",
        )
        return temporary, repository, guides

    def build_fixture(self, repository, guides):
        catalog = repository / ".build" / "docc" / "Fixture.docc"
        manifest = repository / ".build" / "docc" / "manifest.json"
        result = builder.build_catalog(
            guides,
            catalog,
            manifest,
            repository,
            "https://github.com/example/fixture",
            "main",
        )
        return catalog, manifest, result

    def make_rendered_site(self, repository, result):
        site = repository / "site"
        data = site / "data" / "documentation" / "fixture"
        data.mkdir(parents=True)

        assets = {
            "favicon.ico": b"icon",
            "favicon.svg": b"svg",
            "css/index.css": b"body { color: black; }",
            "js/chunk-vendors.js": b"vendor",
            "js/index.js": b"app",
        }
        for relative, content in assets.items():
            target = site / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)

        shell = (
            '<!doctype html><html><head>'
            '<link rel="icon" href="/fixture/favicon.ico">'
            '<link rel="mask-icon" href="/fixture/favicon.svg">'
            '<link rel="stylesheet" href="/fixture/css/index.css">'
            '<script>var baseUrl = "/fixture/"</script>'
            '<script defer src="/fixture/js/chunk-vendors.js"></script>'
            '<script defer src="/fixture/js/index.js"></script>'
            '</head><body><div id="app"></div></body></html>'
        )
        (site / "index.html").write_text(shell, encoding="utf-8")

        for page in result["pages"]:
            identifier = page["identifier"]
            json_path = data / f"{identifier.casefold()}.json"
            json_path.write_text(
                json.dumps(
                    {
                        "identifier": {
                            "url": f"doc://fixture/documentation/Fixture/{identifier}"
                        },
                        "references": {},
                    }
                ),
                encoding="utf-8",
            )
            route = site / "documentation" / "fixture" / identifier.casefold()
            route.mkdir(parents=True)
            (route / "index.html").write_text(shell, encoding="utf-8")
        return site, data, assets

    def make_renderer(self, repository, assets):
        renderer = repository / "renderer"
        renderer.mkdir()
        (renderer / "index.html").write_text("template", encoding="utf-8")
        (renderer / "index-template.html").write_text(
            "template {{BASE_PATH}}", encoding="utf-8"
        )
        for relative, content in assets.items():
            target = renderer / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        return renderer

    def test_builds_unique_curated_pages_without_mutating_sources(self):
        temporary, repository, guides = self.make_fixture()
        self.addCleanup(temporary.cleanup)
        before = {
            path.relative_to(guides): path.read_bytes() for path in guides.rglob("*.md")
        }

        catalog, manifest, result = self.build_fixture(repository, guides)

        after = {
            path.relative_to(guides): path.read_bytes() for path in guides.rglob("*.md")
        }
        self.assertEqual(before, after)
        self.assertEqual(result["page_count"], 5)
        self.assertEqual(len(list(catalog.glob("*.md"))), 5)
        self.assertTrue(manifest.is_file())

        root = (catalog / "AppleAIGuides.md").read_text(encoding="utf-8")
        part = (catalog / "Part-01.md").read_text(encoding="utf-8")
        guide = (catalog / "Part-01-Guide-01.md").read_text(encoding="utf-8")
        self.assertIn("@TechnologyRoot", root)
        self.assertIn("[Part one](<doc:Part-01>)", root)
        self.assertIn("- <doc:Part-01>", root)
        self.assertIn("[Guide](<doc:Part-01-Guide-01>)", part)
        self.assertIn("- <doc:Part-01-Guide-01>", part)
        self.assertIn(
            "[Series](<doc://dev.hbmartin.apple-ai-guides/documentation/AppleAIGuides#fixture-guides>)",
            guide,
        )
        self.assertIn(
            "https://github.com/example/fixture/blob/main/scripts/helper.sh#L1", guide
        )
        self.assertIn("> ## Quoted upstream title", guide)
        self.assertIn(
            "> <!-- -->Plain quotation: **bold continuation**", guide
        )
        self.assertIn("> Note: Keep this as an intentional aside.", guide)
        self.assertIn("Use <code>SymbolName</code> as code.", guide)
        self.assertIn(
            "Use <code>An error with\n`nested` code</code> across lines.", guide
        )
        self.assertIn("operator[](thread_index_type idx)", guide)
        self.assertIn("Quoting \\<doc:Prose> in prose.", guide)
        self.assertIn(
            "Keep `<doc:InSingle>` and <code>&lt;doc:InDouble&gt;</code> verbatim.",
            guide,
        )
        self.assertNotIn("\\<doc:InSingle>", guide)
        self.assertNotIn("\\&lt;doc:", guide)
        self.assertIn(
            "Keep `<doc:SingleAcross>\n<doc:SingleContinuation>` verbatim.",
            guide,
        )
        self.assertIn(
            "Keep ```<doc:TripleAcross>\n<doc:TripleContinuation>``` verbatim.",
            guide,
        )
        self.assertNotIn("\\<doc:SingleContinuation>", guide)
        self.assertNotIn("\\<doc:TripleContinuation>", guide)
        self.assertIn("An unmatched ` marker stays literal.", guide)
        self.assertIn("Escape \\<doc:AfterUnmatched> after the paragraph.", guide)

        manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
        self.assertEqual(
            {page["identifier"] for page in manifest_data["pages"]},
            {
                "AppleAIGuides",
                "API-Index",
                "Silent-Failures",
                "Part-01",
                "Part-01-Guide-01",
            },
        )

    def test_rebuild_replaces_only_a_marked_generated_catalog(self):
        temporary, repository, guides = self.make_fixture()
        self.addCleanup(temporary.cleanup)
        catalog, _, _ = self.build_fixture(repository, guides)
        stale = catalog / "Stale.md"
        stale.write_text("stale", encoding="utf-8")

        catalog, _, _ = self.build_fixture(repository, guides)
        self.assertFalse((catalog / "Stale.md").exists())

    def test_refuses_to_replace_an_unmarked_catalog(self):
        temporary, repository, guides = self.make_fixture()
        self.addCleanup(temporary.cleanup)
        catalog = repository / ".build" / "docc" / "Fixture.docc"
        catalog.mkdir(parents=True)
        (catalog / "User.md").write_text("# User content\n", encoding="utf-8")

        with self.assertRaisesRegex(builder.CatalogError, "refusing to replace"):
            builder.build_catalog(
                guides,
                catalog,
                catalog.parent / "manifest.json",
                repository,
                "https://github.com/example/fixture",
                "main",
            )
        self.assertTrue((catalog / "User.md").is_file())

    def test_unresolved_relative_link_fails(self):
        temporary, repository, guides = self.make_fixture()
        self.addCleanup(temporary.cleanup)
        guide = guides / "part-01-start" / "references" / "01-guide.md"
        guide.write_text(
            guide.read_text(encoding="utf-8") + "\n[Missing](missing.md)\n",
            encoding="utf-8",
        )

        with self.assertRaisesRegex(builder.CatalogError, "target does not exist"):
            self.build_fixture(repository, guides)

    def test_archive_verifier_checks_pages_routes_and_relative_urls(self):
        temporary, repository, guides = self.make_fixture()
        self.addCleanup(temporary.cleanup)
        _, manifest, result = self.build_fixture(repository, guides)
        site, data, _ = self.make_rendered_site(repository, result)

        page_count, html_count, asset_count = verifier.verify(site, manifest)
        self.assertEqual(page_count, 5)
        self.assertEqual(html_count, 6)
        self.assertEqual(asset_count, 5)

        broken = data / "part-01-guide-01.json"
        payload = json.loads(broken.read_text(encoding="utf-8"))
        payload["references"] = {
            "mail": {"url": "mailto:maintainer.md@example.com"},
            "external": {"url": "https://example.com/guide.md"},
            "protocol-relative": {"url": "//example.com/guide.md"},
        }
        broken.write_text(json.dumps(payload), encoding="utf-8")
        verifier.verify(site, manifest)

        payload["references"] = {"bad": {"url": "../guide.md"}}
        broken.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(verifier.VerificationError, "relative .md URLs"):
            verifier.verify(site, manifest)

    def test_archive_verifier_rejects_missing_javascript(self):
        temporary, repository, guides = self.make_fixture()
        self.addCleanup(temporary.cleanup)
        _, manifest, result = self.build_fixture(repository, guides)
        site, _, _ = self.make_rendered_site(repository, result)
        (site / "js" / "index.js").unlink()

        with self.assertRaisesRegex(
            verifier.VerificationError, "missing referenced browser asset"
        ):
            verifier.verify(site, manifest)

    def test_archive_verifier_rejects_asset_outside_hosting_base_path(self):
        temporary, repository, guides = self.make_fixture()
        self.addCleanup(temporary.cleanup)
        _, manifest, result = self.build_fixture(repository, guides)
        site, _, _ = self.make_rendered_site(repository, result)
        root = site / "index.html"
        root.write_text(
            root.read_text(encoding="utf-8").replace(
                "/fixture/js/index.js", "/wrong/js/index.js"
            ),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(
            verifier.VerificationError, "outside DocC baseUrl"
        ):
            verifier.verify(site, manifest)

    def test_archive_verifier_matches_every_pinned_renderer_asset(self):
        temporary, repository, guides = self.make_fixture()
        self.addCleanup(temporary.cleanup)
        _, manifest, result = self.build_fixture(repository, guides)
        site, _, assets = self.make_rendered_site(repository, result)
        renderer = self.make_renderer(repository, assets)

        verifier.verify(site, manifest, renderer)

        dynamic_chunk = renderer / "js" / "dynamic-chunk.js"
        dynamic_chunk.write_text("chunk", encoding="utf-8")
        with self.assertRaisesRegex(
            verifier.VerificationError, "missing DocC renderer asset"
        ):
            verifier.verify(site, manifest, renderer)

    def test_archive_verifier_rejects_changed_renderer_asset(self):
        temporary, repository, guides = self.make_fixture()
        self.addCleanup(temporary.cleanup)
        _, manifest, result = self.build_fixture(repository, guides)
        site, _, assets = self.make_rendered_site(repository, result)
        renderer = self.make_renderer(repository, assets)
        (site / "js" / "index.js").write_text("changed", encoding="utf-8")

        with self.assertRaisesRegex(
            verifier.VerificationError, "renderer asset differs from source"
        ):
            verifier.verify(site, manifest, renderer)

    def test_source_snapshot_covers_page_discovery(self):
        temporary, repository, guides = self.make_fixture()
        self.addCleanup(temporary.cleanup)
        guide = guides / "part-01-start" / "references" / "01-guide.md"
        discover_pages = builder.discover_pages

        def mutate_during_discovery(source_root):
            pages = discover_pages(source_root)
            guide.write_text(
                guide.read_text(encoding="utf-8") + "\nChanged during discovery.\n",
                encoding="utf-8",
            )
            return pages

        with mock.patch.object(
            builder, "discover_pages", side_effect=mutate_during_discovery
        ), self.assertRaisesRegex(builder.CatalogError, "changed during catalog"):
            self.build_fixture(repository, guides)

    def test_applies_docc_anchor_fixits_only_to_generated_catalog(self):
        temporary, repository, guides = self.make_fixture()
        self.addCleanup(temporary.cleanup)
        catalog, _, _ = self.build_fixture(repository, guides)
        generated = catalog / "Part-01-Guide-01.md"
        diagnostics = repository / ".build" / "docc" / "diagnostics.json"
        diagnostics.write_text(
            json.dumps(
                {
                    "diagnostics": [
                        {
                            "source": generated.as_uri(),
                            "summary": (
                                "'fixture-guides' doesn't exist at '/AppleAIGuides'"
                            ),
                            "range": {"start": {"line": 3, "column": 1}},
                            "solutions": [
                                {
                                    "replacements": [
                                        {
                                            "text": "Fixture-guides",
                                            "range": {},
                                        }
                                    ]
                                }
                            ],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        source_before = (
            guides / "part-01-start" / "references" / "01-guide.md"
        ).read_bytes()

        applied, changed = canonicalizer.canonicalize(catalog, diagnostics)

        self.assertEqual((applied, changed), (1, 1))
        self.assertIn("#Fixture-guides", generated.read_text(encoding="utf-8"))
        self.assertEqual(
            source_before,
            (guides / "part-01-start" / "references" / "01-guide.md").read_bytes(),
        )

    def test_refuses_to_edit_unmarked_docc_catalog(self):
        temporary, repository, guides = self.make_fixture()
        self.addCleanup(temporary.cleanup)
        catalog, _, _ = self.build_fixture(repository, guides)
        marker = catalog.parent / (
            f".{catalog.name}{canonicalizer.GENERATED_MARKER_SUFFIX}"
        )
        marker.unlink()
        diagnostics = repository / ".build" / "docc" / "diagnostics.json"
        diagnostics.write_text(json.dumps({"diagnostics": []}), encoding="utf-8")

        with self.assertRaisesRegex(
            canonicalizer.CanonicalizationError, "without generated marker"
        ):
            canonicalizer.canonicalize(catalog, diagnostics)

    def test_ignores_unidentified_non_anchor_diagnostic(self):
        temporary, repository, guides = self.make_fixture()
        self.addCleanup(temporary.cleanup)
        catalog, _, _ = self.build_fixture(repository, guides)
        diagnostics = repository / ".build" / "docc" / "diagnostics.json"
        diagnostics.write_text(
            json.dumps(
                {
                    "diagnostics": [
                        {
                            "severity": "warning",
                            "source": (catalog / "Part-01-Guide-01.md").as_uri(),
                            "summary": "A Linux diagnostic without an identifier",
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        self.assertEqual(canonicalizer.canonicalize(catalog, diagnostics), (0, 0))

    def test_refuses_docc_fixits_outside_generated_catalog(self):
        temporary, repository, guides = self.make_fixture()
        self.addCleanup(temporary.cleanup)
        catalog, _, _ = self.build_fixture(repository, guides)
        diagnostics = repository / ".build" / "docc" / "diagnostics.json"
        source = guides / "README.md"
        diagnostics.write_text(
            json.dumps(
                {
                    "diagnostics": [
                        {
                            "id": "org.swift.docc.unresolvedTopicReference",
                            "source": source.as_uri(),
                            "summary": "'fixture' is not an anchor of '/Root'",
                            "solutions": [
                                {"replacements": [{"text": "Fixture", "range": {}}]}
                            ],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(
            canonicalizer.CanonicalizationError, "outside the generated catalog"
        ):
            canonicalizer.canonicalize(catalog, diagnostics)

    def test_drops_unresolvable_section_but_keeps_generated_page_link(self):
        temporary, repository, guides = self.make_fixture()
        self.addCleanup(temporary.cleanup)
        catalog, _, _ = self.build_fixture(repository, guides)
        generated = catalog / "Part-01-Guide-01.md"
        diagnostics = repository / ".build" / "docc" / "diagnostics.json"
        diagnostics.write_text(
            json.dumps(
                {
                    "diagnostics": [
                        {
                            "id": "org.swift.docc.unresolvedTopicReference",
                            "source": generated.as_uri(),
                            "summary": (
                                "'fixture-guides' is not an anchor of '/AppleAIGuides'"
                            ),
                            "range": {"start": {"line": 3, "column": 1}},
                            "solutions": [],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        applied, changed = canonicalizer.canonicalize(catalog, diagnostics)

        self.assertEqual((applied, changed), (1, 1))
        text = generated.read_text(encoding="utf-8")
        self.assertIn("documentation/AppleAIGuides>)", text)
        self.assertNotIn("#fixture-guides", text)

    def test_drops_repeated_hyphen_fixit_that_docc_cannot_resolve(self):
        diagnostic = {
            "summary": "'section-heading' is not an anchor of '/Page'",
            "solutions": [
                {"replacements": [{"text": "Section--heading", "range": {}}]}
            ],
        }

        self.assertIsNone(canonicalizer.replacement_text(diagnostic))

    def test_anchor_fix_targets_only_the_matching_docc_fragment(self):
        lines = [
            "[web](https://example.com/#old-anchor) and "
            "<doc:SomePage#old-anchor>\n"
        ]

        changed = canonicalizer.replace_fragment(
            lines, "old-anchor", "New-anchor", 1, Path("Guide.md")
        )

        self.assertTrue(changed)
        self.assertIn("https://example.com/#old-anchor", lines[0])
        self.assertIn("<doc:SomePage#New-anchor>", lines[0])

    def test_anchor_fix_rejects_a_different_single_docc_fragment(self):
        lines = ["<doc:SomePage#different-anchor>\n"]

        with self.assertRaisesRegex(
            canonicalizer.CanonicalizationError, "could not uniquely locate"
        ):
            canonicalizer.replace_fragment(
                lines, "old-anchor", "New-anchor", 1, Path("Guide.md")
            )


if __name__ == "__main__":
    unittest.main()
