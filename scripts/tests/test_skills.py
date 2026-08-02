#!/usr/bin/env python3
"""Tests for generating installable Claude Code skills from the guides."""

import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[2]
GUIDES = REPO / "guides"
SKILLS = REPO / "skills"
MANIFEST = REPO / "notes" / "synthesis" / "skill-manifest.json"
BUILD_SKILLS = REPO / "scripts" / "build-skills.py"


def load_script(name, filename):
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


builder = load_script("build_skills", "build-skills.py")
verifier = load_script("verify_skills", "verify-skills.py")


PART_README = """\
# Part 1 — Orientation

**Version floor:** everything here is **27.0 and only 27.0**. Older SDKs lack it.

**Who this is for:** everyone.

---

## ⚠️ Read this before you trust a signature

> 🟡 **RECONSTRUCTED** — spelling inferred from a session.

## Why this part exists

Because the stack is new.

## Read this first: the triage table

| If your situation is… | Read | Why |
|---|---|---|
| "I need the map" | [1.1 §2](references/01-map.md) | The whole picture |
| "I need gating" | [1.1 §5](references/01-map.md) | `@available` rules |

## The guides in this part

### [1.1 — The map](references/01-map.md)
A tour of the stack, and where each piece stops.

> ⚠️ **SILENT FAILURE** — the wrong backend returns plausible output.

## Reading order

Read 1.1 first.

## What this part deliberately does not cover

Nothing else.

## Sources for this part

WWDC sessions.
"""

REFERENCE = """\
# The map

## What this covers

The stack.

## 1. Orientation

Text.

```swift compile:27 imports:CoreAI
// ## not a heading, and this fence must survive byte-for-byte
let x = [Int](repeating: 0, count: rank)
```

> ```swift illustrative
> // a blockquoted fence, which the callout extractor's regex ignores
> ```

## 2. ⚠️ The trap

More text, citing [the runbook](../../../notes/FRESHNESS-RUNBOOK.md).
"""

SERIES_README = """\
# Apple on-device AI

## Editorial conventions

Markers are load-bearing.
"""

SILENT_FAILURES = """\
# The silent-failure index

**2 of them.**

## Wrong output

*Runs and returns output that is wrong.*

**Part 1**

- [The wrong backend returns plausible output.](part-01-orientation/README.md#the-guides-in-this-part) — 1.README 🔇
- [A trap that does not throw.](part-01-orientation/references/01-map.md#2-️-the-trap) — 1.1 🔇

---

🔇 = the guide marks this as an explicit **SILENT FAILURE** callout.
"""

API_INDEX = """\
# API & symbol index

**1 symbol.**

## CoreAI  <sub>1 symbols</sub>

| Symbol | 26.5 | 27.0 | Covered in |
|---|:-:|:-:|---|
| `AIModel` | ✓ | ✓ | [1.1](part-01-orientation/references/01-map.md) |
"""

SKILL_MANIFEST = {
    "schema_version": 1,
    "repository": {"url": "https://github.com/owner/repo", "branch": "main"},
    "defaults": {"max_triage_rows": 18},
    "skills": [
        {
            "name": "apple-test-skill",
            "title": "Test skill",
            "owns": [{"part": 1}],
            "description": "Covers the orientation part of the series.",
            "when_to_use": "Use when choosing a stack.",
            "related": [],
        }
    ],
}


def make_fixture(root):
    guides = root / "guides"
    part = guides / "part-01-orientation"
    (part / "references").mkdir(parents=True)
    (guides / "README.md").write_text(SERIES_README, encoding="utf-8")
    (guides / "SILENT-FAILURES.md").write_text(SILENT_FAILURES, encoding="utf-8")
    (guides / "API-INDEX.md").write_text(API_INDEX, encoding="utf-8")
    (part / "README.md").write_text(PART_README, encoding="utf-8")
    (part / "references" / "01-map.md").write_text(REFERENCE, encoding="utf-8")
    notes = root / "notes"
    notes.mkdir()
    (notes / "FRESHNESS-RUNBOOK.md").write_text("# Runbook\n", encoding="utf-8")
    (notes / "skill-manifest.json").write_text(
        json.dumps(SKILL_MANIFEST), encoding="utf-8"
    )
    (root / "notes" / "sdk-interfaces").mkdir()
    return guides


class SkillBuildTests(unittest.TestCase):
    def build(self, root, guides, **overrides):
        arguments = dict(
            source_root=guides,
            skills_root=root / "skills",
            manifest_path=root / "notes" / "skill-manifest.json",
            repository_root=root,
            interfaces=root / "notes" / "sdk-interfaces",
        )
        arguments.update(overrides)
        return builder.build_skills(**arguments)

    def test_sources_are_untouched_by_a_build(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            guides = make_fixture(root)
            before = {
                path.relative_to(guides): path.read_bytes()
                for path in guides.rglob("*.md")
            }
            self.build(root, guides)
            after = {
                path.relative_to(guides): path.read_bytes()
                for path in guides.rglob("*.md")
            }
            self.assertEqual(before, after)

    def test_bundles_part_readmes_but_not_deep_references(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            guides = make_fixture(root)
            self.build(root, guides)
            skill = root / "skills" / "apple-test-skill"
            self.assertTrue((skill / "references" / "part-01-orientation" / "README.md").is_file())
            self.assertFalse(
                (skill / "references" / "part-01-orientation" / "references").exists()
            )
            for name in ("API-INDEX.md", "SILENT-FAILURES.md", "SECTION-MAPS.md"):
                self.assertTrue((skill / "references" / name).is_file(), name)

    def test_mirrored_layout_leaves_intra_document_anchors_alone(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            guides = make_fixture(root)
            self.build(root, guides)
            copied = (
                root / "skills" / "apple-test-skill" / "references"
                / "part-01-orientation" / "README.md"
            ).read_text(encoding="utf-8")
            # Deep references leave the skill, so they become absolute...
            self.assertIn("https://github.com/owner/repo/blob/main/guides/", copied)
            # ...while the reproduced callouts and headings are untouched.
            self.assertIn("⚠️ **SILENT FAILURE**", copied)
            self.assertIn("**Version floor:**", copied)

    def test_out_of_guides_links_become_repository_urls(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            guides = make_fixture(root)
            self.build(root, guides)
            maps = (
                root / "skills" / "apple-test-skill" / "references" / "SECTION-MAPS.md"
            ).read_text(encoding="utf-8")
            self.assertIn(
                "https://github.com/owner/repo/blob/main/guides/part-01-orientation"
                "/references/01-map.md",
                maps,
            )

    def test_section_maps_use_github_faithful_anchors(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            guides = make_fixture(root)
            self.build(root, guides)
            maps = (
                root / "skills" / "apple-test-skill" / "references" / "SECTION-MAPS.md"
            ).read_text(encoding="utf-8")
            # GitHub drops U+26A0 as a symbol but keeps its U+FE0F variation
            # selector, so the anchor for '## 2. ⚠️ The trap' keeps the mark.
            self.assertIn("`#2-️-the-trap`", maps)
            # A '##' inside a fence is not a heading.
            self.assertNotIn("not a heading", maps)

    def test_silent_failure_slice_keeps_only_owned_entries(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            guides = make_fixture(root)
            self.build(root, guides)
            sliced = (
                root / "skills" / "apple-test-skill" / "references" / "SILENT-FAILURES.md"
            ).read_text(encoding="utf-8")
            self.assertIn("The wrong backend returns plausible output.", sliced)
            self.assertIn("A trap that does not throw.", sliced)
            self.assertIn("🔇", sliced)

    def test_silent_failure_slice_does_not_read_a_blurb_as_a_guide_id(self):
        # '— 2.35 s switch-in' appears mid-blurb in the real corpus; only a
        # match anchored at end of line is a guide id.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            guides = make_fixture(root)
            (guides / "SILENT-FAILURES.md").write_text(
                SILENT_FAILURES.replace(
                    "A trap that does not throw.",
                    "Switching re-prefills — 2.35 s measured.",
                ),
                encoding="utf-8",
            )
            self.build(root, guides)
            sliced = (
                root / "skills" / "apple-test-skill" / "references" / "SILENT-FAILURES.md"
            ).read_text(encoding="utf-8")
            self.assertIn("2.35 s measured", sliced)

    def test_skill_md_carries_the_full_evidence_legend(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            guides = make_fixture(root)
            self.build(root, guides)
            text = (root / "skills" / "apple-test-skill" / "SKILL.md").read_text(
                encoding="utf-8"
            )
            for marker in ("✅ **VERIFIED**", "🟡 **RECONSTRUCTED**", "🟠 **Suggestive**",
                           "🔴 **GAP**", "⚠️ **SILENT FAILURE**"):
                self.assertIn(marker, text, marker)

    def test_lifted_triage_rows_are_repointed_at_the_skill_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            guides = make_fixture(root)
            self.build(root, guides)
            text = (root / "skills" / "apple-test-skill" / "SKILL.md").read_text(
                encoding="utf-8"
            )
            # The row was authored relative to the part README; in SKILL.md a
            # bare 'references/01-map.md' would resolve to the wrong place.
            self.assertNotIn("](references/01-map.md)", text)
            self.assertIn("references/part-01-orientation/README.md", text)

    def test_refuses_a_manifest_that_leaves_a_part_unowned(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            guides = make_fixture(root)
            manifest = dict(SKILL_MANIFEST)
            manifest["skills"] = [dict(manifest["skills"][0], owns=[])]
            (root / "notes" / "skill-manifest.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            with self.assertRaises(builder.SkillError) as caught:
                self.build(root, guides)
            self.assertIn("not owned", str(caught.exception))

    def test_refuses_a_manifest_that_claims_a_reference_twice(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            guides = make_fixture(root)
            manifest = dict(SKILL_MANIFEST)
            first = manifest["skills"][0]
            manifest["skills"] = [first, dict(first, name="apple-other-skill")]
            (root / "notes" / "skill-manifest.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            with self.assertRaises(builder.SkillError) as caught:
                self.build(root, guides)
            self.assertIn("disjoint", str(caught.exception))

    def test_refuses_a_description_over_the_context_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            guides = make_fixture(root)
            manifest = dict(SKILL_MANIFEST)
            manifest["skills"] = [dict(manifest["skills"][0], description="x" * 1200)]
            (root / "notes" / "skill-manifest.json").write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            with self.assertRaises(builder.SkillError) as caught:
                self.build(root, guides)
            self.assertIn("budget", str(caught.exception))

    def test_refuses_an_unrecognized_part_heading(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            guides = make_fixture(root)
            path = guides / "part-01-orientation" / "README.md"
            path.write_text(
                PART_README.replace(
                    "## Reading order", "## Something nobody planned for"
                ),
                encoding="utf-8",
            )
            with self.assertRaises(builder.SkillError) as caught:
                self.build(root, guides)
            self.assertIn("unrecognized H2", str(caught.exception))

    def test_refuses_to_replace_a_tree_it_did_not_generate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            guides = make_fixture(root)
            (root / "skills").mkdir()
            (root / "skills" / "hand-written.md").write_text("mine\n", encoding="utf-8")
            with self.assertRaises(builder.SkillError) as caught:
                self.build(root, guides)
            self.assertIn("refusing to replace", str(caught.exception))
            self.assertTrue((root / "skills" / "hand-written.md").is_file())

    def test_regenerating_over_its_own_output_succeeds(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            guides = make_fixture(root)
            first = self.build(root, guides)
            second = self.build(root, guides)
            self.assertEqual(first["files"], second["files"])

    def test_skills_root_may_not_sit_inside_the_guides(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            guides = make_fixture(root)
            with self.assertRaises(builder.SkillError):
                self.build(root, guides, skills_root=guides / "skills")


class RenderingHelperTests(unittest.TestCase):
    def test_first_sentence_never_ends_inside_a_code_span(self):
        # These strings land in table cells; a dangling backtick makes GitHub run
        # the code span to the next backtick and eat the rest of the row.
        text = "Needs the Metal Toolchain, whose absence fails any build containing a `.aimodel` file"
        for limit in range(20, len(text) + 5):
            self.assertEqual(
                builder.first_sentence(text, limit).count("`") % 2, 0, f"limit={limit}"
            )

    def test_first_sentence_truncates_on_a_word_boundary(self):
        text = "the conceptual material starts at 26.0 and the introspection APIs are 26.4 of which"
        truncated = builder.first_sentence(text, 40)
        self.assertTrue(truncated.endswith(" …"), truncated)
        self.assertTrue(text.startswith(truncated[:-2].rstrip()), truncated)

    def test_first_sentence_leaves_short_text_alone(self):
        self.assertEqual(builder.first_sentence("Short `code` here."), "Short `code` here.")

    def test_owns_row_keeps_only_rows_citing_owned_guides(self):
        row = '| "x" | [16.1 §9](references/01-speech-analyzer-end-to-end.md) | why |'
        self.assertTrue(builder.owns_row(row, frozenset({1})))
        self.assertFalse(builder.owns_row(row, frozenset({2, 3, 4})))
        self.assertTrue(builder.owns_row(row, None))
        # A row citing no reference guide at all is a plain pointer; keep it.
        self.assertTrue(builder.owns_row('| "x" | Part 17 | why |', frozenset({2})))


class AnchorFidelityTests(unittest.TestCase):
    """Anchors for ⚠️ headings, pinned against GitHub's actual output.

    Checked on 2026-08-01 by reading the `user-content-` ids out of GitHub's own
    rendered HTML for
    guides/part-11-metal-and-tensorops/references/02-cooperative-tensors-and-flash-attention.md.
    All 79 anchors mdslug generated for that file appeared in GitHub's set, with
    zero mismatches. GitHub drops U+26A0 as a symbol and KEEPS its U+FE0F
    variation selector, which is a Unicode mark — so `#13--️-freshness-…` is
    correct and `#13--freshness-…` is not. Automated reviewers repeatedly claim
    the opposite; this test is the evidence.
    """

    CASES = {
        # heading text (verbatim from the guide) -> GitHub's rendered anchor
        "§13 — ⚠️ Freshness: NAX is new and still settling":
            "13--️-freshness-nax-is-new-and-still-settling",
        "§5.5 ⚠️ Cooperative tensors are not zero-initialised":
            "55-️-cooperative-tensors-are-not-zero-initialised",
        "§6.3 ⚠️ SILENT FAILURE — the identity default":
            "63-️-silent-failure--the-identity-default",
    }

    def test_warning_heading_anchors_match_github(self):
        mdslug = load_script("mdslug", "mdslug.py")
        for heading, expected in self.CASES.items():
            self.assertEqual(mdslug.slugify(heading), expected, heading)
            self.assertIn("️", mdslug.slugify(heading))


class FenceTrackingTests(unittest.TestCase):
    def test_an_info_string_line_does_not_close_an_open_fence(self):
        mdlinks = load_script("mdlinks", "mdlinks.py")
        text = "```markdown\n```swift\n[a](b.md)\n```\nafter\n"
        states = [fenced for _, _, fenced in mdlinks.iter_lines(text)]
        # Only the trailing 'after' is outside; the inner ```swift is content,
        # so the link-shaped line between them is never rewritten.
        self.assertEqual(states, [True, True, True, True, False])


class InlineScannerTests(unittest.TestCase):
    """The three ways a line can only look like it holds a link."""

    def setUp(self):
        self.mdlinks = load_script("mdlinks", "mdlinks.py")

    def rewrite(self, inner):
        return "REWRITTEN"

    def test_an_escaped_bracket_is_not_a_link(self):
        # A guide showing Markdown syntax literally: the brackets are displayed,
        # not linked, so the destination must survive untouched.
        line = r"Write it as \[example\](path.md) to show the syntax."
        self.assertEqual(self.mdlinks.scan_inline_links(line, self.rewrite), line)

    def test_an_escaped_backslash_still_leaves_a_real_link(self):
        # `\\` is an escaped backslash, so the `](` after it opens a real body.
        line = r"[text\\](path.md)"
        self.assertEqual(
            self.mdlinks.scan_inline_links(line, self.rewrite), r"[text\\](REWRITTEN)"
        )

    def test_a_code_span_open_on_a_previous_line_suppresses_rewriting(self):
        scanner = self.mdlinks.InlineScanner()
        first = scanner.scan("A span that opens here: `foo", self.rewrite)
        second = scanner.scan("](bar.md)` and closes on this line.", self.rewrite)
        self.assertEqual(first, "A span that opens here: `foo")
        self.assertEqual(second, "](bar.md)` and closes on this line.")
        # Closed now, so the next line is live again.
        self.assertEqual(scanner.scan("[t](x.md)", self.rewrite), "[t](REWRITTEN)")

    def test_a_blank_line_closes_an_unterminated_span(self):
        # A code span cannot cross a paragraph break, so an unclosed backtick
        # must not swallow the rest of the document.
        scanner = self.mdlinks.InlineScanner()
        scanner.scan("An unmatched ` backtick", self.rewrite)
        scanner.scan("", self.rewrite)
        self.assertEqual(scanner.scan("[t](x.md)", self.rewrite), "[t](REWRITTEN)")


class TriageRowOwnershipTests(unittest.TestCase):
    """A row citing one owned and one unowned guide stays, and stays remote."""

    ROW = (
        '| "My transcript is truncated" | [16.1 §9](references/01-speech.md) · '
        "[16.2 §3](references/02-intents.md) | Two causes |"
    )

    def test_a_mixed_row_is_kept_by_every_skill_that_owns_part_of_it(self):
        self.assertTrue(builder.owns_row(self.ROW, frozenset({1})))
        self.assertTrue(builder.owns_row(self.ROW, frozenset({2, 3, 4})))

    def test_a_row_citing_only_unowned_guides_is_dropped(self):
        self.assertFalse(builder.owns_row(self.ROW, frozenset({3, 5})))

    def test_a_row_citing_no_guide_is_always_kept(self):
        self.assertTrue(builder.owns_row("| Anything | See Part 2 | Why |", frozenset({1})))


class SkillVerifierTests(unittest.TestCase):
    def build_and_verify(self, root):
        guides = make_fixture(root)
        manifest = builder.build_skills(
            source_root=guides,
            skills_root=root / "skills",
            manifest_path=root / "notes" / "skill-manifest.json",
            repository_root=root,
            interfaces=root / "notes" / "sdk-interfaces",
        )
        path = root / "skills" / "skills-manifest.json"
        path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
        return verifier.verify(root / "skills", path)

    def test_accepts_a_freshly_generated_tree(self):
        with tempfile.TemporaryDirectory() as directory:
            summary = self.build_and_verify(Path(directory))
            self.assertEqual(summary["skills"], 1)
            self.assertGreater(summary["links"], 0)

    def test_rejects_a_link_that_escapes_the_skill_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.build_and_verify(root)
            skill = root / "skills" / "apple-test-skill"
            path = skill / "references" / "SECTION-MAPS.md"
            path.write_text(
                path.read_text(encoding="utf-8") + "\n[out](../../elsewhere.md)\n",
                encoding="utf-8",
            )
            with self.assertRaises(verifier.VerificationError) as caught:
                verifier.check_links(skill, "apple-test-skill")
            self.assertIn("escapes the skill root", str(caught.exception))

    def test_rejects_a_reference_style_link_that_escapes_the_skill_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.build_and_verify(root)
            skill = root / "skills" / "apple-test-skill"
            path = skill / "references" / "SECTION-MAPS.md"
            path.write_text(
                path.read_text(encoding="utf-8")
                + "\nSee [the notes][runbook].\n\n[runbook]: ../../../notes/x.md\n",
                encoding="utf-8",
            )
            with self.assertRaises(verifier.VerificationError) as caught:
                verifier.check_links(skill, "apple-test-skill")
            self.assertIn("escapes the skill root", str(caught.exception))

    def test_a_footnote_definition_is_not_read_as_a_reference_link(self):
        self.assertEqual(verifier.destinations("[^note]: just prose, not a link\n"), [])

    def test_rejects_a_fragment_with_no_matching_heading(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.build_and_verify(root)
            skill = root / "skills" / "apple-test-skill"
            path = skill / "references" / "SECTION-MAPS.md"
            path.write_text(
                path.read_text(encoding="utf-8")
                + "\n[bad](part-01-orientation/README.md#no-such-heading)\n",
                encoding="utf-8",
            )
            with self.assertRaises(verifier.VerificationError) as caught:
                verifier.check_links(skill, "apple-test-skill")
            self.assertIn("no matching anchor", str(caught.exception))

    def test_rejects_a_root_skill_md_that_would_vendor_the_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.build_and_verify(root)
            (root / "skills" / "SKILL.md").write_text("---\nname: x\n---\n", encoding="utf-8")
            with self.assertRaises(verifier.VerificationError) as caught:
                verifier.verify(root / "skills", root / "skills" / "skills-manifest.json")
            self.assertIn("shadow", str(caught.exception))

    def test_rejects_frontmatter_that_is_not_flat_scalars(self):
        with self.assertRaises(verifier.VerificationError):
            verifier.parse_frontmatter("---\nname: x\nnested:\n  a: 1\n---\nbody\n", "x")

    def test_the_frontmatter_budget_measures_the_rendered_block(self):
        # A description full of quotes renders longer than its decoded text, and
        # it is the rendered block the agent holds in context. Summing the
        # decoded fields would let this through.
        quoted = '"' * (verifier.MAX_FRONTMATTER_CHARS - 100)
        text = f'---\nname: x\ndescription: "{quoted.replace(chr(34), chr(92) + chr(34))}"\n---\nbody\n'
        fields, _, block = verifier.parse_frontmatter(text, "x")
        self.assertEqual(len(fields["description"]), verifier.MAX_FRONTMATTER_CHARS - 100)
        self.assertGreater(len(block), verifier.MAX_FRONTMATTER_CHARS)

    def test_anchor_set_covers_both_namespaces(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "page.md"
            path.write_text(
                '# T\n\n<a name="explicit"></a>\n\n## Dup\n\n## Dup\n\n'
                "```\n## Not a heading\n```\n",
                encoding="utf-8",
            )
            anchors = verifier.anchors_of(path)
            self.assertIn("explicit", anchors)
            self.assertIn("dup", anchors)
            self.assertIn("dup-1", anchors)
            self.assertNotIn("not-a-heading", anchors)


class CommittedSkillsTests(unittest.TestCase):
    """The committed tree must match a clean regeneration of the real corpus."""

    def test_committed_skills_match_clean_generation(self):
        manifest_path = SKILLS / "skills-manifest.json"
        self.assertTrue(manifest_path.is_file(), "run ./scripts/build-skills.sh")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        import datetime

        generated = datetime.date.fromisoformat(manifest["generated"])
        epoch = int(
            datetime.datetime.combine(
                generated, datetime.time(12), tzinfo=datetime.timezone.utc
            ).timestamp()
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "skills"
            result = subprocess.run(
                [
                    sys.executable, str(BUILD_SKILLS),
                    "--source", "guides",
                    "--skills", str(output),
                    "--manifest", str(MANIFEST),
                    "--repository-root", ".",
                ],
                cwd=REPO,
                env={**os.environ, "SOURCE_DATE_EPOCH": str(epoch)},
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            committed = {
                path.relative_to(SKILLS).as_posix()
                for path in SKILLS.rglob("*")
                if path.is_file()
            }
            fresh = {
                path.relative_to(output).as_posix()
                for path in output.rglob("*")
                if path.is_file()
            }
            # Set equality first: a per-file comparison alone never visits an
            # orphan left behind by a deleted guide.
            self.assertEqual(
                committed, fresh, "skills/ is stale; run ./scripts/build-skills.sh"
            )
            for relative in sorted(fresh):
                self.assertEqual(
                    (output / relative).read_bytes(),
                    (SKILLS / relative).read_bytes(),
                    f"skills/{relative} is stale; run ./scripts/build-skills.sh",
                )

    def test_committed_skills_pass_verification(self):
        expected = len(json.loads(MANIFEST.read_text(encoding="utf-8"))["skills"])
        summary = verifier.verify(SKILLS, SKILLS / "skills-manifest.json")
        self.assertEqual(summary["skills"], expected)

    def test_every_real_part_readme_parses(self):
        # The drift alarm: a guide edit that changes a part README's structure
        # must fail here, at the edit, rather than silently dropping a section
        # from a released skill.
        pages = builder.discover_pages(GUIDES)
        parts = [page for page in pages if page.role == "part"]
        self.assertEqual(len(parts), 17)
        for page in parts:
            router = builder.parse_part_readme(
                page, page.source.read_text(encoding="utf-8")
            )
            self.assertTrue(router.version_floor, page.relative)
            self.assertTrue(router.triage_rows, page.relative)
            references = sorted(
                other.guide for other in pages
                if other.role == "guide" and other.part == page.part
            )
            self.assertEqual(
                [card.guide for card in router.cards], references,
                f"{page.relative}: guide cards do not match its references/ directory",
            )

    def test_no_skill_cites_a_guide_it_does_not_own(self):
        # Three skills share part 16, so filtering by part rather than by guide
        # would point a reader at deep guides missing from their section map.
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        cited = re.compile(r"(?:^### |\[)(\d{1,2}\.\d{1,2})(?=[\] ])", re.M)
        pages = builder.discover_pages(GUIDES)
        for entry in manifest["skills"]:
            if entry.get("full_indexes"):
                continue
            owned = set()
            for owns in entry["owns"]:
                part = owns["part"]
                references = owns.get("references")
                if references is None:
                    owned.update(
                        f"{part}.{page.guide}"
                        for page in pages
                        if page.role == "guide" and page.part == part
                    )
                else:
                    owned.update(f"{part}.{number}" for number in references)
            skill = SKILLS / entry["name"]
            for name in ("API-INDEX.md", "SECTION-MAPS.md"):
                text = (skill / "references" / name).read_text(encoding="utf-8")
                for identifier in set(cited.findall(text)):
                    self.assertIn(
                        identifier, owned,
                        f"{entry['name']}/{name} cites unowned guide {identifier}",
                    )

    def test_discovery_matches_the_cli_two_level_walk(self):
        # `npx skills` walks skills/ two levels deep for SKILL.md and lets a
        # shallower hit shadow anything nested below it.
        found = sorted(
            path.parent.name
            for path in SKILLS.glob("*/SKILL.md")
        )
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.assertEqual(found, sorted(entry["name"] for entry in manifest["skills"]))
        self.assertEqual(list(SKILLS.glob("*/*/SKILL.md")), [])
        self.assertFalse((SKILLS / "SKILL.md").exists())
        self.assertFalse((REPO / "SKILL.md").exists())


if __name__ == "__main__":
    unittest.main()
