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


def write_config(workspace: Path) -> None:
    workspace.joinpath(".itx-config.yml").write_text(
        "\n".join(
            [
                'domain: "base"',
                'execution_mode: "mcp"',
                'hook_mode: "hybrid"',
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_e2e_test(workspace: Path) -> None:
    workspace.joinpath("e2e_test_architecture.py").write_text(
        "def test_architecture_gate_smoke():\n    assert True\n",
        encoding="utf-8",
    )


def write_policy(
    workspace: Path,
    *,
    mode: str,
    command: list[str],
    parse: dict | None = None,
    fail_on_unmapped: bool = False,
) -> None:
    policy = yaml.safe_load((ROOT / "presets" / "base" / "policy.yml").read_text(encoding="utf-8"))
    architecture = policy.setdefault("quality", {}).setdefault("architecture", {})
    architecture["enabled"] = True
    architecture["mode"] = mode
    architecture["runner"] = "generic"
    architecture["command"] = command
    architecture["events"] = ["after_implement"]
    architecture["parse"] = parse
    architecture["fail_on_unmapped_violation"] = fail_on_unmapped
    architecture["exit_code_signals"] = "report"
    target = workspace / ".specify" / "policy.yml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(policy, sort_keys=False), encoding="utf-8")


def sarif_command(rule_id: str, message: str) -> list[str]:
    payload = {
        "version": "2.1.0",
        "runs": [
            {
                "results": [
                    {
                        "ruleId": rule_id,
                        "level": "warning",
                        "message": {"text": message},
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {"uri": "src/service.py"},
                                    "region": {"startLine": 12},
                                }
                            }
                        ],
                    }
                ]
            }
        ],
    }
    script = f"import json; print(json.dumps({json.dumps(payload)}))"
    return [sys.executable, "-c", script]


def json_command() -> list[str]:
    payload = {
        "summary": {
            "violations": [
                {
                    "rule": {"name": "layer-violation", "severity": "error"},
                    "from": "src/domain/service.py",
                    "comment": "Forbidden import from infrastructure layer.",
                    "line": 33,
                }
            ]
        }
    }
    script = f"import json; print(json.dumps({json.dumps(payload)}))"
    return [sys.executable, "-c", script]


class ArchitectureWaveFTests(unittest.TestCase):
    def run_orchestrator(self, workspace: Path, event: str = "after_implement") -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(ORCH), "--event", event, "--workspace", str(workspace)],
            check=False,
            capture_output=True,
            text=True,
        )

    def run_gatectl_baseline_update(self, workspace: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(GATECTL),
                "baseline-update",
                "--workspace",
                str(workspace),
                "--kind",
                "architecture",
                "--json",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_after_implement_advisory_architecture_finding_is_tier1(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws)
            write_e2e_test(ws)
            write_policy(ws, mode="advisory", command=sarif_command("cycle-detected", "Dependency cycle found."))

            result = self.run_orchestrator(ws)

            self.assertEqual(result.returncode, 0)
            self.assertIn("Non-critical failures", result.stdout)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertTrue(feedback.exists())
            self.assertIn("architecture-cycle-detected", feedback.read_text(encoding="utf-8"))
            report = ws / ".specify" / "context" / "architecture-report.json"
            self.assertTrue(report.exists())
            payload = json.loads(report.read_text(encoding="utf-8"))
            self.assertEqual(payload["version"], "2.1.0")

    def test_after_implement_strict_architecture_finding_is_tier2(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws)
            write_e2e_test(ws)
            write_policy(ws, mode="strict", command=sarif_command("layer-violation", "Layer rule broken."))

            result = self.run_orchestrator(ws)

            self.assertEqual(result.returncode, 1)
            self.assertIn("Critical gate failure", result.stderr)

    def test_strict_finding_demoted_after_baseline_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws)
            write_e2e_test(ws)
            write_policy(ws, mode="strict", command=sarif_command("layer-violation", "Layer rule broken."))

            first = self.run_orchestrator(ws)
            self.assertEqual(first.returncode, 1)

            baseline = self.run_gatectl_baseline_update(ws)
            self.assertEqual(baseline.returncode, 0, msg=baseline.stderr)
            payload = json.loads(baseline.stdout)
            self.assertEqual(payload["status"], "updated")
            self.assertGreaterEqual(payload["fingerprint_count"], 1)

            second = self.run_orchestrator(ws)
            self.assertEqual(second.returncode, 0)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertTrue(feedback.exists())
            self.assertIn("[pre-existing]", feedback.read_text(encoding="utf-8"))

    def test_generic_json_mapping_parses_violation(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws)
            write_e2e_test(ws)
            parse = {
                "format": "json",
                "iterate": "$.summary.violations[*]",
                "map": {
                    "rule_id": "rule.name",
                    "severity": "rule.severity",
                    "file": "from",
                    "message": "comment",
                    "line": "line",
                },
            }
            write_policy(ws, mode="advisory", command=json_command(), parse=parse)

            result = self.run_orchestrator(ws)

            self.assertEqual(result.returncode, 0)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertTrue(feedback.exists())
            self.assertIn("architecture-layer-violation", feedback.read_text(encoding="utf-8"))

    def test_baseline_update_fails_when_report_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws)
            (ws / ".specify" / "context").mkdir(parents=True, exist_ok=True)

            result = self.run_gatectl_baseline_update(ws)

            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "missing-report")


if __name__ == "__main__":
    unittest.main()

