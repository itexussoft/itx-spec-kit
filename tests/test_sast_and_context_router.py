import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "extensions" / "itx-gates" / "hooks"))


class SastAndContextRouterTests(unittest.TestCase):
    def test_semgrep_provider_maps_sql_injection_to_tier2(self):
        from security_providers import semgrep_provider

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            rules = ws / "rules.yml"
            rules.write_text("rules: []\n", encoding="utf-8")
            semgrep_output = {
                "results": [
                    {
                        "check_id": "banking-sql-injection-ledger-query",
                        "path": "ledger.py",
                        "start": {"line": 42},
                        "extra": {
                            "message": "Potential SQL injection in ledger query execution.",
                            "severity": "ERROR",
                        },
                    }
                ]
            }
            with (
                patch("security_providers.semgrep_provider.shutil.which", return_value="/usr/bin/semgrep"),
                patch(
                    "security_providers.semgrep_provider.subprocess.run",
                    return_value=type(
                        "Result",
                        (),
                        {"returncode": 1, "stdout": json.dumps(semgrep_output), "stderr": ""},
                    )(),
                ),
            ):
                findings = semgrep_provider.run(
                    ws,
                    {
                        "semgrep_rules": str(rules),
                        "on_missing_binary": "warn",
                    },
                )
            self.assertEqual(len(findings), 1)
            finding = findings[0]
            self.assertEqual(finding["rule"], "banking-sql-injection-ledger-query")
            self.assertEqual(finding["severity"], "tier2")
            self.assertIn("ledger.py:42", finding["message"])

    def test_lazy_router_after_tasks_avoids_ledger_for_frontend_only_tasks(self):
        from orchestrator_brief import _sync_lazy_knowledge

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / ".specify").mkdir(parents=True, exist_ok=True)
            (ws / ".specify" / "patterns").mkdir(parents=True, exist_ok=True)
            store = ws / ".specify" / ".knowledge-store" / "patterns"
            store.mkdir(parents=True, exist_ok=True)

            (store / "event-sourced-ledger.md").write_text("# Event sourced ledger\n", encoding="utf-8")
            (store / "frontend-widget-architecture.md").write_text("# Frontend widget architecture\n", encoding="utf-8")

            manifest = {
                "schema_version": "1.1",
                "files": {
                    "event-sourced-ledger.md": {
                        "category": "patterns",
                        "source": str(store / "event-sourced-ledger.md"),
                        "tags": ["ledger", "db", "sql", "transaction"],
                        "phases": ["after_plan", "after_tasks", "after_review"],
                        "token_estimate": 300,
                    },
                    "frontend-widget-architecture.md": {
                        "category": "patterns",
                        "source": str(store / "frontend-widget-architecture.md"),
                        "tags": ["frontend", "ui", "component"],
                        "phases": ["after_plan", "after_tasks", "after_review"],
                        "token_estimate": 250,
                    },
                },
            }
            (ws / ".specify" / "knowledge-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

            (ws / ".itx-config.yml").write_text(
                "\n".join(
                    [
                        'domain: "fintech-banking"',
                        'execution_mode: "mcp"',
                        "knowledge:",
                        '  mode: "lazy"',
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            specs = ws / "specs" / "feature-frontend"
            specs.mkdir(parents=True, exist_ok=True)
            (specs / "system-design-plan.md").write_text(
                "\n".join(
                    [
                        "---",
                        "work_class: patch",
                        "---",
                        "# Plan",
                        "## 1. Problem Statement",
                        "Frontend-only interaction update for dashboard widget.",
                        "## 2. Files / Modules Affected",
                        "- web/src/components/BalanceWidget.tsx",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            (specs / "tasks.md").write_text(
                "\n".join(
                    [
                        "# Tasks",
                        "- [ ] Build frontend component interaction and UI states",
                        "- [ ] Add React unit tests for component behavior",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            findings = _sync_lazy_knowledge(
                {"knowledge": {"mode": "lazy"}},
                ws,
                {"work_classes": {"patch": {"pattern_selection": "optional"}}},
                event="after_tasks",
            )
            self.assertEqual(findings, [])
            self.assertTrue((ws / ".specify" / "patterns" / "frontend-widget-architecture.md").exists())
            self.assertFalse((ws / ".specify" / "patterns" / "event-sourced-ledger.md").exists())


if __name__ == "__main__":
    unittest.main()
