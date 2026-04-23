import json
import subprocess
import sys
import tempfile
import textwrap
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
    workspace.joinpath("e2e_test_mutation.py").write_text(
        "def test_mutation_gate_smoke():\n    assert True\n",
        encoding="utf-8",
    )


def write_policy(
    workspace: Path,
    *,
    mode: str,
    command: list[str],
    threshold: int = 60,
    strict_threshold: int = 80,
    flaky_reruns: int = 0,
) -> None:
    policy = yaml.safe_load((ROOT / "presets" / "base" / "policy.yml").read_text(encoding="utf-8"))
    mutation = policy.setdefault("quality", {}).setdefault("mutation_testing", {})
    mutation["enabled"] = True
    mutation["mode"] = mode
    mutation["runner"] = "generic"
    mutation["command"] = command
    mutation["threshold"] = threshold
    mutation["strict_threshold"] = strict_threshold
    mutation["flaky_reruns"] = flaky_reruns
    mutation["events"] = ["after_implement"]
    mutation["exit_code_signals"] = "report"
    target = workspace / ".specify" / "policy.yml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(policy, sort_keys=False), encoding="utf-8")


def mutation_command(statuses: list[str]) -> list[str]:
    mutants = []
    for idx, status in enumerate(statuses, start=1):
        mutants.append(
            {
                "id": f"m-{idx}",
                "mutatorName": "ReturnValue",
                "location": {"file": "src/service.py", "line": 10 + idx, "column": None},
                "status": status,
                "replacement": None,
                "killedBy": [],
                "coveredBy": [],
                "duration": None,
            }
        )
    payload = {"schemaVersion": "1.0", "mutants": mutants}
    script = f"import json; payload = {payload!r}; print(json.dumps(payload))"
    return [sys.executable, "-c", script]


def flaky_mutation_command() -> list[str]:
    script = textwrap.dedent(
        """
        import json
        from pathlib import Path

        state_file = Path(".mutation-flaky-state")
        count = int(state_file.read_text()) if state_file.exists() else 0
        count += 1
        state_file.write_text(str(count))
        status = "Survived" if count == 1 else "Killed"
        payload = {
            "schemaVersion": "1.0",
            "mutants": [
                {
                    "id": "flaky-1",
                    "mutatorName": "BooleanReturn",
                    "location": {"file": "src/flaky.py", "line": 5, "column": None},
                    "status": status,
                    "replacement": None,
                    "killedBy": [],
                    "coveredBy": [],
                    "duration": None,
                }
            ],
        }
        print(json.dumps(payload))
        """
    )
    return [sys.executable, "-c", script]


class MutationWaveGTests(unittest.TestCase):
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
                "mutation",
                "--json",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_after_implement_advisory_threshold_breach_is_tier1(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws)
            write_e2e_test(ws)
            write_policy(ws, mode="advisory", command=mutation_command(["Survived", "Killed"]))

            result = self.run_orchestrator(ws)

            self.assertEqual(result.returncode, 0)
            self.assertIn("Non-critical failures", result.stdout)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertTrue(feedback.exists())
            body = feedback.read_text(encoding="utf-8")
            self.assertIn("mutation-score-below-threshold", body)
            self.assertIn("mutation-survived", body)
            report = ws / ".specify" / "context" / "mutation-report.json"
            summary = ws / ".specify" / "context" / "mutation-summary.md"
            self.assertTrue(report.exists())
            self.assertTrue(summary.exists())

    def test_after_implement_strict_threshold_breach_is_tier2(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws)
            write_e2e_test(ws)
            write_policy(ws, mode="strict", command=mutation_command(["Survived"]), strict_threshold=80)

            result = self.run_orchestrator(ws)

            self.assertEqual(result.returncode, 1)
            self.assertIn("Critical gate failure", result.stderr)

    def test_mutation_baseline_update_demotes_preexisting_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws)
            write_e2e_test(ws)
            write_policy(ws, mode="strict", command=mutation_command(["Survived"]), strict_threshold=80)

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

    def test_flaky_reruns_tag_flaky_and_exclude_from_score(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws)
            write_e2e_test(ws)
            write_policy(
                ws,
                mode="advisory",
                command=flaky_mutation_command(),
                threshold=80,
                flaky_reruns=1,
            )

            result = self.run_orchestrator(ws)

            self.assertEqual(result.returncode, 0)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertFalse(feedback.exists())
            report = json.loads((ws / ".specify" / "context" / "mutation-report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["flakyExcluded"], 1)
            self.assertEqual(report["mutants"][0]["statusReason"], "flaky")
            self.assertEqual(report["score"]["total"], 0)


if __name__ == "__main__":
    unittest.main()
