import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ORCH = ROOT / "extensions" / "itx-gates" / "hooks" / "orchestrator.py"
GATECTL = ROOT / "extensions" / "itx-gates" / "hooks" / "gatectl.py"


def write_config(workspace: Path, *, hook_mode: str = "hybrid") -> None:
    workspace.joinpath(".itx-config.yml").write_text(
        "\n".join(
            [
                'domain: "base"',
                'execution_mode: "mcp"',
                f'hook_mode: "{hook_mode}"',
                "knowledge:",
                '  mode: "eager"',
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_config_with_auto_retry(workspace: Path, *, max_attempts: int, hook_mode: str = "hybrid") -> None:
    workspace.joinpath(".itx-config.yml").write_text(
        "\n".join(
            [
                'domain: "base"',
                'execution_mode: "mcp"',
                f'hook_mode: "{hook_mode}"',
                "knowledge:",
                '  mode: "eager"',
                "gate:",
                "  auto_retry:",
                f"    max_attempts: {max_attempts}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_policy(workspace: Path) -> None:
    policy_src = ROOT / "presets" / "base" / "policy.yml"
    dest = workspace / ".specify" / "policy.yml"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(policy_src.read_text(encoding="utf-8"), encoding="utf-8")


def write_valid_plan(workspace: Path) -> Path:
    plan_dir = workspace / "specs" / "feature-a"
    plan_dir.mkdir(parents=True, exist_ok=True)
    plan_path = plan_dir / "system-design-plan.md"
    plan_path.write_text(
        "\n".join(
            [
                "# Plan",
                "## 4. Architectural Patterns Applied",
                "- Domain-Driven Design with explicit bounded contexts",
                "## 4b. Code-Level Design Patterns Applied",
                "- Command + Handler and Value Objects are required for this feature",
                "## 5. DDD Aggregates",
                "- Order aggregate with transition invariants",
                "## 13. Test Strategy",
                "- E2E: place order journey with DB + event assertions",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return plan_path


class ItxGatesRuntimeStateTests(unittest.TestCase):
    def run_orchestrator(self, workspace: Path, event: str, *, json_mode: bool = False) -> subprocess.CompletedProcess[str]:
        cmd = ["python3", str(ORCH), "--event", event, "--workspace", str(workspace)]
        if json_mode:
            cmd.append("--json")
        return subprocess.run(cmd, check=False, capture_output=True, text=True)

    def run_gatectl(self, workspace: Path, event: str, *, json_mode: bool = False, force: bool = False) -> subprocess.CompletedProcess[str]:
        cmd = ["python3", str(GATECTL), "ensure", "--event", event, "--workspace", str(workspace)]
        if json_mode:
            cmd.append("--json")
        if force:
            cmd.append("--force")
        return subprocess.run(cmd, check=False, capture_output=True, text=True)

    def test_after_plan_json_output_writes_gate_state_and_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws)
            write_policy(ws)
            write_valid_plan(ws)

            result = self.run_orchestrator(ws, "after_plan", json_mode=True)

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["event"], "after_plan")
            self.assertEqual(payload["status"], "passed")
            self.assertEqual(payload["tier1_count"], 0)
            self.assertEqual(payload["tier2_count"], 0)

            gate_state = ws / ".specify" / "context" / "gate-state.yml"
            summary = ws / ".specify" / "context" / "last-gate-summary.md"
            self.assertTrue(gate_state.exists())
            self.assertTrue(summary.exists())

            state = yaml.safe_load(gate_state.read_text(encoding="utf-8"))
            self.assertEqual(state["event"], "after_plan")
            self.assertEqual(state["status"], "passed")
            self.assertGreaterEqual(len(state["input_artifacts"]), 2)
            self.assertIn("Status: `passed`", summary.read_text(encoding="utf-8"))

    def test_after_plan_tier1_writes_machine_readable_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws)
            write_policy(ws)

            result = self.run_orchestrator(ws, "after_plan", json_mode=True)

            self.assertEqual(result.returncode, 0)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "tier1")
            self.assertGreaterEqual(payload["tier1_count"], 1)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            gate_state = ws / ".specify" / "context" / "gate-state.yml"
            self.assertTrue(feedback.exists())
            self.assertTrue(gate_state.exists())

    def test_gatectl_skips_when_gate_state_is_fresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws)
            write_policy(ws)
            write_valid_plan(ws)

            first = self.run_gatectl(ws, "after_plan")
            self.assertEqual(first.returncode, 0, msg=first.stderr)
            second = self.run_gatectl(ws, "after_plan", json_mode=True)

            self.assertEqual(second.returncode, 0, msg=second.stderr)
            payload = json.loads(second.stdout)
            self.assertEqual(payload["action"], "skipped-fresh")
            self.assertTrue(payload["fresh"])

    def test_gatectl_reruns_when_inputs_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws)
            write_policy(ws)
            plan_path = write_valid_plan(ws)

            self.assertEqual(self.run_gatectl(ws, "after_plan").returncode, 0)
            plan_path.write_text(plan_path.read_text(encoding="utf-8") + "\n<!-- changed -->\n", encoding="utf-8")

            rerun = self.run_gatectl(ws, "after_plan", json_mode=True)

            self.assertEqual(rerun.returncode, 0, msg=rerun.stderr)
            payload = json.loads(rerun.stdout)
            self.assertEqual(payload["action"], "executed")
            self.assertFalse(payload["fresh_before_run"])
            self.assertEqual(payload["freshness_reason"], "inputs-changed")
            self.assertEqual(payload["status"], "passed")

    def test_gatectl_after_implement_tier1_writes_failure_report_and_retry_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws)
            write_policy(ws)

            result = self.run_gatectl(ws, "after_implement", json_mode=True, force=True)

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "tier1")
            self.assertTrue(payload["retry_requested"])
            self.assertEqual(payload["auto_retry_attempt"], 1)
            report = ws / payload["gate_failure_report_path"]
            self.assertTrue(report.exists())
            self.assertIn("<SYSTEM_CORRECTION>", report.read_text(encoding="utf-8"))

    def test_gatectl_after_implement_auto_retry_exhausts_and_requires_human(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config_with_auto_retry(ws, max_attempts=1)
            write_policy(ws)

            first = self.run_gatectl(ws, "after_implement", json_mode=True, force=True)
            self.assertEqual(first.returncode, 0, msg=first.stderr)
            first_payload = json.loads(first.stdout)
            self.assertTrue(first_payload["retry_requested"])
            self.assertFalse(first_payload["human_action_required"])

            second = self.run_gatectl(ws, "after_implement", json_mode=True, force=True)
            self.assertEqual(second.returncode, 0, msg=second.stderr)
            second_payload = json.loads(second.stdout)
            self.assertFalse(second_payload["retry_requested"])
            self.assertTrue(second_payload["human_action_required"])
            self.assertEqual(second_payload["auto_retry_attempt"], 2)


if __name__ == "__main__":
    unittest.main()
