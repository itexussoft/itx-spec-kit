import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
EXT_ROOT = ROOT / "extensions" / "itx-brownfield-workflows"


class BrownfieldExtensionCommandTests(unittest.TestCase):
    def _load_extension(self) -> dict:
        return yaml.safe_load((EXT_ROOT / "extension.yml").read_text(encoding="utf-8"))

    def _load_command_text(self, stem: str) -> str:
        return (EXT_ROOT / "commands" / f"{stem}.md").read_text(encoding="utf-8")

    def test_extension_declares_expected_workflow_root_commands(self):
        data = self._load_extension()
        commands = data["provides"]["commands"]
        names = [entry["name"] for entry in commands]
        self.assertEqual(
            names,
            [
                "speckit.bugfix",
                "speckit.refactor",
                "speckit.modify",
                "speckit.hotfix",
                "speckit.deprecate",
            ],
        )

    def test_commands_are_brownfield_intake_commands_with_plan_handoff(self):
        for stem in ("bugfix", "refactor", "modify", "hotfix", "deprecate"):
            with self.subTest(command=stem):
                text = self._load_command_text(stem)
                self.assertIn("## User Input", text)
                self.assertIn("$ARGUMENTS", text)
                self.assertIn("intake entry point", text)
                self.assertIn("workflow-state.yml", text)
                self.assertIn("workstream_id", text)
                self.assertIn("artifact_root", text)
                self.assertIn("/speckit.plan", text)
                self.assertIn("/speckit.tasks", text)
                self.assertIn("/speckit.implement", text)
                self.assertNotIn("replaces `/speckit.plan`", text)

    def test_workflow_docs_explain_brownfield_intake_routes_into_core_plan(self):
        doc = (ROOT / "presets" / "base" / "docs" / "workflow-and-gates.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Brownfield flow", doc)
        self.assertIn("do not replace `/speckit.plan`", doc)
        self.assertIn("workstream metadata", doc)

    def test_readme_documents_brownfield_intake_behavior(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("brownfield intake commands", readme)
        self.assertIn("workstream metadata", readme)
        self.assertIn("/speckit.plan", readme)
        self.assertIn("not guaranteed upstream core commands", readme)
        self.assertNotIn("/speckit.review_run", readme)
        self.assertNotIn("/speckit.cleanup_run", readme)


if __name__ == "__main__":
    unittest.main()
