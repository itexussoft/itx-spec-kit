import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "extensions" / "itx-gates" / "hooks"))
sys.path.insert(0, str(ROOT / "scripts"))


class SastAndContextRouterTests(unittest.TestCase):
    def test_build_manifest_emits_anti_tags_from_frontmatter(self):
        from build_knowledge_manifest import build_manifest

        banking_manifest = build_manifest(ROOT, "fintech-banking")
        ledger = banking_manifest["files"]["event-sourced-ledger.md"]
        self.assertIn("anti_tags", ledger)
        self.assertIn("react", ledger["anti_tags"])
        self.assertIn("frontend", ledger["anti_tags"])

        saga = banking_manifest["files"]["saga-distributed-transactions.md"]
        self.assertIn("anti_tags", saga)
        self.assertIn("react", saga["anti_tags"])

        ledger_commands = banking_manifest["files"]["command-pattern-ledger.md"]
        self.assertIn("anti_tags", ledger_commands)
        self.assertIn("palette", ledger_commands["anti_tags"])

        in_place_balance = banking_manifest["files"]["in-place-balance-updates.md"]
        self.assertIn("anti_tags", in_place_balance)
        self.assertIn("widget", in_place_balance["anti_tags"])

        base_manifest = build_manifest(ROOT, "base")
        outbox = base_manifest["files"]["transactional-outbox.md"]
        self.assertIn("anti_tags", outbox)
        self.assertIn("click", outbox["anti_tags"])

        event_driven = base_manifest["files"]["event-driven-microservices.md"]
        self.assertIn("anti_tags", event_driven)
        self.assertIn("dom", event_driven["anti_tags"])

        async_loop = base_manifest["files"]["asynchronous-event-loop-architecture.md"]
        self.assertIn("anti_tags", async_loop)
        self.assertIn("modal", async_loop["anti_tags"])

        cli_orchestrator = base_manifest["files"]["cli-orchestrator-architecture.md"]
        self.assertIn("anti_tags", cli_orchestrator)
        self.assertIn("palette", cli_orchestrator["anti_tags"])

        over_engineered_cli = base_manifest["files"]["over-engineered-cli.md"]
        self.assertIn("anti_tags", over_engineered_cli)
        self.assertIn("shortcut", over_engineered_cli["anti_tags"])

        trading_manifest = build_manifest(ROOT, "fintech-trading")
        cqrs = trading_manifest["files"]["cqrs-order-sequencing.md"]
        self.assertIn("anti_tags", cqrs)
        self.assertIn("table", cqrs["anti_tags"])

        lifecycle = trading_manifest["files"]["state-pattern-order-lifecycle.md"]
        self.assertIn("anti_tags", lifecycle)
        self.assertIn("modal", lifecycle["anti_tags"])

        saas_manifest = build_manifest(ROOT, "saas-platform")
        isolation = saas_manifest["files"]["multi-tenant-data-isolation.md"]
        self.assertIn("anti_tags", isolation)
        self.assertIn("theme", isolation["anti_tags"])

        tenant_context = saas_manifest["files"]["tenant-context-middleware.md"]
        self.assertIn("anti_tags", tenant_context)
        self.assertIn("provider", tenant_context["anti_tags"])

        leakage = saas_manifest["files"]["cross-tenant-data-leakage.md"]
        self.assertIn("anti_tags", leakage)
        self.assertIn("branding", leakage["anti_tags"])

        procurement_manifest = build_manifest(ROOT, "procurement-guarantees")
        flow = procurement_manifest["files"]["configurable-flow-metamodel.md"]
        self.assertIn("anti_tags", flow)
        self.assertIn("react", flow["anti_tags"])

        lifecycle = procurement_manifest["files"]["dual-state-machine-application-track.md"]
        self.assertIn("anti_tags", lifecycle)
        self.assertIn("table", lifecycle["anti_tags"])

        status_bypass = procurement_manifest["files"]["implicit-status-bypass.md"]
        self.assertIn("anti_tags", status_bypass)
        self.assertIn("badge", status_bypass["anti_tags"])

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

    def test_lazy_router_refund_request_prefers_api_and_saga_over_ledger_ui_collision(self):
        from orchestrator_brief import _sync_lazy_knowledge

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / ".specify").mkdir(parents=True, exist_ok=True)
            (ws / ".specify" / "patterns").mkdir(parents=True, exist_ok=True)
            store = ws / ".specify" / ".knowledge-store" / "patterns"
            store.mkdir(parents=True, exist_ok=True)

            (store / "event-sourced-ledger.md").write_text("# Event sourced ledger\n", encoding="utf-8")
            (store / "saga-distributed-transactions.md").write_text("# Saga distributed transactions\n", encoding="utf-8")
            (store / "psd2-api-gateway.md").write_text("# PSD2 API gateway\n", encoding="utf-8")

            manifest = {
                "schema_version": "1.1",
                "files": {
                    "event-sourced-ledger.md": {
                        "category": "patterns",
                        "source": str(store / "event-sourced-ledger.md"),
                        "tags": ["ledger", "transaction", "db", "sql"],
                        "anti_tags": ["react", "frontend", "ui", "component"],
                        "phases": ["after_plan", "after_tasks", "after_review"],
                        "token_estimate": 300,
                    },
                    "saga-distributed-transactions.md": {
                        "category": "patterns",
                        "source": str(store / "saga-distributed-transactions.md"),
                        "tags": ["saga", "refund", "transaction", "processing"],
                        "anti_tags": [],
                        "phases": ["after_plan", "after_tasks", "after_review"],
                        "token_estimate": 280,
                    },
                    "psd2-api-gateway.md": {
                        "category": "patterns",
                        "source": str(store / "psd2-api-gateway.md"),
                        "tags": ["api", "endpoint", "controller", "idempotency"],
                        "anti_tags": [],
                        "phases": ["after_plan", "after_tasks", "after_review"],
                        "token_estimate": 260,
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

            specs = ws / "specs" / "refund-button"
            specs.mkdir(parents=True, exist_ok=True)
            request = (
                "Add a 'Refund' button to the React transaction history component. "
                "When clicked, it should call the POST /api/v1/refund endpoint with a newly "
                "generated UUID idempotency key, and gracefully display a warning toast if the "
                "server returns a 409 Conflict (indicating the refund saga is already processing)."
            )
            (specs / "modify-plan.md").write_text(
                "\n".join(
                    [
                        "---",
                        "work_class: modify",
                        "---",
                        "# Modify plan",
                        "## 1. Problem Statement",
                        request,
                        "## 2. Files / Modules Affected",
                        "- web/src/components/TransactionHistory.tsx",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            findings = _sync_lazy_knowledge(
                {"knowledge": {"mode": "lazy"}},
                ws,
                {"work_classes": {"modify": {"pattern_selection": "optional"}}},
                event="after_plan",
            )
            self.assertEqual(findings, [])
            self.assertTrue((ws / ".specify" / "patterns" / "saga-distributed-transactions.md").exists())
            self.assertTrue((ws / ".specify" / "patterns" / "psd2-api-gateway.md").exists())
            self.assertFalse((ws / ".specify" / "patterns" / "event-sourced-ledger.md").exists())

    def test_lazy_router_avoids_event_backends_for_frontend_click_event_request(self):
        from orchestrator_brief import _sync_lazy_knowledge

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / ".specify").mkdir(parents=True, exist_ok=True)
            (ws / ".specify" / "patterns").mkdir(parents=True, exist_ok=True)
            store = ws / ".specify" / ".knowledge-store" / "patterns"
            store.mkdir(parents=True, exist_ok=True)

            (store / "event-driven-microservices.md").write_text("# Event-driven microservices\n", encoding="utf-8")
            (store / "transactional-outbox.md").write_text("# Transactional outbox\n", encoding="utf-8")
            (store / "frontend-widget-architecture.md").write_text("# Frontend widget architecture\n", encoding="utf-8")

            manifest = {
                "schema_version": "1.1",
                "files": {
                    "event-driven-microservices.md": {
                        "category": "patterns",
                        "source": str(store / "event-driven-microservices.md"),
                        "tags": ["event", "messaging", "broker", "consumer", "command"],
                        "anti_tags": ["react", "frontend", "ui", "component", "click", "dom"],
                        "phases": ["after_plan", "after_tasks", "after_review"],
                        "token_estimate": 320,
                    },
                    "transactional-outbox.md": {
                        "category": "patterns",
                        "source": str(store / "transactional-outbox.md"),
                        "tags": ["transaction", "outbox", "event", "database", "relay"],
                        "anti_tags": ["react", "frontend", "ui", "component", "button", "click"],
                        "phases": ["after_plan", "after_tasks", "after_review"],
                        "token_estimate": 300,
                    },
                    "frontend-widget-architecture.md": {
                        "category": "patterns",
                        "source": str(store / "frontend-widget-architecture.md"),
                        "tags": ["frontend", "ui", "react", "component", "button", "toast"],
                        "anti_tags": [],
                        "phases": ["after_plan", "after_tasks", "after_review"],
                        "token_estimate": 240,
                    },
                },
            }
            (ws / ".specify" / "knowledge-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            (ws / ".itx-config.yml").write_text(
                "\n".join(
                    [
                        'domain: "base"',
                        'execution_mode: "mcp"',
                        "knowledge:",
                        '  mode: "lazy"',
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            specs = ws / "specs" / "frontend-event"
            specs.mkdir(parents=True, exist_ok=True)
            request = (
                "Add a click event handler to the React notification component so the button "
                "opens a warning toast and updates the UI state without a page refresh."
            )
            (specs / "modify-plan.md").write_text(
                "\n".join(
                    [
                        "---",
                        "work_class: modify",
                        "---",
                        "# Modify plan",
                        "## 1. Problem Statement",
                        request,
                        "## 2. Files / Modules Affected",
                        "- web/src/components/NotificationBell.tsx",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            findings = _sync_lazy_knowledge(
                {"knowledge": {"mode": "lazy"}},
                ws,
                {"work_classes": {"modify": {"pattern_selection": "optional"}}},
                event="after_plan",
            )
            self.assertEqual(findings, [])
            self.assertTrue((ws / ".specify" / "patterns" / "frontend-widget-architecture.md").exists())
            self.assertFalse((ws / ".specify" / "patterns" / "event-driven-microservices.md").exists())
            self.assertFalse((ws / ".specify" / "patterns" / "transactional-outbox.md").exists())

    def test_lazy_router_avoids_trading_backend_order_patterns_for_frontend_history_request(self):
        from orchestrator_brief import _sync_lazy_knowledge

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / ".specify").mkdir(parents=True, exist_ok=True)
            (ws / ".specify" / "patterns").mkdir(parents=True, exist_ok=True)
            (ws / ".specify" / "design-patterns").mkdir(parents=True, exist_ok=True)
            pattern_store = ws / ".specify" / ".knowledge-store" / "patterns"
            design_store = ws / ".specify" / ".knowledge-store" / "design-patterns"
            pattern_store.mkdir(parents=True, exist_ok=True)
            design_store.mkdir(parents=True, exist_ok=True)

            (pattern_store / "cqrs-order-sequencing.md").write_text("# CQRS order sequencing\n", encoding="utf-8")
            (design_store / "state-pattern-order-lifecycle.md").write_text("# State pattern order lifecycle\n", encoding="utf-8")
            (pattern_store / "frontend-widget-architecture.md").write_text("# Frontend widget architecture\n", encoding="utf-8")

            manifest = {
                "schema_version": "1.1",
                "files": {
                    "cqrs-order-sequencing.md": {
                        "category": "patterns",
                        "source": str(pattern_store / "cqrs-order-sequencing.md"),
                        "tags": ["cqrs", "order", "sequencing", "command", "projection"],
                        "anti_tags": ["react", "frontend", "ui", "component", "table", "grid", "button"],
                        "phases": ["after_plan", "after_tasks", "after_review"],
                        "token_estimate": 320,
                    },
                    "state-pattern-order-lifecycle.md": {
                        "category": "design-patterns",
                        "source": str(design_store / "state-pattern-order-lifecycle.md"),
                        "tags": ["state-machine", "order", "lifecycle", "transition", "settlement"],
                        "anti_tags": ["react", "frontend", "ui", "component", "table", "modal", "toast"],
                        "phases": ["after_plan", "after_tasks", "after_review"],
                        "token_estimate": 280,
                    },
                    "frontend-widget-architecture.md": {
                        "category": "patterns",
                        "source": str(pattern_store / "frontend-widget-architecture.md"),
                        "tags": ["frontend", "ui", "react", "component", "table", "status", "badge"],
                        "anti_tags": [],
                        "phases": ["after_plan", "after_tasks", "after_review"],
                        "token_estimate": 220,
                    },
                },
            }
            (ws / ".specify" / "knowledge-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            (ws / ".itx-config.yml").write_text(
                "\n".join(
                    [
                        'domain: "fintech-trading"',
                        'execution_mode: "mcp"',
                        "knowledge:",
                        '  mode: "lazy"',
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            specs = ws / "specs" / "order-history-ui"
            specs.mkdir(parents=True, exist_ok=True)
            request = (
                "Add sorting and status badges to the React order history table, and open a details "
                "modal when a row is clicked so traders can review the latest UI state."
            )
            (specs / "modify-plan.md").write_text(
                "\n".join(
                    [
                        "---",
                        "work_class: modify",
                        "---",
                        "# Modify plan",
                        "## 1. Problem Statement",
                        request,
                        "## 2. Files / Modules Affected",
                        "- web/src/components/OrderHistoryTable.tsx",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            findings = _sync_lazy_knowledge(
                {"knowledge": {"mode": "lazy"}},
                ws,
                {"work_classes": {"modify": {"pattern_selection": "optional"}}},
                event="after_plan",
            )
            self.assertEqual(findings, [])
            self.assertTrue((ws / ".specify" / "patterns" / "frontend-widget-architecture.md").exists())
            self.assertFalse((ws / ".specify" / "patterns" / "cqrs-order-sequencing.md").exists())
            self.assertFalse((ws / ".specify" / "design-patterns" / "state-pattern-order-lifecycle.md").exists())

    def test_lazy_router_avoids_saas_backend_context_patterns_for_frontend_theming_request(self):
        from orchestrator_brief import _sync_lazy_knowledge

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / ".specify").mkdir(parents=True, exist_ok=True)
            (ws / ".specify" / "patterns").mkdir(parents=True, exist_ok=True)
            (ws / ".specify" / "design-patterns").mkdir(parents=True, exist_ok=True)
            (ws / ".specify" / "anti-patterns").mkdir(parents=True, exist_ok=True)
            pattern_store = ws / ".specify" / ".knowledge-store" / "patterns"
            design_store = ws / ".specify" / ".knowledge-store" / "design-patterns"
            anti_store = ws / ".specify" / ".knowledge-store" / "anti-patterns"
            pattern_store.mkdir(parents=True, exist_ok=True)
            design_store.mkdir(parents=True, exist_ok=True)
            anti_store.mkdir(parents=True, exist_ok=True)

            (pattern_store / "multi-tenant-data-isolation.md").write_text("# Multi-tenant data isolation\n", encoding="utf-8")
            (design_store / "tenant-context-middleware.md").write_text("# Tenant context middleware\n", encoding="utf-8")
            (pattern_store / "white-label-theming-architecture.md").write_text("# White-label theming architecture\n", encoding="utf-8")
            (anti_store / "cross-tenant-data-leakage.md").write_text("# Cross-tenant data leakage\n", encoding="utf-8")

            manifest = {
                "schema_version": "1.1",
                "files": {
                    "multi-tenant-data-isolation.md": {
                        "category": "patterns",
                        "source": str(pattern_store / "multi-tenant-data-isolation.md"),
                        "tags": ["tenant", "isolation", "rls", "schema", "database", "cache"],
                        "anti_tags": ["react", "frontend", "ui", "theme", "theming", "branding", "logo", "color"],
                        "phases": ["after_plan", "after_tasks", "after_review"],
                        "token_estimate": 320,
                    },
                    "tenant-context-middleware.md": {
                        "category": "design-patterns",
                        "source": str(design_store / "tenant-context-middleware.md"),
                        "tags": ["tenant", "context", "middleware", "propagation", "request", "header"],
                        "anti_tags": ["react", "frontend", "ui", "provider", "hook", "theme", "modal"],
                        "phases": ["after_plan", "after_tasks", "after_review"],
                        "token_estimate": 260,
                    },
                    "white-label-theming-architecture.md": {
                        "category": "patterns",
                        "source": str(pattern_store / "white-label-theming-architecture.md"),
                        "tags": ["tenant", "theme", "theming", "branding", "logo", "color", "typography"],
                        "anti_tags": [],
                        "phases": ["after_plan", "after_tasks", "after_review"],
                        "token_estimate": 220,
                    },
                    "cross-tenant-data-leakage.md": {
                        "category": "anti-patterns",
                        "source": str(anti_store / "cross-tenant-data-leakage.md"),
                        "tags": ["tenant", "leakage", "isolation", "cache", "query", "tenant_id"],
                        "anti_tags": ["react", "frontend", "ui", "theme", "theming", "branding", "logo", "color"],
                        "phases": ["after_plan", "after_tasks", "after_review"],
                        "token_estimate": 240,
                    },
                },
            }
            (ws / ".specify" / "knowledge-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            (ws / ".itx-config.yml").write_text(
                "\n".join(
                    [
                        'domain: "saas-platform"',
                        'execution_mode: "mcp"',
                        "knowledge:",
                        '  mode: "lazy"',
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            specs = ws / "specs" / "tenant-theme-ui"
            specs.mkdir(parents=True, exist_ok=True)
            request = (
                "Add a React TenantContext provider and tenant-aware theme switcher so each customer "
                "sees the right logo, colors, and typography in the dashboard UI."
            )
            (specs / "modify-plan.md").write_text(
                "\n".join(
                    [
                        "---",
                        "work_class: modify",
                        "---",
                        "# Modify plan",
                        "## 1. Problem Statement",
                        request,
                        "## 2. Files / Modules Affected",
                        "- web/src/theme/TenantThemeProvider.tsx",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            findings = _sync_lazy_knowledge(
                {"knowledge": {"mode": "lazy"}},
                ws,
                {"work_classes": {"modify": {"pattern_selection": "optional"}}},
                event="after_plan",
            )
            self.assertEqual(findings, [])
            self.assertTrue((ws / ".specify" / "patterns" / "white-label-theming-architecture.md").exists())
            self.assertFalse((ws / ".specify" / "patterns" / "multi-tenant-data-isolation.md").exists())
            self.assertFalse((ws / ".specify" / "design-patterns" / "tenant-context-middleware.md").exists())
            self.assertFalse((ws / ".specify" / "anti-patterns" / "cross-tenant-data-leakage.md").exists())

    def test_lazy_router_avoids_cli_antipattern_for_frontend_command_palette_request(self):
        from orchestrator_brief import _sync_lazy_knowledge

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / ".specify").mkdir(parents=True, exist_ok=True)
            (ws / ".specify" / "patterns").mkdir(parents=True, exist_ok=True)
            (ws / ".specify" / "anti-patterns").mkdir(parents=True, exist_ok=True)
            pattern_store = ws / ".specify" / ".knowledge-store" / "patterns"
            anti_store = ws / ".specify" / ".knowledge-store" / "anti-patterns"
            pattern_store.mkdir(parents=True, exist_ok=True)
            anti_store.mkdir(parents=True, exist_ok=True)

            (pattern_store / "frontend-widget-architecture.md").write_text("# Frontend widget architecture\n", encoding="utf-8")
            (anti_store / "over-engineered-cli.md").write_text("# Over-engineered CLI\n", encoding="utf-8")

            manifest = {
                "schema_version": "1.1",
                "files": {
                    "frontend-widget-architecture.md": {
                        "category": "patterns",
                        "source": str(pattern_store / "frontend-widget-architecture.md"),
                        "tags": ["frontend", "ui", "react", "component", "palette", "shortcut", "modal"],
                        "anti_tags": [],
                        "phases": ["after_plan", "after_tasks", "after_review"],
                        "token_estimate": 220,
                    },
                    "over-engineered-cli.md": {
                        "category": "anti-patterns",
                        "source": str(anti_store / "over-engineered-cli.md"),
                        "tags": ["cli", "orchestrator", "command", "workflow", "automation", "subprocess"],
                        "anti_tags": ["react", "frontend", "ui", "palette", "toolbar", "menu", "shortcut", "modal"],
                        "phases": ["after_plan", "after_tasks", "after_review"],
                        "token_estimate": 240,
                    },
                },
            }
            (ws / ".specify" / "knowledge-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            (ws / ".itx-config.yml").write_text(
                "\n".join(
                    [
                        'domain: "base"',
                        'execution_mode: "mcp"',
                        "knowledge:",
                        '  mode: "lazy"',
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            specs = ws / "specs" / "command-palette"
            specs.mkdir(parents=True, exist_ok=True)
            request = (
                "Add a React command palette with keyboard shortcuts and a modal search UI so users "
                "can jump between dashboard actions quickly."
            )
            (specs / "modify-plan.md").write_text(
                "\n".join(
                    [
                        "---",
                        "work_class: modify",
                        "---",
                        "# Modify plan",
                        "## 1. Problem Statement",
                        request,
                        "## 2. Files / Modules Affected",
                        "- web/src/components/CommandPalette.tsx",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            findings = _sync_lazy_knowledge(
                {"knowledge": {"mode": "lazy"}},
                ws,
                {"work_classes": {"modify": {"pattern_selection": "optional"}}},
                event="after_plan",
            )
            self.assertEqual(findings, [])
            self.assertTrue((ws / ".specify" / "patterns" / "frontend-widget-architecture.md").exists())
            self.assertFalse((ws / ".specify" / "anti-patterns" / "over-engineered-cli.md").exists())


if __name__ == "__main__":
    unittest.main()
