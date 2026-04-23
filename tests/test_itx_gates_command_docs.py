import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
COMMANDS_ROOT = ROOT / "extensions" / "itx-gates" / "commands"
CURSOR_RULE = ROOT / "presets" / "base" / "cursor-rules" / "itx-speckit-commands.mdc"


def _split_frontmatter(markdown: str) -> tuple[dict, str]:
    if not markdown.startswith("---\n"):
        return {}, markdown
    _, _, rest = markdown.partition("---\n")
    raw_frontmatter, sep, body = rest.partition("\n---\n")
    if not sep:
        return {}, markdown
    data = yaml.safe_load(raw_frontmatter) or {}
    return data if isinstance(data, dict) else {}, body


class ItxGatesCommandDocsTests(unittest.TestCase):
    def _load_command(self, name: str) -> tuple[dict, str]:
        markdown = (COMMANDS_ROOT / f"{name}.md").read_text(encoding="utf-8")
        return _split_frontmatter(markdown)

    def test_after_gate_commands_define_script_frontmatter(self):
        expected_events = {
            "after_plan": "after_plan",
            "after_tasks": "after_tasks",
            "after_implement": "after_implement",
            "after_review": "after_review",
        }
        for command_name, event_name in expected_events.items():
            with self.subTest(command=command_name):
                frontmatter, body = self._load_command(command_name)
                scripts = frontmatter.get("scripts")
                self.assertIsInstance(scripts, dict)
                sh = scripts.get("sh")
                self.assertIsInstance(sh, str)
                self.assertIn("hooks/gatectl.py ensure", sh)
                self.assertIn(f"--event {event_name}", sh)
                self.assertIn("{SCRIPT}", body)

    def test_after_gate_commands_document_exit_code_interpretation_and_artifacts(self):
        for command_name in ("after_plan", "after_tasks", "after_implement", "after_review"):
            with self.subTest(command=command_name):
                _, body = self._load_command(command_name)
                self.assertIn("Exit `0`", body)
                self.assertIn("Exit `1`", body)
                self.assertIn(".specify/context/gate_feedback.md", body)
                self.assertIn(".specify/context/gate-state.yml", body)
                self.assertIn(".specify/context/gate-events.jsonl", body)
                self.assertIn(".specify/context/last-gate-summary.md", body)

    def test_cursor_rule_requires_manual_gate_invocation_when_hooks_are_not_auto_fired(self):
        text = CURSOR_RULE.read_text(encoding="utf-8")
        self.assertIn("does **not** auto-run extension hooks", text)
        self.assertIn("After `/speckit.plan` -> run `after_plan`", text)
        self.assertIn("After `/speckit.tasks` -> run `after_tasks`", text)
        self.assertIn("After `/speckit.implement` -> run `after_implement`", text)
        self.assertIn("After review completion", text)
        self.assertIn(".specify/context/gate_feedback.md", text)
        self.assertIn(".specify/context/execution-brief.md", text)


if __name__ == "__main__":
    unittest.main()
