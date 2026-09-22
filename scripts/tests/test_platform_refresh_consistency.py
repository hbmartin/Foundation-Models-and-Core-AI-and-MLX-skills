from __future__ import annotations

import json
from datetime import date
from pathlib import Path
import re
import unittest
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[2]
GUIDES = ROOT / "guides"
FROZEN_NOEMA_URL = (
    "https://github.com/hbmartin/Foundation-Models-and-Core-AI-and-MLX-skills/"
    "blob/467d3cc496248af2928d92f8d330ba4a8457f0f8/notes/repos/noema-ios.md"
)


class PlatformRefreshConsistencyTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_image_tool_reverification_records_both_tool_runs(self) -> None:
        probes = self.read("probes/README.md")
        result = next(
            line for line in probes.splitlines()
            if "name=fm.attachment-label-recording" in line and "toolRan=true" in line
        )
        self.assertRegex(result, r"unlabeledTool=timeout\s+toolRan=true")
        self.assertRegex(result, r"labeledTool=timeout\s+toolRan=true")

    def test_large_overflow_uses_its_own_token_count(self) -> None:
        taxonomy = self.read(
            "guides/part-17-migration-from-pre-ios-27/"
            "references/03-error-taxonomy-migration.md"
        )
        stable_row = next(
            line for line in taxonomy.splitlines()
            if "Context overflow (stable macOS 27)" in line
        )
        self.assertIn("contextSizeExceeded(4096,168951)", stable_row)
        self.assertNotIn("4096,4099", stable_row)

        probes = self.read("probes/README.md")
        july = probes.split("## Results harvested 2026-07-31", 1)[1].split(
            "## Results harvested 2026-07-31, second pass", 1
        )[0]
        september = probes.split("## Results harvested 2026-09-16", 1)[1].split(
            "## Probe inventory", 1
        )[0]
        self.assertIn("168918", july)
        self.assertNotIn("168951", july)
        self.assertIn("168951", september)
        self.assertNotIn("168918", september)

    def test_full_snippet_run_date_is_not_later_than_the_snapshot(self) -> None:
        state = json.loads(self.read("notes/current-state.json"))
        verification = state["verification"]

        full_run = date.fromisoformat(verification["lastFullRun"])
        snapshot = date.fromisoformat(state["asOf"])
        self.assertLessEqual(full_run, snapshot)

    def test_active_guides_do_not_depend_on_removed_noema_checkout(self) -> None:
        offenders = []
        for path in GUIDES.rglob("*.md"):
            contents = path.read_text(encoding="utf-8")
            unavailable_sources = (
                "repos/noemaai-labs__noema-ios",
                "RuntimePerformance.md",
                "MultimodalPrompting.md",
                "DebuggingAndProfiling.md",
            )
            if any(source in contents for source in unavailable_sources):
                offenders.append(path.relative_to(ROOT).as_posix())
        self.assertEqual([], offenders)

    def test_frozen_noema_citations_use_immutable_links(self) -> None:
        citation_pattern = re.compile(r"\[[^]]+\]\(([^)\s]+)(?:\s+[^)]*)?\)")
        note = (ROOT / "notes/repos/noema-ios.md").resolve()
        guide_citations = []
        guide_offenders = []
        for path in GUIDES.rglob("*.md"):
            for destination in citation_pattern.findall(path.read_text(encoding="utf-8")):
                target = destination.partition("#")[0]
                if target.endswith("notes/repos/noema-ios.md"):
                    relative = path.relative_to(ROOT).as_posix()
                    guide_citations.append((relative, destination))
                    resolved = (path.parent / unquote(target)).resolve()
                    if "://" in target or resolved != note or not resolved.is_file():
                        guide_offenders.append((relative, destination))

        self.assertTrue(
            guide_citations, "expected at least one local citation to the frozen Noema note"
        )
        self.assertEqual([], guide_offenders)

        skill_citations = []
        skill_offenders = []
        for path in (ROOT / "skills").rglob("*.md"):
            for destination in citation_pattern.findall(path.read_text(encoding="utf-8")):
                target = destination.partition("#")[0]
                if target.endswith("notes/repos/noema-ios.md"):
                    relative = path.relative_to(ROOT).as_posix()
                    skill_citations.append((relative, destination))
                    if target != FROZEN_NOEMA_URL:
                        skill_offenders.append((relative, destination))
        self.assertTrue(
            skill_citations, "expected generated skills to cite the frozen Noema note"
        )
        self.assertEqual([], skill_offenders)

    def test_stable_fm_claims_point_to_the_canonical_surface(self) -> None:
        fm = self.read(
            "guides/part-05-prototyping-profiling-non-swift/"
            "references/02-fm-cli-and-python-sdk.md"
        )
        canonical_anchor = "#3--the-fm-help-surface-captured-on-macos-27"
        linked_files = (
            "notes/NEEDED-FROM-A-MACOS-27-MACHINE.md",
            "guides/part-01-orientation-and-gating/references/01-apple-ai-stack-2026-map.md",
            "guides/part-05-prototyping-profiling-non-swift/README.md",
            "guides/part-17-migration-from-pre-ios-27/references/01-what-changed-checklist.md",
            "notes/repos/issues-community-stack.md",
            "notes/synthesis/PROPOSED-GUIDE-TOPICS.md",
            "notes/synthesis/proposal-by-depth.md",
            "notes/synthesis/proposal-by-framework.md",
        )
        for relative in linked_files:
            self.assertIn(canonical_anchor, self.read(relative), relative)

    def test_retired_8192_claim_is_not_an_active_gap(self) -> None:
        files = (
            "guides/part-03-context-profiles-agentic/references/01-context-window-and-kv-cache.md",
            "guides/part-03-context-profiles-agentic/references/04-agentic-orchestration.md",
            "guides/part-17-migration-from-pre-ios-27/references/01-what-changed-checklist.md",
            "guides/part-17-migration-from-pre-ios-27/references/04-dual-sdk-builds.md",
        )
        for relative in files:
            contents = self.read(relative)
            self.assertRegex(contents, r"(?is)8192.{0,500}retired|retired.{0,500}8192")

        orchestration = self.read(
            "guides/part-03-context-profiles-agentic/references/04-agentic-orchestration.md"
        )
        source_entry_match = re.search(
            r"(?ms)^- \[frozen Noema 3\.5 snapshot\].*?(?=^\s*-\s|\Z)",
            orchestration,
        )
        self.assertIsNotNone(
            source_entry_match,
            "expected the frozen Noema source bullet in the orchestration guide",
        )
        source_entry = source_entry_match.group(0)
        self.assertIn("historical", source_entry.lower())
        self.assertIn("unreproduced", source_entry.lower())

    def test_current_runtime_claims_match_the_preserved_apple_pages(self) -> None:
        performance = self.read(
            "guides/part-05-prototyping-profiling-non-swift/"
            "references/01-playground-and-instruments.md"
        )
        readme = self.read("guides/part-05-prototyping-profiling-non-swift/README.md")
        orchestration = self.read(
            "guides/part-03-context-profiles-agentic/references/04-agentic-orchestration.md"
        )
        evidence = self.read(
            "notes/web/apple-foundation-models-runtime-performance-2026-09-22.md"
        )

        lane_section = performance.split("### 6.3 The six documented lanes", 1)[1].split(
            "\n---", 1
        )[0]
        for lane in (
            "Session",
            "Request",
            "Instructions",
            "Model Inference",
            "Tool",
            "Model Loading",
        ):
            self.assertIn(f"**{lane}**", lane_section)

        metric_section = performance.split("### 9.2 The four current token metrics", 1)[
            1
        ].split("### 9.3", 1)[0]
        for metric in (
            "Total Tokens",
            "Consumed Tokens",
            "Generated Tokens",
            "Cached Tokens",
        ):
            self.assertIn(f"**{metric}**", metric_section)
        self.assertNotIn("Reasoning Tokens", metric_section)
        self.assertIn("duration and output", performance)
        self.assertIn("cached input tokens ÷ total input tokens", performance)
        self.assertIn("cached input tokens ÷ total input tokens", orchestration)

        combined = "\n".join((performance, readme, orchestration))
        for contradiction in (
            "four of the six lane names are unknown",
            "The same retired summary reported two more inspector fields",
            "four token metrics reported by the retired summary",
            "runtime-performance article, via mirror",
        ):
            self.assertNotIn(contradiction, combined)
        for document in (performance, readme, orchestration):
            self.assertIn(
                "apple-foundation-models-runtime-performance-2026-09-22.md",
                document,
            )

        self.assertIn(
            "1dca2e84e0da356d5b61f04a9b720776e4df26610c3e7493b6e18fec14d73110",
            evidence,
        )
        self.assertIn(
            "3ce642e4e431912b276a1f4b7c9536d7d6d5b03ed8b9398f0301d601ca3bbde4",
            evidence,
        )

    def test_stated_noema_line_count_matches_the_frozen_snapshot(self) -> None:
        snapshot = self.read("notes/repos/noema-ios.md")
        line_count = len(snapshot.splitlines())
        self.assertEqual(2_225, line_count)

        mlx = self.read(
            "guides/part-13-mlx-swift/references/01-mlx-swift-lm-in-an-app.md"
        )
        entry = re.search(
            r"(?ms)^- \[`notes/repos/noema-ios\.md`\].*?(?=^\s*-\s|\Z)", mlx
        )
        self.assertIsNotNone(entry, "expected Noema research-note source entry")
        self.assertIn(f"{line_count:,} lines", entry.group(0))

    def test_historical_host_26_is_defined(self) -> None:
        probes = self.read("probes/README.md")
        definition = next(
            line for line in probes.splitlines() if "| **HISTORICAL HOST-26** |" in line
        )
        self.assertIn("archived", definition.lower())
        self.assertIn("macOS 26", definition)
        self.assertNotRegex(probes, r"(?<!HISTORICAL )HOST-26")

    def test_readme_callout_counts_match_generated_index(self) -> None:
        index = self.read("guides/SILENT-FAILURES.md")
        overview = self.read("guides/README.md")
        match = re.search(
            r"Every ⚠️ callout in the series — ([\d,]+) of them, "
            r"([\d,]+) describing a concrete silent failure",
            index,
        )
        self.assertIsNotNone(match)
        total, concrete = (f"{int(value.replace(',', '')):,}" for value in match.groups())
        self.assertIn(f"({total},\n  of which {concrete} describe", overview)


if __name__ == "__main__":
    unittest.main()
