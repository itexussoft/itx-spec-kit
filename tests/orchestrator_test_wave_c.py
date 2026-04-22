import subprocess
import tempfile
import unittest
from pathlib import Path

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


def write_policy(workspace: Path) -> None:
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


class OrchestratorWaveCTests(unittest.TestCase):
    def run_gate(self, workspace: Path, event: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["python3", str(ORCH), "--event", event, "--workspace", str(workspace)],
            check=False,
            capture_output=True,
            text=True,
        )

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
            (ws / "specs" / "feature-b" / "tasks.md").write_text("- [ ] T999 unrelated task from feature-b\n", encoding="utf-8")

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

    def test_after_plan_addendum_overlays_are_selected_when_relevant(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            (ws / "specs" / "feature-addendum").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-addendum" / "patch-plan.md").write_text(
                "\n".join(
                    [
                        "# Patch plan",
                        "<!-- selected_patterns: adapter-anti-corruption.md -->",
                        "## 1. Problem Statement",
                        "Modify existing behavior for a public API endpoint using OAuth token checks and rate limit controls.",
                        "## 2. Files / Modules Affected",
                        "- `src/integrations/vendor_client.py`",
                        "- `src/api/public.py`",
                        "## 5. Regression Testing",
                        "- add failing regression test before code change",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            brief = ws / ".specify" / "context" / "execution-brief.md"
            text = brief.read_text(encoding="utf-8")
            self.assertIn("## Targeted Micro-Overlays", text)
            self.assertIn("ACL boundary", text)
            self.assertIn("Security/auth-secrets", text)
            self.assertIn("Security/OWASP", text)
            self.assertIn("Security/rate-limiting", text)
            self.assertIn("TDD loop", text)

    def test_after_plan_brief_includes_active_context_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            (ws / "specs" / "feature-context").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-context" / "patch-plan.md").write_text(
                "\n".join(
                    [
                        "# Patch plan",
                        "## 1. Problem Statement",
                        "Adjust an internal formatting helper.",
                        "## 2. Files / Modules Affected",
                        "- `src/formatting.py`",
                        "## 5. Regression Testing",
                        "- add integration regression",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            brief = ws / ".specify" / "context" / "execution-brief.md"
            text = brief.read_text(encoding="utf-8")
            self.assertIn("## Active Context", text)
            self.assertIn("active context snapshot", text)

    def test_after_plan_audit_log_includes_why_and_expected_outcome(self):
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
            text = audit_log.read_text(encoding="utf-8")
            self.assertIn("- Why:", text)
            self.assertIn("- Expected Outcome:", text)

    def test_after_plan_auth_overlay_not_triggered_by_author_header_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            (ws / "specs" / "feature-author-only").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-author-only" / "patch-plan.md").write_text(
                "\n".join(
                    [
                        "# Patch plan",
                        "## 1. Problem Statement",
                        "Adjust internal markdown rendering for docs output.",
                        "## 2. Files / Modules Affected",
                        "- `src/docs/render.py`",
                        "## 5. Regression Testing",
                        "- docs integration regression",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            brief = ws / ".specify" / "context" / "execution-brief.md"
            text = brief.read_text(encoding="utf-8")
            self.assertNotIn("Security/auth-secrets", text)

    def test_after_plan_acl_overlay_not_triggered_by_internal_integration_wording(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            (ws / "specs" / "feature-internal-integration").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-internal-integration" / "patch-plan.md").write_text(
                "\n".join(
                    [
                        "# Patch plan",
                        "## 1. Problem Statement",
                        "Improve integration regression coverage for internal module boundaries.",
                        "## 2. Files / Modules Affected",
                        "- `src/internal/integration_runner.py`",
                        "## 5. Regression Testing",
                        "- internal integration regression",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            brief = ws / ".specify" / "context" / "execution-brief.md"
            text = brief.read_text(encoding="utf-8")
            self.assertNotIn("ACL boundary", text)

    def test_after_plan_structure_only_refactor_does_not_force_tdd_overlay(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            (ws / "specs" / "feature-refactor-structure").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-refactor-structure" / "refactor-plan.md").write_text(
                "\n".join(
                    [
                        "---",
                        "work_class: refactor",
                        "---",
                        "# Refactor plan",
                        "## 1. Goal",
                        "Reshape package layout to improve module ownership.",
                        "## 2. Scope / Non-Scope",
                        "- In: module relocation only",
                        "- Out: behavior changes",
                        "## 3. Invariants to Preserve",
                        "- Public behavior unchanged",
                        "## 4. Public Contract Impact",
                        "None",
                        "## 5. Behavioral Equivalence Strategy",
                        "- Snapshot equivalence checks",
                        "## 6. Regression Strategy",
                        "- keep current regression suite green",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            brief = ws / ".specify" / "context" / "execution-brief.md"
            text = brief.read_text(encoding="utf-8")
            self.assertNotIn("TDD loop", text)

    def test_after_plan_generic_request_input_query_words_do_not_force_owasp_overlay(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            write_config(ws, "base")
            write_policy(ws)
            (ws / "specs" / "feature-generic-words").mkdir(parents=True, exist_ok=True)
            (ws / "specs" / "feature-generic-words" / "patch-plan.md").write_text(
                "\n".join(
                    [
                        "# Patch plan",
                        "## 1. Problem Statement",
                        "Improve internal request parsing and query formatting for analytics input files.",
                        "## 2. Files / Modules Affected",
                        "- `src/analytics/parser.py`",
                        "## 5. Regression Testing",
                        "- analytics integration regression",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            result = self.run_gate(ws, "after_plan")
            self.assertEqual(result.returncode, 0)
            brief = ws / ".specify" / "context" / "execution-brief.md"
            text = brief.read_text(encoding="utf-8")
            self.assertNotIn("Security/OWASP", text)
