from __future__ import annotations

import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
GUIDES = ROOT / "guides"


class PlatformRefreshConsistencyTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (ROOT / relative).read_text(encoding="utf-8")

    def test_image_tool_reverification_is_not_described_as_drift(self) -> None:
        guide = self.read(
            "guides/part-02-foundation-models-everyday-api/"
            "references/05-image-input-and-attachments.md"
        )
        router = self.read("guides/part-02-foundation-models-everyday-api/README.md")
        probes = self.read("probes/README.md")

        self.assertNotIn("where both generic tool turns completed", guide)
        self.assertNotIn("had completed those generic tool turns", router)
        self.assertIn("unlabeledTool=timeout toolRan=true labeledTool=timeout toolRan=true", probes)

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

    def test_full_snippet_run_date_precedes_blocked_refresh(self) -> None:
        state = json.loads(self.read("notes/current-state.json"))
        verification = state["verification"]

        self.assertEqual("2026-08-17", verification["lastFullRun"])
        self.assertIn("Xcode", verification["blocker"])
        self.assertIn("26", verification["blocker"])
        self.assertNotEqual(state["asOf"], verification["lastFullRun"])

    def test_active_guides_do_not_depend_on_removed_noema_checkout(self) -> None:
        offenders = []
        for path in GUIDES.rglob("*.md"):
            if "repos/noemaai-labs__noema-ios" in path.read_text(encoding="utf-8"):
                offenders.append(path.relative_to(ROOT).as_posix())
        self.assertEqual([], offenders)

    def test_stable_fm_claims_point_to_the_canonical_surface(self) -> None:
        fm = self.read(
            "guides/part-05-prototyping-profiling-non-swift/"
            "references/02-fm-cli-and-python-sdk.md"
        )
        stale_claims = (
            "Interactive, has a model switch. macOS 27 only.",
            "PCC from Python means shelling out to `fm`.",
            "Use `fm` / `fm serve`.",
        )
        for claim in stale_claims:
            self.assertNotIn(claim, fm)

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
            self.assertNotIn("8192 claim remains uncorroborated", contents, relative)
            self.assertNotIn("uncorroborated, not disproved", contents, relative)
            self.assertRegex(contents, r"(?is)8192.{0,500}retired|retired.{0,500}8192")

    def test_historical_host_26_is_defined(self) -> None:
        probes = self.read("probes/README.md")
        definition = "| **HISTORICAL HOST-26** | archived macOS 26.x observations"
        self.assertIn(definition, probes)
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
