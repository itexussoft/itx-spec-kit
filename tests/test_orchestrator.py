import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
ORCH = ROOT / "extensions" / "itx-gates" / "hooks" / "orchestrator.py"


def write_config(
    workspace: Path,
    domain: str,
    execution_mode: str = "mcp",
    knowledge_mode: str | None = None,
) -> None:
    lines = [
        f'domain: "{domain}"',
        f'execution_mode: "{execution_mode}"',
    ]
    if knowledge_mode:
        lines.extend(
            [
                "knowledge:",
                f'  mode: "{knowledge_mode}"',
            ]
        )
    lines.extend(
        [
            "docker:",
            '  container_name: "sandbox"',
            "",
        ]
    )
    workspace.joinpath(".itx-config.yml").write_text("\n".join(lines), encoding="utf-8")


def write_config_without_container(workspace: Path, domain: str, execution_mode: str = "docker-fallback") -> None:
    workspace.joinpath(".itx-config.yml").write_text(
        "\n".join(
            [
                f'domain: "{domain}"',
                f'execution_mode: "{execution_mode}"',
                "docker: {}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_policy(workspace: Path) -> None:
    """Install the shared policy.yml into the workspace."""
    policy_src = ROOT / "presets" / "base" / "policy.yml"
    dest = workspace / ".specify" / "policy.yml"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if policy_src.exists():
        dest.write_text(policy_src.read_text(encoding="utf-8"), encoding="utf-8")


def write_workflow_state_feature(workspace: Path, feature: str) -> None:
    state_path = workspace / ".specify" / "context" / "workflow-state.yml"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        "\n".join(
            [
                f'feature: "{feature}"',
                'current_phase: "tasks"',
                "phases:",
                "  tasks:",
                "    status: in_progress",
                "",
            ]
        ),
        encoding="utf-8",
    )


def write_e2e_test(workspace: Path, name: str = "e2e_test_orders.py", with_assertion: bool = True) -> Path:
    content = "def test_order_flow():\n    assert True\n" if with_assertion else "def test_order_flow():\n    pass\n"
    target = workspace / name
    target.write_text(content, encoding="utf-8")
    return target


class OrchestratorTests(unittest.TestCase):
    def run_gate(self, workspace: Path, event: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["python3", str(ORCH), "--event", event, "--workspace", str(workspace)],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_after_tasks_missing_task_file_returns_tier1_continue(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            result = self.run_gate(ws, "after_tasks")
            self.assertEqual(result.returncode, 0)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertTrue(feedback.exists())

    def test_after_tasks_refactor_plan_without_tasks_is_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            (ws / "specs" / "feature-r").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-r" / "refactor-plan.md").write_text(
                "\n".join(
                    [
                        "---",
                        "work_class: refactor",
                        "---",
                        "# Refactor plan",
                        "## 1. Goal",
                        "Improve internal module boundaries without changing behavior.",
                        "## 2. Scope / Non-Scope",
                        "- In scope: service-layer extraction",
                        "- Out of scope: API contract changes",
                        "## 3. Invariants to Preserve",
                        "- Public API response shape remains unchanged",
                        "## 4. Public Contract Impact",
                        "None",
                        "## 5. Behavioral Equivalence Strategy",
                        "- Compare baseline integration outputs before/after",
                        "## 6. Regression Strategy",
                        "- Add integration regression for order orchestration path",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_tasks")
            self.assertEqual(result.returncode, 0)
            self.assertIn("Gates passed", result.stdout)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            if feedback.exists():
                self.assertNotIn("tasks-presence", feedback.read_text(encoding="utf-8"))

    def test_after_tasks_bugfix_report_without_tasks_is_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            (ws / "specs" / "feature-b").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-b" / "bugfix-report.md").write_text(
                "\n".join(
                    [
                        "---",
                        "work_class: bugfix",
                        "---",
                        "# Bugfix report",
                        "## 1. Symptom",
                        "- Checkout endpoint intermittently returns 500.",
                        "## 2. Reproduction",
                        "1. Create cart with expired promo token",
                        "2. Submit checkout request",
                        "3. Observe 500 response",
                        "## 3. Expected Behavior",
                        "- Endpoint returns 400 with structured validation error.",
                        "## 4. Regression Test Target",
                        "- Add integration test for expired promo checkout path",
                        "## 5. Root Cause",
                        "- Null handling gap in promo validator",
                        "## 6. Fix Strategy",
                        "- Guard null token state and return domain validation error",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_tasks")
            self.assertEqual(result.returncode, 0)
            self.assertIn("Gates passed", result.stdout)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            if feedback.exists():
                self.assertNotIn("tasks-presence", feedback.read_text(encoding="utf-8"))

    def test_after_tasks_patch_plan_without_tasks_still_requires_tasks(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            (ws / "specs" / "feature-p").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-p" / "patch-plan.md").write_text(
                "\n".join(
                    [
                        "# Patch plan",
                        "## 1. Problem Statement",
                        "Fix a scoped issue in existing module",
                        "## 2. Files / Modules Affected",
                        "- src/service.py",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_tasks")
            self.assertEqual(result.returncode, 0)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertTrue(feedback.exists())
            self.assertIn("tasks-presence", feedback.read_text(encoding="utf-8"))

    def test_after_tasks_active_bugfix_scope_ignores_other_feature_plans(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)

            (ws / "specs" / "feature-required").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-required" / "system-design-plan.md").write_text(
                "\n".join(
                    [
                        "# Plan",
                        "## 4. Architectural Patterns Applied",
                        "- DDD",
                        "## 4b. Code-Level Design Patterns Applied",
                        "- Command + Handler",
                        "## 5. DDD Aggregates",
                        "- Account",
                        "## 13. Test Strategy",
                        "- E2E journey",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            (ws / "specs" / "feature-bugfix").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-bugfix" / "bugfix-report.md").write_text(
                "\n".join(
                    [
                        "---",
                        "work_class: bugfix",
                        "---",
                        "# Bugfix report",
                        "## 1. Symptom",
                        "- Failure in checkout path",
                        "## 2. Reproduction",
                        "1. Submit request",
                        "2. Observe 500",
                        "## 3. Expected Behavior",
                        "- Return 400",
                        "## 4. Regression Test Target",
                        "- Add integration regression",
                        "## 5. Root Cause",
                        "- Missing guard",
                        "## 6. Fix Strategy",
                        "- Add guard",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            write_workflow_state_feature(ws, "feature-bugfix")

            result = self.run_gate(ws, "after_tasks")
            self.assertEqual(result.returncode, 0)
            self.assertIn("Gates passed", result.stdout)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            if feedback.exists():
                self.assertNotIn("tasks-presence", feedback.read_text(encoding="utf-8"))

    def test_after_review_active_bugfix_scope_ignores_unchecked_tasks_in_other_feature(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            write_e2e_test(ws)

            write_workflow_state_feature(ws, "feature-bugfix")
            state_path = ws / ".specify" / "context" / "workflow-state.yml"
            state_path.write_text(
                "\n".join(
                    [
                        'feature: "feature-bugfix"',
                        'current_phase: "review"',
                        "phases:",
                        "  review:",
                        "    status: in_progress",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            (ws / "specs" / "feature-required").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-required" / "tasks.md").write_text("- [ ] unfinished task\n", encoding="utf-8")

            (ws / "specs" / "feature-bugfix").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-bugfix" / "bugfix-report.md").write_text(
                "\n".join(
                    [
                        "---",
                        "work_class: bugfix",
                        "---",
                        "# Bugfix report",
                        "## 1. Symptom",
                        "- Failure in checkout path",
                        "## 2. Reproduction",
                        "1. Submit request",
                        "2. Observe 500",
                        "## 3. Expected Behavior",
                        "- Return 400",
                        "## 4. Regression Test Target",
                        "- Add integration regression",
                        "## 5. Root Cause",
                        "- Missing guard",
                        "## 6. Fix Strategy",
                        "- Add guard",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            result = self.run_gate(ws, "after_review")
            self.assertEqual(result.returncode, 0)
            self.assertIn("Gates passed", result.stdout)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            if feedback.exists():
                self.assertNotIn("completion-tasks-unchecked", feedback.read_text(encoding="utf-8"))

    def test_after_tasks_feature_local_tasks_file_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            (ws / "specs" / "feature-a").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-a" / "tasks.md").write_text("- [ ] task\n", encoding="utf-8")
            result = self.run_gate(ws, "after_tasks")
            self.assertEqual(result.returncode, 0)
            self.assertIn("Gates passed", result.stdout)

    def test_after_tasks_root_tasks_file_fallback_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            (ws / "tasks.md").write_text("- [ ] task\n", encoding="utf-8")
            result = self.run_gate(ws, "after_tasks")
            self.assertEqual(result.returncode, 0)
            self.assertIn("Gates passed", result.stdout)

    def test_after_tasks_bare_list_returns_tier1_checkbox_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            (ws / "specs" / "feature-a").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-a" / "tasks.md").write_text(
                "# Tasks\n- T001 Implement domain layer\n- T002 Write tests\n",
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_tasks")
            self.assertEqual(result.returncode, 0)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertTrue(feedback.exists())
            self.assertIn("tasks-checkbox-format", feedback.read_text(encoding="utf-8"))

    def test_after_tasks_checkbox_format_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            (ws / "specs" / "feature-a").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-a" / "tasks.md").write_text(
                "# Tasks\n- [ ] Implement domain layer\n- [x] Write tests\n",
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_tasks")
            self.assertEqual(result.returncode, 0)
            self.assertIn("Gates passed", result.stdout)

    def test_after_tasks_mixed_checkbox_and_bare_emits_warning(self):
        """Any bare task list item should trigger the format warning."""
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            (ws / "specs" / "feature-a").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-a" / "tasks.md").write_text(
                "# Tasks\n- [ ] T001 Real task\n- T002 follow-up cleanup item\n",
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_tasks")
            self.assertEqual(result.returncode, 0)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertTrue(feedback.exists())
            self.assertIn("tasks-checkbox-format", feedback.read_text(encoding="utf-8"))

    def test_after_tasks_notes_bullets_are_not_treated_as_tasks(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            (ws / "specs" / "feature-a").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-a" / "tasks.md").write_text(
                "\n".join(
                    [
                        "# Tasks",
                        "## Implementation",
                        "- [ ] Real task",
                        "## Notes",
                        "- Note: this is contextual information",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_tasks")
            self.assertEqual(result.returncode, 0)
            self.assertIn("Gates passed", result.stdout)

    def test_after_tasks_subheading_under_tasks_inherits_task_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            (ws / "specs" / "feature-a").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-a" / "tasks.md").write_text(
                "\n".join(
                    [
                        "# Tasks",
                        "## Implementation",
                        "- [ ] T001 Real task",
                        "- T002 follow-up cleanup item",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_tasks")
            self.assertEqual(result.returncode, 0)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertTrue(feedback.exists())
            self.assertIn("tasks-checkbox-format", feedback.read_text(encoding="utf-8"))

    def test_after_tasks_bare_instruction_bullets_do_not_emit_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            (ws / "specs" / "feature-a").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-a" / "tasks.md").write_text(
                "# Format Rules\n- Include exact file paths\n- Assign story IDs\n",
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_tasks")
            self.assertEqual(result.returncode, 0)
            self.assertIn("Gates passed", result.stdout)

    def test_after_plan_missing_plan_file_returns_tier1_continue(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertTrue(feedback.exists())
            self.assertIn("plan-presence", feedback.read_text(encoding="utf-8"))

    def test_after_plan_valid_system_design_plan_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            (ws / "specs" / "feature-a").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-a" / "system-design-plan.md").write_text(
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
            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            self.assertIn("Gates passed", result.stdout)

    def test_after_plan_system_plan_missing_test_strategy_returns_tier1(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            (ws / "specs" / "feature-a").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-a" / "system-design-plan.md").write_text(
                "\n".join(
                    [
                        "# Plan",
                        "## 4. Architectural Patterns Applied",
                        "- Domain-Driven Design with explicit bounded contexts",
                        "## 4b. Code-Level Design Patterns Applied",
                        "- Command + Handler and Value Objects are required for this feature",
                        "## 5. DDD Aggregates",
                        "- Order aggregate with transition invariants",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertTrue(feedback.exists())
            self.assertIn("plan-section-missing", feedback.read_text(encoding="utf-8"))

    def test_after_plan_placeholder_only_content_returns_tier1_continue(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            (ws / "specs" / "feature-a").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-a" / "system-design-plan.md").write_text(
                "\n".join(
                    [
                        "# Plan",
                        "## 4. Architectural Patterns Applied",
                        "_e.g., fill this with actual patterns_",
                        "## 4b. Code-Level Design Patterns Applied",
                        "_e.g., list code-level patterns_",
                        "## 5. DDD Aggregates",
                        "MANDATORY: declare aggregates",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertTrue(feedback.exists())
            self.assertIn("plan-section-placeholder", feedback.read_text(encoding="utf-8"))

    def test_after_plan_missing_4b_returns_tier1_continue(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            (ws / "specs" / "feature-a").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-a" / "system-design-plan.md").write_text(
                "\n".join(
                    [
                        "# Plan",
                        "## 4. Architectural Patterns Applied",
                        "- DDD and Hexagonal Architecture",
                        "## 5. DDD Aggregates",
                        "- Account aggregate with invariant checks",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertTrue(feedback.exists())
            self.assertIn("plan-section-missing", feedback.read_text(encoding="utf-8"))

    def test_after_plan_heading_mention_in_prose_does_not_count_as_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            (ws / "specs" / "feature-a").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-a" / "system-design-plan.md").write_text(
                "\n".join(
                    [
                        "# Plan",
                        "We will later add the heading ## 4b. Code-Level Design Patterns Applied.",
                        "## 4. Architectural Patterns Applied",
                        "- DDD and Hexagonal Architecture",
                        "## 5. DDD Aggregates",
                        "- Account aggregate with invariant checks",
                        "## 13. Test Strategy",
                        "- E2E paths",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertTrue(feedback.exists())
            self.assertIn("plan-section-missing", feedback.read_text(encoding="utf-8"))

    def test_after_plan_heading_in_code_fence_does_not_count_as_section(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            (ws / "specs" / "feature-a").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-a" / "system-design-plan.md").write_text(
                "\n".join(
                    [
                        "# Plan",
                        "## 4. Architectural Patterns Applied",
                        "- DDD and Hexagonal Architecture",
                        "```md",
                        "## 4b. Code-Level Design Patterns Applied",
                        "- This is only an example in code fence",
                        "```",
                        "## 5. DDD Aggregates",
                        "- Account aggregate with invariant checks",
                        "## 13. Test Strategy",
                        "- E2E paths",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertTrue(feedback.exists())
            self.assertIn("plan-section-missing", feedback.read_text(encoding="utf-8"))

    def test_after_plan_patch_plan_uses_patch_headings(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            (ws / "specs" / "feature-b").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-b" / "patch-plan.md").write_text(
                "\n".join(
                    [
                        "# Patch plan",
                        "## 1. Problem Statement",
                        "Fix a scoped bug in existing module",
                        "## 2. Files / Modules Affected",
                        "- src/payments/service.py",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            self.assertIn("Gates passed", result.stdout)

    def test_after_plan_legacy_filename_wins_over_conflicting_work_class(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            (ws / "specs" / "feature-b").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-b" / "system-design-plan.md").write_text(
                "\n".join(
                    [
                        "---",
                        "work_class: patch",
                        "---",
                        "# Plan",
                        "## 1. Problem Statement",
                        "Apply a scoped non-feature change",
                        "## 2. Files / Modules Affected",
                        "- src/service.py",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertTrue(feedback.exists())
            self.assertIn("plan-section-missing", feedback.read_text(encoding="utf-8"))
            self.assertIn("ignoring work_class", result.stderr)

    def test_after_plan_unknown_work_class_falls_back_to_filename_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            (ws / "specs" / "feature-b").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-b" / "patch-plan.md").write_text(
                "\n".join(
                    [
                        "---",
                        "work_class: does-not-exist",
                        "---",
                        "# Patch plan",
                        "## 1. Problem Statement",
                        "Fix a scoped issue",
                        "## 2. Files / Modules Affected",
                        "- src/service.py",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            self.assertIn("ignoring work_class", result.stderr)
            self.assertIn("Gates passed", result.stdout)

    def test_after_plan_legacy_policy_without_work_classes_still_works_without_frontmatter(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            (ws / ".specify").mkdir(parents=True, exist_ok=True)
            (ws / ".specify" / "policy.yml").write_text(
                "\n".join(
                    [
                        "plan_tiers:",
                        "  system:",
                        "    match_filename: system-design-plan",
                        "    mandatory_sections:",
                        "      - '## 4. Architectural Patterns Applied'",
                        "      - '## 4b. Code-Level Design Patterns Applied'",
                        "      - '## 5. DDD Aggregates'",
                        "      - '## 13. Test Strategy'",
                        "    pattern_selection: required",
                        "  patch:",
                        "    match_filename: patch-plan",
                        "    mandatory_sections:",
                        "      - '## 1. Problem Statement'",
                        "      - '## 2. Files / Modules Affected'",
                        "    pattern_selection: optional",
                        "placeholder_markers:",
                        "  - '_e.g.,'",
                        "  - 'e.g.,'",
                        "  - 'MANDATORY'",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            (ws / "specs" / "feature-a").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-a" / "system-design-plan.md").write_text(
                "\n".join(
                    [
                        "# Plan",
                        "## 4. Architectural Patterns Applied",
                        "- DDD + Hexagonal",
                        "## 4b. Code-Level Design Patterns Applied",
                        "- Strategy + Command",
                        "## 5. DDD Aggregates",
                        "- Account aggregate",
                        "## 13. Test Strategy",
                        "- E2E journey coverage",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            (ws / "specs" / "feature-a" / "patch-plan.md").write_text(
                "\n".join(
                    [
                        "# Patch plan",
                        "## 1. Problem Statement",
                        "Fix a scoped issue",
                        "## 2. Files / Modules Affected",
                        "- src/service.py",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            self.assertIn("Gates passed", result.stdout)

    def test_after_plan_non_legacy_work_class_uses_legacy_policy_mapping(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            (ws / ".specify").mkdir(parents=True, exist_ok=True)
            (ws / ".specify" / "policy.yml").write_text(
                "\n".join(
                    [
                        "plan_tiers:",
                        "  system:",
                        "    match_filename: system-design-plan",
                        "    mandatory_sections:",
                        "      - '## 4. Architectural Patterns Applied'",
                        "      - '## 4b. Code-Level Design Patterns Applied'",
                        "      - '## 5. DDD Aggregates'",
                        "      - '## 13. Test Strategy'",
                        "    pattern_selection: required",
                        "  patch:",
                        "    match_filename: patch-plan",
                        "    mandatory_sections:",
                        "      - '## 1. Problem Statement'",
                        "      - '## 2. Files / Modules Affected'",
                        "    pattern_selection: optional",
                        "placeholder_markers:",
                        "  - '_e.g.,'",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            (ws / "specs" / "feature-a").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-a" / "refactor-plan.md").write_text(
                "\n".join(
                    [
                        "---",
                        "work_class: patch",
                        "---",
                        "# Refactor plan",
                        "## 1. Problem Statement",
                        "Fix a scoped issue",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertTrue(feedback.exists())
            self.assertIn("plan-section-missing", feedback.read_text(encoding="utf-8"))

    def test_after_plan_non_legacy_feature_work_class_uses_legacy_policy_mapping(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            (ws / ".specify").mkdir(parents=True, exist_ok=True)
            (ws / ".specify" / "policy.yml").write_text(
                "\n".join(
                    [
                        "plan_tiers:",
                        "  system:",
                        "    match_filename: system-design-plan",
                        "    mandatory_sections:",
                        "      - '## 4. Architectural Patterns Applied'",
                        "      - '## 4b. Code-Level Design Patterns Applied'",
                        "      - '## 5. DDD Aggregates'",
                        "      - '## 13. Test Strategy'",
                        "    pattern_selection: required",
                        "  patch:",
                        "    match_filename: patch-plan",
                        "    mandatory_sections:",
                        "      - '## 1. Problem Statement'",
                        "      - '## 2. Files / Modules Affected'",
                        "    pattern_selection: optional",
                        "placeholder_markers:",
                        "  - '_e.g.,'",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            (ws / "specs" / "feature-a").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-a" / "refactor-plan.md").write_text(
                "\n".join(
                    [
                        "---",
                        "work_class: feature",
                        "---",
                        "# Refactor plan",
                        "## 4. Architectural Patterns Applied",
                        "- DDD and Hexagonal Architecture",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertTrue(feedback.exists())
            text = feedback.read_text(encoding="utf-8")
            self.assertIn("plan-section-missing", text)
            self.assertNotIn("plan-work-class-unresolved", text)

    def test_after_plan_non_legacy_name_with_work_class_is_discovered(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            (ws / "specs" / "feature-c").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-c" / "refactor-plan.md").write_text(
                "\n".join(
                    [
                        "---",
                        "work_class: refactor",
                        "---",
                        "# Refactor plan",
                        "## 1. Goal",
                        "Refactor internals without changing behavior.",
                        "## 2. Scope / Non-Scope",
                        "- In scope: extract service internals",
                        "- Out of scope: endpoint contract changes",
                        "## 3. Invariants to Preserve",
                        "- Existing API payloads and status codes",
                        "## 4. Public Contract Impact",
                        "None",
                        "## 5. Behavioral Equivalence Strategy",
                        "- Compare integration snapshots before and after",
                        "## 6. Regression Strategy",
                        "- Add regression test for refactored orchestration path",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            self.assertIn("Gates passed", result.stdout)

    def test_after_plan_bugfix_report_with_work_class_is_discovered(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            (ws / "specs" / "feature-c").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-c" / "bugfix-report.md").write_text(
                "\n".join(
                    [
                        "---",
                        "work_class: bugfix",
                        "---",
                        "# Bugfix report",
                        "## 1. Symptom",
                        "- Checkout flow returns 500 for expired promo token.",
                        "## 2. Reproduction",
                        "1. Submit checkout with expired promo token",
                        "2. Observe HTTP 500",
                        "## 3. Expected Behavior",
                        "- Return HTTP 400 with validation error payload.",
                        "## 4. Regression Test Target",
                        "- Add integration test for expired promo checkout flow",
                        "## 5. Root Cause",
                        "- Missing null guard in promo validation branch",
                        "## 6. Fix Strategy",
                        "- Add guard and map to validation error response",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            self.assertIn("Gates passed", result.stdout)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            if feedback.exists():
                self.assertNotIn("plan-presence", feedback.read_text(encoding="utf-8"))

    def test_after_plan_bugfix_report_with_work_class_uses_legacy_plan_tiers_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            (ws / ".specify").mkdir(parents=True, exist_ok=True)
            (ws / ".specify" / "policy.yml").write_text(
                "\n".join(
                    [
                        "plan_tiers:",
                        "  system:",
                        "    match_filename: system-design-plan",
                        "    mandatory_sections:",
                        "      - '## 4. Architectural Patterns Applied'",
                        "      - '## 4b. Code-Level Design Patterns Applied'",
                        "      - '## 5. DDD Aggregates'",
                        "      - '## 13. Test Strategy'",
                        "    pattern_selection: required",
                        "  patch:",
                        "    match_filename: patch-plan",
                        "    mandatory_sections:",
                        "      - '## 1. Problem Statement'",
                        "      - '## 2. Files / Modules Affected'",
                        "    pattern_selection: optional",
                        "placeholder_markers:",
                        "  - '_e.g.,'",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            (ws / "specs" / "feature-c").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-c" / "bugfix-report.md").write_text(
                "\n".join(
                    [
                        "---",
                        "work_class: patch",
                        "---",
                        "# Bugfix report",
                        "## 1. Problem Statement",
                        "Fix a regression introduced in the last release",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertTrue(feedback.exists())
            text = feedback.read_text(encoding="utf-8")
            self.assertIn("plan-section-missing", text)
            self.assertNotIn("plan-work-class-unresolved", text)

    def test_after_plan_refactor_plan_missing_required_section_returns_tier1(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            (ws / "specs" / "feature-r").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-r" / "refactor-plan.md").write_text(
                "\n".join(
                    [
                        "---",
                        "work_class: refactor",
                        "---",
                        "# Refactor plan",
                        "## 1. Goal",
                        "Improve internal structure while preserving behavior.",
                        "## 2. Scope / Non-Scope",
                        "- In scope: repository abstraction cleanup",
                        "## 3. Invariants to Preserve",
                        "- API contract and persistence format",
                        "## 4. Public Contract Impact",
                        "None",
                        "## 5. Behavioral Equivalence Strategy",
                        "- Compare baseline snapshots",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertTrue(feedback.exists())
            self.assertIn("plan-section-missing", feedback.read_text(encoding="utf-8"))

    def test_after_plan_bugfix_report_missing_required_section_returns_tier1(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            (ws / "specs" / "feature-b").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-b" / "bugfix-report.md").write_text(
                "\n".join(
                    [
                        "---",
                        "work_class: bugfix",
                        "---",
                        "# Bugfix report",
                        "## 1. Symptom",
                        "- Endpoint returns 500 for malformed payload",
                        "## 2. Reproduction",
                        "1. Send malformed payload",
                        "2. Observe 500 response",
                        "## 3. Expected Behavior",
                        "- Endpoint returns 400 validation error",
                        "## 4. Regression Test Target",
                        "- Add integration test for malformed payload",
                        "## 5. Root Cause",
                        "- Missing validation branch",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertTrue(feedback.exists())
            self.assertIn("plan-section-missing", feedback.read_text(encoding="utf-8"))

    def test_after_plan_migration_plan_with_work_class_is_discovered(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            (ws / "specs" / "feature-d").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-d" / "migration-plan.md").write_text(
                "\n".join(
                    [
                        "---",
                        "work_class: migration",
                        "---",
                        "# Migration plan",
                        "## 4. Architectural Patterns Applied",
                        "- Incremental migration with bounded-context boundaries",
                        "## 4b. Code-Level Design Patterns Applied",
                        "- Adapter + anti-corruption layer",
                        "## 5. DDD Aggregates",
                        "- Account aggregate remains source of truth",
                        "## 13. Test Strategy",
                        "- E2E and rollback validation",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            self.assertIn("Gates passed", result.stdout)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            if feedback.exists():
                self.assertNotIn("plan-presence", feedback.read_text(encoding="utf-8"))

    def test_after_plan_spike_note_with_work_class_is_discovered(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            (ws / "specs" / "feature-e").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-e" / "spike-note.md").write_text(
                "\n".join(
                    [
                        "---",
                        "work_class: spike",
                        "---",
                        "# Spike note",
                        "## 1. Problem Statement",
                        "Evaluate two candidate storage engines under current constraints",
                        "## 2. Files / Modules Affected",
                        "- docs/spike-notes/storage-options.md",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            self.assertIn("Gates passed", result.stdout)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            if feedback.exists():
                self.assertNotIn("plan-presence", feedback.read_text(encoding="utf-8"))

    def test_after_plan_tooling_plan_with_work_class_is_discovered(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            (ws / "specs" / "feature-f").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-f" / "tooling-plan.md").write_text(
                "\n".join(
                    [
                        "---",
                        "work_class: tooling",
                        "---",
                        "# Tooling plan",
                        "## 1. Problem Statement",
                        "Improve local lint execution stability",
                        "## 2. Files / Modules Affected",
                        "- scripts/lint.sh",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            self.assertIn("Gates passed", result.stdout)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            if feedback.exists():
                self.assertNotIn("plan-presence", feedback.read_text(encoding="utf-8"))

    def test_after_plan_non_legacy_name_without_frontmatter_is_tier1_missing_work_class(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            (ws / "specs" / "feature-c").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-c" / "refactor-plan.md").write_text(
                "\n".join(
                    [
                        "# Refactor plan",
                        "## Notes",
                        "- Internal cleanup, no explicit work_class metadata",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertTrue(feedback.exists())
            text = feedback.read_text(encoding="utf-8")
            self.assertIn("plan-work-class-missing", text)
            self.assertNotIn("plan-presence", text)

    def test_after_plan_ignores_auxiliary_plan_docs_under_specs(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            (ws / "specs" / "feature-c").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-c" / "notes-plan.md").write_text(
                "\n".join(
                    [
                        "---",
                        "work_class: feature",
                        "---",
                        "# Notes plan",
                        "This is a sidecar design note and must not be gated as a first-class plan artifact.",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertTrue(feedback.exists())
            text = feedback.read_text(encoding="utf-8")
            self.assertIn("plan-presence", text)
            self.assertNotIn("plan-section-missing", text)

    def test_after_plan_valid_legacy_plan_with_auxiliary_metadata_plan_stays_green(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            (ws / "specs" / "feature-c").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-c" / "system-design-plan.md").write_text(
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
            (ws / "specs" / "feature-c" / "rollback-plan.md").write_text(
                "\n".join(
                    [
                        "---",
                        "work_class: feature",
                        "---",
                        "# Rollback notes",
                        "Auxiliary documentation that should be ignored by after_plan.",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            self.assertIn("Gates passed", result.stdout)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            if feedback.exists():
                self.assertNotIn("plan-section-missing", feedback.read_text(encoding="utf-8"))

    def test_after_plan_non_legacy_blank_work_class_emits_unresolved(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            (ws / "specs" / "feature-c").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-c" / "refactor-plan.md").write_text(
                "\n".join(
                    [
                        "---",
                        "work_class: '   '",
                        "---",
                        "# Refactor plan",
                        "## Notes",
                        "- Internal cleanup",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertTrue(feedback.exists())
            text = feedback.read_text(encoding="utf-8")
            self.assertIn("plan-work-class-unresolved", text)
            self.assertNotIn("plan-presence", text)

    def test_after_plan_non_legacy_non_string_work_class_emits_unresolved(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            (ws / "specs" / "feature-c").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-c" / "refactor-plan.md").write_text(
                "\n".join(
                    [
                        "---",
                        "work_class:",
                        "  - patch",
                        "---",
                        "# Refactor plan",
                        "## Notes",
                        "- Internal cleanup",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertTrue(feedback.exists())
            text = feedback.read_text(encoding="utf-8")
            self.assertIn("plan-work-class-unresolved", text)
            self.assertNotIn("plan-presence", text)

    def test_after_plan_non_legacy_bom_prefixed_frontmatter_is_discovered(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            (ws / "specs" / "feature-c").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-c" / "refactor-plan.md").write_text(
                "\ufeff"
                + "\n".join(
                    [
                        "---",
                        "work_class: patch",
                        "---",
                        "# Refactor plan",
                        "## 1. Problem Statement",
                        "Refactor internals without changing behavior",
                        "## 2. Files / Modules Affected",
                        "- src/refactor_target.py",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            self.assertIn("Gates passed", result.stdout)

    def test_after_plan_non_legacy_unknown_work_class_emits_tier1_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            (ws / "specs" / "feature-c").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-c" / "refactor-plan.md").write_text(
                "\n".join(
                    [
                        "---",
                        "work_class: does-not-exist",
                        "---",
                        "# Refactor plan",
                        "## 1. Problem Statement",
                        "Refactor internals without changing behavior",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertTrue(feedback.exists())
            self.assertIn("plan-work-class-unresolved", feedback.read_text(encoding="utf-8"))

    def test_after_plan_does_not_run_domain_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "fintech-trading")
            write_policy(ws)
            ws.joinpath("trade.py").write_text("price: float = 12.3\n", encoding="utf-8")
            (ws / "specs" / "feature-a").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-a" / "system-design-plan.md").write_text(
                "\n".join(
                    [
                        "# Plan",
                        "## 4. Architectural Patterns Applied",
                        "- DDD + Hexagonal",
                        "## 4b. Code-Level Design Patterns Applied",
                        "- State machine and command handler",
                        "## 5. DDD Aggregates",
                        "- Order aggregate",
                        "## 13. Test Strategy",
                        "- E2E journey coverage declared",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            self.assertIn("Gates passed", result.stdout)

    def test_after_plan_lazy_mode_loads_selected_patterns(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base", knowledge_mode="lazy")
            write_policy(ws)
            (ws / "specs" / "feature-a").mkdir(parents=True, exist_ok=True)
            (ws / ".specify" / ".knowledge-store" / "patterns").mkdir(parents=True, exist_ok=True)
            (ws / ".specify" / ".knowledge-store" / "patterns" / "domain-driven-design.md").write_text(
                "# DDD\n",
                encoding="utf-8",
            )
            (ws / "specs" / "feature-a" / "system-design-plan.md").write_text(
                "\n".join(
                    [
                        "# Plan",
                        "<!-- selected_patterns: domain-driven-design.md -->",
                        "## 4. Architectural Patterns Applied",
                        "- DDD with explicit bounded contexts",
                        "## 4b. Code-Level Design Patterns Applied",
                        "- command + handler",
                        "## 5. DDD Aggregates",
                        "- Order",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            self.assertTrue((ws / ".specify" / "patterns" / "domain-driven-design.md").exists())

    def test_after_plan_lazy_mode_missing_pattern_selection_is_tier1(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base", knowledge_mode="lazy")
            write_policy(ws)
            (ws / "specs" / "feature-a").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-a" / "system-design-plan.md").write_text(
                "\n".join(
                    [
                        "# Plan",
                        "## 4. Architectural Patterns Applied",
                        "- Domain-driven architecture selected",
                        "## 4b. Code-Level Design Patterns Applied",
                        "- command + handler",
                        "## 5. DDD Aggregates",
                        "- Order",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertTrue(feedback.exists())
            self.assertIn("knowledge-pattern-selection-missing", feedback.read_text(encoding="utf-8"))

    def test_after_plan_lazy_mode_non_legacy_feature_work_class_requires_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base", knowledge_mode="lazy")
            write_policy(ws)
            (ws / "specs" / "feature-c").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-c" / "refactor-plan.md").write_text(
                "\n".join(
                    [
                        "---",
                        "work_class: feature",
                        "---",
                        "# Refactor plan",
                        "## 4. Architectural Patterns Applied",
                        "- Domain-driven architecture selected",
                        "## 4b. Code-Level Design Patterns Applied",
                        "- command + handler",
                        "## 5. DDD Aggregates",
                        "- Order",
                        "## 13. Test Strategy",
                        "- E2E flow for order lifecycle",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertTrue(feedback.exists())
            self.assertIn("knowledge-pattern-selection-missing", feedback.read_text(encoding="utf-8"))

    def test_after_plan_lazy_mode_non_legacy_without_work_class_is_tier1_missing_work_class(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base", knowledge_mode="lazy")
            write_policy(ws)
            (ws / "specs" / "feature-c").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-c" / "refactor-plan.md").write_text(
                "\n".join(
                    [
                        "# Refactor plan",
                        "## Notes",
                        "- Internal cleanup, no explicit work_class metadata",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertTrue(feedback.exists())
            text = feedback.read_text(encoding="utf-8")
            self.assertIn("plan-work-class-missing", text)
            self.assertNotIn("knowledge-pattern-selection-missing", text)

    def test_after_plan_lazy_mode_patch_plan_none_selection_passes(self):
        """Patch plans with explicit 'none' selection should not trigger findings."""
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base", knowledge_mode="lazy")
            write_policy(ws)
            (ws / "specs" / "feature-b").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-b" / "patch-plan.md").write_text(
                "\n".join(
                    [
                        "# Patch plan",
                        "<!-- selected_patterns: none -->",
                        "## 1. Problem Statement",
                        "Fix a scoped bug in existing module",
                        "## 2. Files / Modules Affected",
                        "- src/service.py",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            self.assertIn("Gates passed", result.stdout)

    def test_after_plan_lazy_mode_structured_selection_multiple(self):
        """Structured block with multiple patterns hydrates all of them."""
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base", knowledge_mode="lazy")
            write_policy(ws)
            store = ws / ".specify" / ".knowledge-store"
            (store / "patterns").mkdir(parents=True, exist_ok=True)
            (store / "design-patterns").mkdir(parents=True, exist_ok=True)
            (store / "patterns" / "domain-driven-design.md").write_text("# DDD\n", encoding="utf-8")
            (store / "design-patterns" / "command-and-handler.md").write_text("# C+H\n", encoding="utf-8")

            (ws / "specs" / "feature-a").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-a" / "system-design-plan.md").write_text(
                "\n".join(
                    [
                        "# Plan",
                        "<!-- selected_patterns: domain-driven-design.md, command-and-handler.md -->",
                        "## 4. Architectural Patterns Applied",
                        "- DDD",
                        "## 4b. Code-Level Design Patterns Applied",
                        "- Command + Handler",
                        "## 5. DDD Aggregates",
                        "- Order",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            self.assertTrue((ws / ".specify" / "patterns" / "domain-driven-design.md").exists())
            self.assertTrue((ws / ".specify" / "design-patterns" / "command-and-handler.md").exists())

    def test_after_plan_lazy_mode_regex_fallback_ignores_unknown_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base", knowledge_mode="lazy")
            write_policy(ws)
            store = ws / ".specify" / ".knowledge-store"
            (store / "patterns").mkdir(parents=True, exist_ok=True)
            (store / "patterns" / "domain-driven-design.md").write_text("# DDD\n", encoding="utf-8")
            (ws / ".specify").mkdir(parents=True, exist_ok=True)
            (ws / ".specify" / "knowledge-manifest.json").write_text(
                json.dumps(
                    {
                        "files": {
                            "domain-driven-design.md": {
                                "category": "patterns",
                                "source": str(store / "patterns" / "domain-driven-design.md"),
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            (ws / "specs" / "feature-a").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-a" / "system-design-plan.md").write_text(
                "\n".join(
                    [
                        "# Plan",
                        "Reference docs: `README.md`, `domain-driven-design.md`",
                        "## 4. Architectural Patterns Applied",
                        "- DDD",
                        "## 4b. Code-Level Design Patterns Applied",
                        "- command + handler",
                        "## 5. DDD Aggregates",
                        "- Order",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            self.assertTrue((ws / ".specify" / "patterns" / "domain-driven-design.md").exists())
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            if feedback.exists():
                self.assertNotIn("knowledge-pattern-unresolved", feedback.read_text(encoding="utf-8"))

    def test_after_plan_lazy_mode_regex_fallback_emits_deprecation(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base", knowledge_mode="lazy")
            write_policy(ws)
            store = ws / ".specify" / ".knowledge-store"
            (store / "patterns").mkdir(parents=True, exist_ok=True)
            (store / "patterns" / "domain-driven-design.md").write_text("# DDD\n", encoding="utf-8")
            (ws / ".specify").mkdir(parents=True, exist_ok=True)
            (ws / ".specify" / "knowledge-manifest.json").write_text(
                json.dumps(
                    {
                        "files": {
                            "domain-driven-design.md": {
                                "category": "patterns",
                                "source": str(store / "patterns" / "domain-driven-design.md"),
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            (ws / "specs" / "feature-a").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-a" / "system-design-plan.md").write_text(
                "\n".join(
                    [
                        "# Plan",
                        "Inline mention: `domain-driven-design.md`",
                        "## 4. Architectural Patterns Applied",
                        "- DDD",
                        "## 4b. Code-Level Design Patterns Applied",
                        "- command + handler",
                        "## 5. DDD Aggregates",
                        "- Order",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            self.assertIn("deprecated inline markdown filename fallback", result.stderr)

    def test_base_policy_wave_a_work_classes_contract_shape(self):
        policy_path = ROOT / "presets" / "base" / "policy.yml"
        data = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
        self.assertIsInstance(data, dict)
        work_classes = data.get("work_classes")
        self.assertIsInstance(work_classes, dict)
        expected_classes = {"feature", "patch", "refactor", "bugfix", "migration", "tooling", "spike"}
        self.assertTrue(expected_classes.issubset(set(work_classes.keys())))

        required_fields = {
            "allowed_templates",
            "mandatory_sections",
            "pattern_selection",
            "task_policy",
            "testing_expectation",
            "gate_profile",
        }
        for work_class in expected_classes:
            entry = work_classes.get(work_class)
            self.assertIsInstance(entry, dict)
            self.assertTrue(required_fields.issubset(set(entry.keys())))

        self.assertEqual(
            work_classes["refactor"].get("allowed_templates"),
            ["refactor-plan-template.md"],
        )
        self.assertEqual(work_classes["refactor"].get("task_policy"), "optional")
        self.assertEqual(work_classes["refactor"].get("gate_profile"), "refactor-safe")
        self.assertEqual(
            work_classes["bugfix"].get("allowed_templates"),
            ["bugfix-report-template.md"],
        )
        self.assertEqual(work_classes["bugfix"].get("task_policy"), "optional")
        self.assertEqual(work_classes["bugfix"].get("gate_profile"), "bugfix-fast")

    def test_wave_b_templates_include_work_class_frontmatter(self):
        refactor_tpl = ROOT / "presets" / "base" / "templates" / "refactor-plan-template.md"
        bugfix_tpl = ROOT / "presets" / "base" / "templates" / "bugfix-report-template.md"

        refactor_text = refactor_tpl.read_text(encoding="utf-8")
        bugfix_text = bugfix_tpl.read_text(encoding="utf-8")

        self.assertIn("---", refactor_text)
        self.assertIn("work_class: refactor", refactor_text)
        self.assertIn("---", bugfix_text)
        self.assertIn("work_class: bugfix", bugfix_text)

    def test_input_contract_plan_templates_reference_system_design_name(self):
        contracts_path = ROOT / "presets" / "base" / "input-contracts.yml"
        text = contracts_path.read_text(encoding="utf-8")
        self.assertIn("system-design-plan-template.md", text)
        self.assertNotIn("full-plan-template.md", text)

    def test_input_contract_tasks_are_conditional_for_wave_b_work_classes(self):
        contracts_path = ROOT / "presets" / "base" / "input-contracts.yml"
        text = contracts_path.read_text(encoding="utf-8")
        self.assertIn("tasks.md required only for work classes with task_policy: required", text)
        self.assertIn("tasks_document", text)
        self.assertIn("optional_inputs:", text)

    def test_after_tasks_does_not_run_domain_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "fintech-trading")
            ws.joinpath("trade.py").write_text("price: float = 12.3\n", encoding="utf-8")
            (ws / "specs" / "feature-a").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-a" / "tasks.md").write_text("- [ ] task\n", encoding="utf-8")
            result = self.run_gate(ws, "after_tasks")
            self.assertEqual(result.returncode, 0)
            self.assertIn("Gates passed", result.stdout)

    def test_trading_float_detected_is_tier2(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "fintech-trading")
            write_e2e_test(ws)
            ws.joinpath("trade.py").write_text("price: float = 12.3\n", encoding="utf-8")
            result = self.run_gate(ws, "after_implement")
            self.assertEqual(result.returncode, 1)
            self.assertIn("trading-no-float-money", result.stderr)

    def test_trading_idempotency_missing_is_tier2(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "fintech-trading")
            write_e2e_test(ws)
            ws.joinpath("orders.py").write_text(
                "\n".join(
                    [
                        "@router.post('/orders')",
                        "def place_order(req):",
                        "    return {'ok': True}",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_implement")
            self.assertEqual(result.returncode, 1)
            self.assertIn("trading-idempotency-key-missing", result.stderr)

    def test_trading_lifecycle_illegal_transition_is_tier2(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "fintech-trading")
            write_e2e_test(ws)
            ws.joinpath("lifecycle.py").write_text(
                "\n".join(
                    [
                        "def bad_transition(order):",
                        "    order.status = 'NEW'",
                        "    order.status = 'FILLED'",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_implement")
            self.assertEqual(result.returncode, 1)
            self.assertIn("trading-order-lifecycle-illegal-transition", result.stderr)

    def test_trading_hotpath_blocking_io_is_tier2(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "fintech-trading")
            write_e2e_test(ws)
            ws.joinpath("matching.py").write_text(
                "\n".join(
                    [
                        "import requests",
                        "def matching_engine_step():",
                        "    requests.get('https://example.com')",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_implement")
            self.assertEqual(result.returncode, 1)
            self.assertIn("trading-hotpath-blocking-io", result.stderr)

    def test_trading_replay_protection_missing_is_tier1(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "fintech-trading")
            write_e2e_test(ws)
            ws.joinpath("exec_handler.py").write_text(
                "\n".join(
                    [
                        "def execution_handler(event):",
                        "    return {'ok': True}",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_implement")
            self.assertEqual(result.returncode, 0)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertTrue(feedback.exists())
            self.assertIn("trading-replay-protection-missing", feedback.read_text(encoding="utf-8"))

    def test_healthcare_log_issue_is_tier1(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "healthcare")
            write_e2e_test(ws)
            ws.joinpath("service.py").write_text(
                "logger.info(f'email={email}')\n",
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_implement")
            self.assertEqual(result.returncode, 0)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertTrue(feedback.exists())

    def test_healthcare_patient_id_logging_is_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "healthcare")
            write_e2e_test(ws)
            ws.joinpath("service.py").write_text(
                "logger.info(f'patient_id={patient_id}')\n",
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_implement")
            self.assertEqual(result.returncode, 0)
            self.assertIn("Gates passed", result.stdout)

    def test_banking_sca_missing_is_tier1_advisory(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "fintech-banking")
            write_e2e_test(ws)
            ws.joinpath("payments.py").write_text(
                "\n".join(
                    [
                        "def payment_handler(req):",
                        "    idempotency_key = req.headers.get('Idempotency-Key')",
                        "    return {'ok': True}",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_implement")
            self.assertEqual(result.returncode, 0)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertTrue(feedback.exists())
            self.assertIn("banking-psd2-sca-missing-advisory", feedback.read_text(encoding="utf-8"))

    def test_banking_idempotency_missing_is_tier2(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "fintech-banking")
            write_e2e_test(ws)
            ws.joinpath("payments.py").write_text(
                "\n".join(
                    [
                        "@router.post('/payments')",
                        "def payment_handler(req):",
                        "    return {'ok': True}",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_implement")
            self.assertEqual(result.returncode, 1)
            self.assertIn("banking-idempotency-key-missing", result.stderr)

    def test_banking_ledger_inplace_mutation_is_tier2(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "fintech-banking")
            write_e2e_test(ws)
            ws.joinpath("ledger.py").write_text(
                "\n".join(
                    [
                        "def apply_entry(balance, delta):",
                        "    balance += delta",
                        "    return balance",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_implement")
            self.assertEqual(result.returncode, 1)
            self.assertIn("banking-ledger-inplace-mutation", result.stderr)

    def test_banking_payment_boundary_missing_controls_is_tier1(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "fintech-banking")
            write_e2e_test(ws)
            ws.joinpath("payments.py").write_text(
                "\n".join(
                    [
                        "@router.post('/payments')",
                        "def payment_handler(req):",
                        "    idempotency_key = req.headers.get('Idempotency-Key')",
                        "    return {'ok': True}",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_implement")
            self.assertEqual(result.returncode, 0)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertTrue(feedback.exists())
            self.assertIn("banking-payment-boundary-controls-missing", feedback.read_text(encoding="utf-8"))

    def test_trading_unparsable_python_reports_tier1(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "fintech-trading")
            write_e2e_test(ws)
            ws.joinpath("bad_trade.py").write_text(
                "def broken(:\n",
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_implement")
            self.assertEqual(result.returncode, 0)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertTrue(feedback.exists())
            self.assertIn("trading-parse-failed", feedback.read_text(encoding="utf-8"))

    def test_after_implement_no_e2e_tests_returns_tier1(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            ws.joinpath("service.py").write_text("x = 1\n", encoding="utf-8")
            result = self.run_gate(ws, "after_implement")
            self.assertEqual(result.returncode, 0)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertTrue(feedback.exists())
            self.assertIn("e2e-test-presence", feedback.read_text(encoding="utf-8"))

    def test_after_implement_e2e_test_present_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_e2e_test(ws)
            result = self.run_gate(ws, "after_implement")
            self.assertEqual(result.returncode, 0)
            self.assertIn("Gates passed", result.stdout)

    def test_after_implement_e2e_test_empty_returns_tier1(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            (ws / "e2e_test_orders.py").write_text("def test_order_flow():\n    value = 1\n", encoding="utf-8")
            result = self.run_gate(ws, "after_implement")
            self.assertEqual(result.returncode, 0)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertTrue(feedback.exists())
            self.assertIn("e2e-test-empty", feedback.read_text(encoding="utf-8"))

    def test_after_implement_e2e_test_placeholder_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            (ws / "e2e_test_orders.py").write_text("def test_order_flow():\n    pass\n", encoding="utf-8")
            result = self.run_gate(ws, "after_implement")
            self.assertEqual(result.returncode, 0)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertTrue(feedback.exists())
            text = feedback.read_text(encoding="utf-8")
            self.assertIn("e2e-test-placeholder", text)
            self.assertIn("Remediation:", text)

    def test_after_implement_e2e_family_without_assertions_reports_family_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            (ws / "checkout.e2e-spec.ts").write_text("test('checkout', async () => { /* TODO */ })\n", encoding="utf-8")
            result = self.run_gate(ws, "after_implement")
            self.assertEqual(result.returncode, 0)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertTrue(feedback.exists())
            text = feedback.read_text(encoding="utf-8")
            self.assertIn("e2e-test-family-empty", text)

    def test_after_implement_e2e_lowercase_todo_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            (ws / "checkout.e2e-spec.ts").write_text("test('checkout', async () => { /* todo */ })\n", encoding="utf-8")
            result = self.run_gate(ws, "after_implement")
            self.assertEqual(result.returncode, 0)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertTrue(feedback.exists())
            self.assertIn("e2e-test-placeholder", feedback.read_text(encoding="utf-8"))

    def test_after_implement_e2e_comment_assert_does_not_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            (ws / "checkout.e2e-spec.ts").write_text("// expect(order).toBeDefined()\n", encoding="utf-8")
            result = self.run_gate(ws, "after_implement")
            self.assertEqual(result.returncode, 0)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertTrue(feedback.exists())
            text = feedback.read_text(encoding="utf-8")
            self.assertIn("e2e-test-empty", text)

    def test_banking_route_without_payment_keyword_does_not_trigger_sca_advisory(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "fintech-banking")
            write_e2e_test(ws)
            ws.joinpath("api.py").write_text(
                "\n".join(
                    [
                        "@router.get('/health')",
                        "def health():",
                        "    return {'ok': True}",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_implement")
            self.assertEqual(result.returncode, 0)
            self.assertIn("Gates passed", result.stdout)

    def test_trading_validator_skips_test_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "fintech-trading")
            write_e2e_test(ws)
            (ws / "tests").mkdir(parents=True, exist_ok=True)
            (ws / "tests" / "trade_test.py").write_text("price: float = 12.3\n", encoding="utf-8")
            result = self.run_gate(ws, "after_implement")
            self.assertEqual(result.returncode, 0)
            self.assertIn("Gates passed", result.stdout)

    def test_tier1_feedback_written_even_with_tier2(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config_without_container(ws, "base", execution_mode="docker-fallback")
            result = self.run_gate(ws, "after_tasks")
            self.assertEqual(result.returncode, 1)
            self.assertIn("docker-container-required", result.stderr)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertTrue(feedback.exists())
            text = feedback.read_text(encoding="utf-8")
            self.assertIn("tasks-presence", text)
            self.assertIn("docker-container-required", text)

    def test_pure_tier2_produces_feedback_artifact(self):
        """Tier 2-only failures must still write gate_feedback.md."""
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            # Create a tasks file so the only finding is the docker Tier 2.
            (ws / "specs" / "feature-a").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-a" / "tasks.md").write_text("- [ ] task\n", encoding="utf-8")
            write_config_without_container(ws, "base", execution_mode="docker-fallback")
            result = self.run_gate(ws, "after_tasks")
            self.assertEqual(result.returncode, 1)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertTrue(feedback.exists())
            text = feedback.read_text(encoding="utf-8")
            self.assertIn("hard-halt", text)
            self.assertIn("docker-container-required", text)

    def test_tier1_escalates_after_max_retries(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")

            for _ in range(3):
                result = self.run_gate(ws, "after_tasks")
                self.assertEqual(result.returncode, 0)

            result = self.run_gate(ws, "after_tasks")
            self.assertEqual(result.returncode, 1)
            self.assertIn("tasks-presence-retry-exceeded", result.stderr)

    def test_multiple_findings_same_rule_increment_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            (ws / "specs" / "feature-a").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-a" / "system-design-plan.md").write_text(
                "\n".join(
                    [
                        "# Plan",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            text = feedback.read_text(encoding="utf-8")
            self.assertIn("- Rule: `plan-section-missing`", text)
            self.assertIn("- Retry: `1 / 3`", text)

            for _ in range(2):
                result = self.run_gate(ws, "after_plan")
                self.assertEqual(result.returncode, 0)

            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 1)
            self.assertIn("plan-section-missing-retry-exceeded", result.stderr)

    def test_tier1_retry_is_scoped_by_event_and_rule(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")

            for _ in range(3):
                result = self.run_gate(ws, "after_tasks")
                self.assertEqual(result.returncode, 0)

            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertIn("plan-presence", feedback.read_text(encoding="utf-8"))

    def test_heuristic_tier1_does_not_auto_escalate_with_default_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "fintech-banking")
            write_e2e_test(ws)
            ws.joinpath("payments.py").write_text(
                "\n".join(
                    [
                        "def payment_handler(req):",
                        "    idempotency_key = req.headers.get('Idempotency-Key')",
                        "    return {'ok': True}",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            for _ in range(5):
                result = self.run_gate(ws, "after_implement")
                self.assertEqual(result.returncode, 0)

    def test_heuristic_retry_escalates_false_string_does_not_escalate(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_e2e_test(ws)
            ws.joinpath(".itx-config.yml").write_text(
                "\n".join(
                    [
                        'domain: "fintech-banking"',
                        'execution_mode: "mcp"',
                        "docker:",
                        '  container_name: "sandbox"',
                        "gate:",
                        "  max_tier1_retries: 1",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            (ws / ".specify").mkdir(parents=True, exist_ok=True)
            (ws / ".specify" / "policy.yml").write_text(
                "\n".join(
                    [
                        "gate:",
                        "  default_max_tier1_retries: 1",
                        '  heuristic_retry_escalates: "false"',
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            ws.joinpath("payments.py").write_text(
                "\n".join(
                    [
                        "def payment_handler(req):",
                        "    idempotency_key = req.headers.get('Idempotency-Key')",
                        "    return {'ok': True}",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            for _ in range(3):
                result = self.run_gate(ws, "after_implement")
                self.assertEqual(result.returncode, 0)

    def test_invalid_retry_limit_falls_back_to_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            ws.joinpath(".itx-config.yml").write_text(
                "\n".join(
                    [
                        'domain: "base"',
                        'execution_mode: "mcp"',
                        "gate:",
                        '  max_tier1_retries: "nope"',
                        "docker:",
                        '  container_name: "sandbox"',
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_tasks")
            self.assertEqual(result.returncode, 0)
            self.assertIn("invalid gate.max_tier1_retries", result.stderr)

    def test_malformed_manifest_files_shape_is_ignored_with_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base", knowledge_mode="lazy")
            write_policy(ws)
            (ws / ".specify").mkdir(parents=True, exist_ok=True)
            (ws / ".specify" / "knowledge-manifest.json").write_text(
                json.dumps({"files": ["not", "a", "mapping"]}),
                encoding="utf-8",
            )
            (ws / "specs" / "feature-a").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-a" / "system-design-plan.md").write_text(
                "\n".join(
                    [
                        "# Plan",
                        "<!-- selected_patterns: none -->",
                        "## 4. Architectural Patterns Applied",
                        "- DDD",
                        "## 4b. Code-Level Design Patterns Applied",
                        "- Command + Handler",
                        "## 5. DDD Aggregates",
                        "- Order",
                        "## 13. Test Strategy",
                        "- E2E journey",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            self.assertIn("malformed knowledge-manifest.json", result.stderr)

    def test_validate_findings_drops_non_mapping_items(self):
        spec = importlib.util.spec_from_file_location("orchestrator_module", ORCH)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        validated = module.validate_findings(
            [
                "not-a-dict",
                {"severity": "tier1", "rule": "x", "message": "y"},
            ]
        )
        self.assertEqual(len(validated), 1)
        self.assertEqual(validated[0]["rule"], "x")

    def test_run_domain_checks_handles_non_list_validator_output(self):
        spec = importlib.util.spec_from_file_location("orchestrator_module", ORCH)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with mock.patch.object(module.importlib, "import_module") as patched_import:
            fake_module = mock.Mock()
            fake_module.run = mock.Mock(return_value={"not": "a-list"})
            patched_import.return_value = fake_module
            with mock.patch.dict(module.DOMAIN_VALIDATORS, {"fake-domain": "fake.validator"}, clear=False):
                findings = module.run_domain_checks("fake-domain", Path("."))

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule"], "validator-invalid-output")

    def test_banking_validator_handles_file_read_errors(self):
        module_path = ROOT / "extensions" / "itx-gates" / "hooks" / "validators" / "banking_heuristic.py"
        hooks_path = ROOT / "extensions" / "itx-gates" / "hooks"
        spec = importlib.util.spec_from_file_location("banking_validator_module", module_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        with mock.patch.object(sys, "path", [str(hooks_path), *sys.path]):
            spec.loader.exec_module(module)

        fake_path = mock.Mock()
        fake_path.name = "payments.py"
        fake_path.read_text.side_effect = OSError("permission denied")
        with mock.patch.object(module, "collect_code_files", return_value=[fake_path]):
            findings = module.run(Path("."))
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule"], "validator-file-read-failed")

    def test_healthcare_validator_handles_file_read_errors(self):
        module_path = ROOT / "extensions" / "itx-gates" / "hooks" / "validators" / "health_regex.py"
        hooks_path = ROOT / "extensions" / "itx-gates" / "hooks"
        spec = importlib.util.spec_from_file_location("health_validator_module", module_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        with mock.patch.object(sys, "path", [str(hooks_path), *sys.path]):
            spec.loader.exec_module(module)

        fake_path = mock.Mock()
        fake_path.read_text.side_effect = OSError("permission denied")
        with mock.patch.object(module, "collect_code_files", return_value=[fake_path]):
            findings = module.run(Path("."))
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule"], "validator-file-read-failed")

    def test_run_docker_exec_handles_missing_docker_binary(self):
        spec = importlib.util.spec_from_file_location("orchestrator_module", ORCH)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with mock.patch.object(module.subprocess, "run", side_effect=FileNotFoundError("docker")):
            result = module.run_docker_exec("sandbox", ["echo", "ping"])
        self.assertEqual(result.returncode, 127)
        self.assertIn("Docker CLI not found", result.stderr)

    def test_after_tasks_docker_missing_binary_returns_structured_tier2(self):
        spec = importlib.util.spec_from_file_location("orchestrator_module", ORCH)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            ws.joinpath(".itx-config.yml").write_text(
                "\n".join(
                    [
                        'domain: "base"',
                        'execution_mode: "docker-fallback"',
                        "docker:",
                        '  container_name: "sandbox"',
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            (ws / "specs" / "feature-a").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-a" / "tasks.md").write_text("- [ ] task\n", encoding="utf-8")
            with mock.patch.object(module.subprocess, "run", side_effect=FileNotFoundError("docker")):
                findings = module.run_generic_checks(
                    {"execution_mode": "docker-fallback", "docker": {"container_name": "sandbox"}},
                    "after_tasks",
                    ws,
                    {},
                )
        self.assertTrue(any(f.get("rule") == "docker-exec-failed" for f in findings))

    def test_after_plan_lazy_mode_same_source_target_no_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base", knowledge_mode="lazy")
            write_policy(ws)
            (ws / ".specify" / "patterns").mkdir(parents=True, exist_ok=True)
            same_path = ws / ".specify" / "patterns" / "domain-driven-design.md"
            same_path.write_text("# DDD\n", encoding="utf-8")
            (ws / ".specify" / "knowledge-manifest.json").write_text(
                json.dumps(
                    {
                        "files": {
                            "domain-driven-design.md": {
                                "category": "patterns",
                                "source": str(same_path),
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            (ws / "specs" / "feature-a").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-a" / "system-design-plan.md").write_text(
                "\n".join(
                    [
                        "# Plan",
                        "<!-- selected_patterns: domain-driven-design.md -->",
                        "## 4. Architectural Patterns Applied",
                        "- DDD",
                        "## 4b. Code-Level Design Patterns Applied",
                        "- Command + Handler",
                        "## 5. DDD Aggregates",
                        "- Order",
                        "## 13. Test Strategy",
                        "- E2E journey",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            self.assertIn("Gates passed", result.stdout)

    def test_feedback_contains_confidence_and_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "fintech-banking")
            write_e2e_test(ws)
            ws.joinpath("payments.py").write_text(
                "\n".join(
                    [
                        "def payment_handler(req):",
                        "    idempotency_key = req.headers.get('Idempotency-Key')",
                        "    return {'ok': True}",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            result = self.run_gate(ws, "after_implement")
            self.assertEqual(result.returncode, 0)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertTrue(feedback.exists())
            text = feedback.read_text(encoding="utf-8")
            self.assertIn("Confidence:", text)
            self.assertIn("Remediation Owner:", text)

    def test_tier2_does_not_increment_tier1_retry_counter(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config_without_container(ws, "base", execution_mode="docker-fallback")

            result = self.run_gate(ws, "after_tasks")
            self.assertEqual(result.returncode, 1)

            write_config(ws, "base")
            result = self.run_gate(ws, "after_tasks")
            self.assertEqual(result.returncode, 0)
            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            text = feedback.read_text(encoding="utf-8")
            self.assertIn("- Rule: `tasks-presence`", text)
            self.assertIn("- Retry: `1 / 3`", text)

    def test_default_policy_matches_policy_yml(self):
        spec = importlib.util.spec_from_file_location("orchestrator_module", ORCH)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        policy_path = ROOT / "presets" / "base" / "policy.yml"
        policy_data = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
        self.assertEqual(module._DEFAULT_POLICY, policy_data)

    def test_missing_policy_emits_warning_before_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            (ws / "specs" / "feature-a").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-a" / "tasks.md").write_text("- [ ] task\n", encoding="utf-8")
            result = self.run_gate(ws, "after_tasks")
            self.assertEqual(result.returncode, 0)
            self.assertIn("missing policy file", result.stderr)

    def test_invalid_policy_yaml_emits_warning_before_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            (ws / ".specify").mkdir(parents=True, exist_ok=True)
            (ws / ".specify" / "policy.yml").write_text("plan_tiers: [\n", encoding="utf-8")
            (ws / "specs" / "feature-a").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-a" / "tasks.md").write_text("- [ ] task\n", encoding="utf-8")
            result = self.run_gate(ws, "after_tasks")
            self.assertEqual(result.returncode, 0)
            self.assertIn("failed to parse policy file", result.stderr)

    def test_non_mapping_policy_emits_warning_before_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            (ws / ".specify").mkdir(parents=True, exist_ok=True)
            (ws / ".specify" / "policy.yml").write_text("- not-a-mapping\n", encoding="utf-8")
            (ws / "specs" / "feature-a").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-a" / "tasks.md").write_text("- [ ] task\n", encoding="utf-8")
            result = self.run_gate(ws, "after_tasks")
            self.assertEqual(result.returncode, 0)
            self.assertIn("is not a mapping", result.stderr)

    def test_gate_feedback_cleared_after_clean_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")

            first = self.run_gate(ws, "after_tasks")
            self.assertEqual(first.returncode, 0)

            feedback = ws / ".specify" / "context" / "gate_feedback.md"
            self.assertTrue(feedback.exists())
            self.assertIn("tasks-presence", feedback.read_text(encoding="utf-8"))

            (ws / "specs" / "feature-a").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-a" / "tasks.md").write_text("- [ ] task\n", encoding="utf-8")

            second = self.run_gate(ws, "after_tasks")
            self.assertEqual(second.returncode, 0)
            self.assertFalse(feedback.exists())

    def test_after_plan_generates_execution_brief(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base", knowledge_mode="lazy")
            write_policy(ws)
            (ws / "specs" / "feature-a").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-a" / "system-design-plan.md").write_text(
                "\n".join(
                    [
                        "# Plan",
                        "<!-- selected_patterns: domain-driven-design.md -->",
                        "## 1. Problem Statement",
                        "Refine order validation for better consistency.",
                        "## 2. Bounded Contexts Involved",
                        "- Orders",
                        "## 4. Architectural Patterns Applied",
                        "- DDD",
                        "## 4b. Code-Level Design Patterns Applied",
                        "- Command + Handler",
                        "## 5. DDD Aggregates",
                        "- Order",
                        "## 11. Risks and Mitigations",
                        "- Risk: regressions in checkout",
                        "## 13. Test Strategy",
                        "- Preserve checkout e2e path",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            brief = ws / ".specify" / "context" / "execution-brief.md"
            self.assertTrue(brief.exists())
            text = brief.read_text(encoding="utf-8")
            self.assertIn("# Execution Brief", text)
            self.assertIn("## Behavior Overlay", text)
            self.assertIn("## Verification Targets", text)
            self.assertIn("domain-driven-design.md", text)

    def test_after_tasks_execution_brief_includes_unchecked_tasks(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            (ws / "specs" / "feature-a").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-a" / "patch-plan.md").write_text(
                "\n".join(
                    [
                        "# Patch plan",
                        "## 1. Problem Statement",
                        "Fix validation edge-case.",
                        "## 2. Files / Modules Affected",
                        "- `src/service.py`",
                        "## 5. Regression Testing",
                        "- add regression test",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            (ws / "specs" / "feature-a" / "tasks.md").write_text(
                "\n".join(
                    [
                        "- [ ] T001 update `src/service.py` validation",
                        "- [x] T002 add docs note",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            result = self.run_gate(ws, "after_tasks")
            self.assertEqual(result.returncode, 0)
            brief = ws / ".specify" / "context" / "execution-brief.md"
            self.assertTrue(brief.exists())
            text = brief.read_text(encoding="utf-8")
            self.assertIn("## Next Actions", text)
            self.assertIn("T001 update", text)
            self.assertNotIn("T002 add docs note", text)

    def test_after_plan_major_refactor_creates_audit_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            (ws / "specs" / "feature-r").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-r" / "refactor-plan.md").write_text(
                "\n".join(
                    [
                        "---",
                        "work_class: refactor",
                        "---",
                        "# Refactor plan",
                        "## 1. Goal",
                        "Major cross-module refactor to isolate adapters.",
                        "## 2. Scope / Non-Scope",
                        "- In: `src/api.py`, `scripts/patch.py`, `extensions/itx-gates/hooks/orchestrator.py`",
                        "- Out: API contract changes",
                        "## 3. Invariants to Preserve",
                        "- API response shape unchanged",
                        "## 4. Public Contract Impact",
                        "None",
                        "## 5. Behavioral Equivalence Strategy",
                        "- Baseline/after snapshot comparison",
                        "## 6. Regression Strategy",
                        "- Keep integration regression suite green",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            audit_log = ws / ".specify" / "context" / "audit-log.md"
            self.assertTrue(audit_log.exists())
            text = audit_log.read_text(encoding="utf-8")
            self.assertIn("major-refactor", text)
            self.assertIn("high-risk-ops-change", text)

    def test_after_plan_low_risk_patch_does_not_create_audit_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            (ws / "specs" / "feature-p").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-p" / "patch-plan.md").write_text(
                "\n".join(
                    [
                        "# Patch plan",
                        "## 1. Problem Statement",
                        "Adjust a small formatting edge-case.",
                        "## 2. Files / Modules Affected",
                        "- `src/formatting.py`",
                        "## 5. Regression Testing",
                        "- add unit regression",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            audit_log = ws / ".specify" / "context" / "audit-log.md"
            self.assertFalse(audit_log.exists())

    def test_after_tasks_execution_brief_reflects_current_gate_feedback(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            (ws / "specs" / "feature-a").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-a" / "patch-plan.md").write_text(
                "\n".join(
                    [
                        "# Patch plan",
                        "## 1. Problem Statement",
                        "Fix validation edge-case.",
                        "## 2. Files / Modules Affected",
                        "- `src/service.py`",
                        "## 5. Regression Testing",
                        "- add regression test",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            result = self.run_gate(ws, "after_tasks")
            self.assertEqual(result.returncode, 0)
            brief = ws / ".specify" / "context" / "execution-brief.md"
            self.assertTrue(brief.exists())
            text = brief.read_text(encoding="utf-8")
            self.assertIn("tasks-presence", text)

    def test_after_plan_multiple_feature_plans_without_workflow_state_skips_brief(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            (ws / ".specify" / "context").mkdir(parents=True, exist_ok=True)
            (ws / ".specify" / "context" / "execution-brief.md").write_text("stale\n", encoding="utf-8")
            for feature in ("feature-a", "feature-b"):
                (ws / "specs" / feature).mkdir(parents=True, exist_ok=True)
                (ws / "specs" / feature / "patch-plan.md").write_text(
                    "\n".join(
                        [
                            "# Patch plan",
                            "## 1. Problem Statement",
                            f"Fix issue in {feature}.",
                            "## 2. Files / Modules Affected",
                            "- `src/service.py`",
                            "## 5. Regression Testing",
                            "- add regression test",
                            "",
                        ]
                    ),
                    encoding="utf-8",
                )

            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            brief = ws / ".specify" / "context" / "execution-brief.md"
            self.assertFalse(brief.exists())

    def test_after_plan_stale_workflow_state_feature_without_plan_skips_brief(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            write_workflow_state_feature(ws, "feature-a")
            (ws / ".specify" / "context").mkdir(parents=True, exist_ok=True)
            (ws / ".specify" / "context" / "execution-brief.md").write_text("stale\n", encoding="utf-8")
            (ws / "specs" / "feature-a").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-b").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-b" / "patch-plan.md").write_text(
                "\n".join(
                    [
                        "# Patch plan",
                        "## 1. Problem Statement",
                        "Fix issue in feature-b.",
                        "## 2. Files / Modules Affected",
                        "- `src/service.py`",
                        "## 5. Regression Testing",
                        "- add regression test",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            brief = ws / ".specify" / "context" / "execution-brief.md"
            self.assertFalse(brief.exists())

    def test_after_plan_feature_brief_does_not_promote_pattern_file_into_file_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            (ws / "specs" / "feature-a").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-a" / "system-design-plan.md").write_text(
                "\n".join(
                    [
                        "# Plan",
                        "<!-- selected_patterns: domain-driven-design.md -->",
                        "## 1. Problem Statement",
                        "Refine order validation for better consistency.",
                        "## 2. Bounded Contexts Involved",
                        "- Orders",
                        "## 4. Architectural Patterns Applied",
                        "- DDD",
                        "## 4b. Code-Level Design Patterns Applied",
                        "- Command + Handler",
                        "## 5. DDD Aggregates",
                        "- Order",
                        "## 13. Test Strategy",
                        "- Preserve checkout e2e path",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            brief = ws / ".specify" / "context" / "execution-brief.md"
            text = brief.read_text(encoding="utf-8")
            self.assertNotIn("## Files/Modules In Scope", text)
            self.assertIn("## Selected Patterns To Load", text)

    def test_after_plan_brief_does_not_pull_unrelated_workspace_tasks_without_workflow_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            (ws / "specs" / "feature-a").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-a" / "patch-plan.md").write_text(
                "\n".join(
                    [
                        "# Patch plan",
                        "## 1. Problem Statement",
                        "Fix validation edge-case.",
                        "## 2. Files / Modules Affected",
                        "- `src/service.py`",
                        "## 5. Regression Testing",
                        "- add regression test",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            (ws / "specs" / "feature-b").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-b" / "tasks.md").write_text(
                "- [ ] T999 unrelated task from feature-b\n",
                encoding="utf-8",
            )

            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            brief = ws / ".specify" / "context" / "execution-brief.md"
            self.assertTrue(brief.exists())
            text = brief.read_text(encoding="utf-8")
            self.assertNotIn("T999 unrelated task", text)

    def test_after_plan_lazy_mode_missing_pattern_selection_does_not_claim_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base", knowledge_mode="lazy")
            write_policy(ws)
            (ws / "specs" / "feature-a").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-a" / "system-design-plan.md").write_text(
                "\n".join(
                    [
                        "# Plan",
                        "## 1. Problem Statement",
                        "Refine order validation for better consistency.",
                        "## 4. Architectural Patterns Applied",
                        "- DDD",
                        "## 4b. Code-Level Design Patterns Applied",
                        "- Command + Handler",
                        "## 5. DDD Aggregates",
                        "- Order",
                        "## 13. Test Strategy",
                        "- Preserve checkout e2e path",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            brief = ws / ".specify" / "context" / "execution-brief.md"
            text = brief.read_text(encoding="utf-8")
            self.assertIn("knowledge-pattern-selection-missing", text)
            self.assertNotIn("## Selected Patterns To Load\n- none", text)

    def test_after_plan_manifest_mention_without_install_does_not_create_audit_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            (ws / "specs" / "feature-p").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-p" / "patch-plan.md").write_text(
                "\n".join(
                    [
                        "# Patch plan",
                        "## 1. Problem Statement",
                        "Review dependency policy around pyproject.toml without changing packages.",
                        "## 2. Files / Modules Affected",
                        "- `docs/architecture.md`",
                        "## 5. Regression Testing",
                        "- docs-only check",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            audit_log = ws / ".specify" / "context" / "audit-log.md"
            self.assertFalse(audit_log.exists())

    def test_after_plan_deployment_wording_without_high_risk_scope_does_not_create_audit_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            (ws / "specs" / "feature-p").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-p" / "patch-plan.md").write_text(
                "\n".join(
                    [
                        "# Patch plan",
                        "## 1. Problem Statement",
                        "Discuss deployment strategy and infrastructure notes for docs.",
                        "## 2. Files / Modules Affected",
                        "- `docs/architecture.md`",
                        "## 5. Regression Testing",
                        "- docs-only check",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            audit_log = ws / ".specify" / "context" / "audit-log.md"
            self.assertFalse(audit_log.exists())

    def test_after_plan_explicit_package_install_creates_audit_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            (ws / "specs" / "feature-pkg").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-pkg" / "patch-plan.md").write_text(
                "\n".join(
                    [
                        "# Patch plan",
                        "## 1. Problem Statement",
                        "Run pip install httpx to support a new adapter test.",
                        "## 2. Files / Modules Affected",
                        "- `requirements-dev.txt`",
                        "## 5. Regression Testing",
                        "- adapter regression test",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            audit_log = ws / ".specify" / "context" / "audit-log.md"
            self.assertTrue(audit_log.exists())
            self.assertIn("package-install-remove", audit_log.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
