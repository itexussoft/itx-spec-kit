import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / "extensions" / "itx-gates" / "hooks"
sys.path.insert(0, str(HOOKS))

from orchestrator_brief import _generate_execution_brief  # noqa: E402
from smell_mapping import guidance_from_gate_feedback, map_rule_to_smell, reverse_index_for_workspace  # noqa: E402


def _write_plan(workspace: Path) -> None:
    plan = workspace / "specs" / "feature-a" / "system-design-plan.md"
    plan.parent.mkdir(parents=True, exist_ok=True)
    plan.write_text(
        "\n".join(
            [
                "# Plan",
                "",
                "## 1. Problem Statement",
                "Reduce complexity in processing flow.",
                "",
                "## 2. Files / Modules Affected",
                "- `src/service.py`",
                "",
                "## 13. Test Strategy",
                "- Run unit tests and gate checks.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _write_smell_catalog(workspace: Path) -> None:
    target = workspace / ".specify" / "smell-catalog.yml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text((ROOT / "presets" / "base" / "smell-catalog.yml").read_text(encoding="utf-8"), encoding="utf-8")


class SmellMappingWaveH1Tests(unittest.TestCase):
    def test_reverse_index_contains_curated_detector_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            _write_smell_catalog(ws)

            reverse_index = reverse_index_for_workspace(ws)

            self.assertEqual(reverse_index.get("java:s138"), "LONG_METHOD")
            self.assertEqual(reverse_index.get("r0913"), "DATA_CLUMPS")

    def test_map_rule_to_smell_resolves_detector_rule(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            _write_smell_catalog(ws)

            smell = map_rule_to_smell(ws, "java:S138")

            self.assertIsNotNone(smell)
            assert smell is not None
            self.assertEqual(smell.get("id"), "LONG_METHOD")

    def test_unknown_smell_rule_falls_back_to_catalog_pointer(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            _write_smell_catalog(ws)
            gate_feedback = (
                "# Gate Feedback\n\n"
                "## Finding 1\n"
                "- Severity: `tier1`\n"
                "- Rule: `smell-unknown`\n"
                "- Retry: `1 / 3`\n"
                "- Message: Unmapped smell.\n"
            )

            guidance = guidance_from_gate_feedback(ws, gate_feedback)

            self.assertEqual(len(guidance), 1)
            self.assertIn("refactoring.com/catalog", guidance[0])

    def test_execution_brief_includes_smell_guidance_when_findings_are_mapped(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            _write_plan(ws)
            _write_smell_catalog(ws)
            context = ws / ".specify" / "context"
            context.mkdir(parents=True, exist_ok=True)
            (context / "gate_feedback.md").write_text(
                "\n".join(
                    [
                        "# Gate Feedback",
                        "",
                        "## Finding 1",
                        "- Severity: `tier1`",
                        "- Rule: `java:S138`",
                        "- Retry: `1 / 3`",
                        "- Message: Long method detected.",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            policy = yaml.safe_load((ROOT / "presets" / "base" / "policy.yml").read_text(encoding="utf-8"))
            config = {"domain": "base", "knowledge": {"mode": "eager"}}
            _generate_execution_brief(ws, config, policy)

            brief_text = (context / "execution-brief.md").read_text(encoding="utf-8")
            self.assertIn("## Smell Guidance", brief_text)
            self.assertIn("Long Method", brief_text)

    def test_execution_brief_omits_smell_guidance_when_no_mapped_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            _write_plan(ws)
            _write_smell_catalog(ws)
            context = ws / ".specify" / "context"
            context.mkdir(parents=True, exist_ok=True)
            (context / "gate_feedback.md").write_text(
                "\n".join(
                    [
                        "# Gate Feedback",
                        "",
                        "## Finding 1",
                        "- Severity: `tier1`",
                        "- Rule: `architecture-layer-violation`",
                        "- Retry: `1 / 3`",
                        "- Message: Layer violation reported.",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            policy = yaml.safe_load((ROOT / "presets" / "base" / "policy.yml").read_text(encoding="utf-8"))
            config = {"domain": "base", "knowledge": {"mode": "eager"}}
            _generate_execution_brief(ws, config, policy)

            brief_text = (context / "execution-brief.md").read_text(encoding="utf-8")
            self.assertNotIn("## Smell Guidance", brief_text)


if __name__ == "__main__":
    unittest.main()
