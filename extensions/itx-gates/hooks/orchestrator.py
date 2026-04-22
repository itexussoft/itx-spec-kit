#!/usr/bin/env python3
"""Itexus gates orchestrator implementing Tier 1/Tier 2 flow control."""

from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import importlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Literal, Mapping, Sequence, cast

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validators import Finding, should_skip_path

TIER_1: Literal["tier1"] = "tier1"
TIER_2: Literal["tier2"] = "tier2"
RETRY_STATE_PREFIX = "- Retry-State: `"


DOMAIN_VALIDATORS: Dict[str, str] = {
    "fintech-trading": "validators.trading_ast",
    "fintech-banking": "validators.banking_heuristic",
    "healthcare": "validators.health_regex",
    "saas-platform": "validators.saas_platform_heuristic",
}

# Inline fallback used when policy.yml is not available in the workspace.
_DEFAULT_POLICY: Dict[str, Any] = {
    "work_classes": {
        "feature": {
            "allowed_templates": ["system-design-plan-template.md"],
            "mandatory_sections": [
                "## 4. Architectural Patterns Applied",
                "## 4b. Code-Level Design Patterns Applied",
                "## 5. DDD Aggregates",
                "## 13. Test Strategy",
            ],
            "pattern_selection": "required",
            "task_policy": "required",
            "testing_expectation": "e2e-required",
            "gate_profile": "feature-strict",
        },
        "patch": {
            "allowed_templates": ["patch-plan-template.md"],
            "mandatory_sections": [
                "## 1. Problem Statement",
                "## 2. Files / Modules Affected",
            ],
            "pattern_selection": "optional",
            "task_policy": "required",
            "testing_expectation": "regression-required",
            "gate_profile": "patch-safe",
        },
        "refactor": {
            "allowed_templates": ["refactor-plan-template.md"],
            "mandatory_sections": [
                "## 1. Goal",
                "## 2. Scope / Non-Scope",
                "## 3. Invariants to Preserve",
                "## 4. Public Contract Impact",
                "## 5. Behavioral Equivalence Strategy",
                "## 6. Regression Strategy",
            ],
            "pattern_selection": "optional",
            "task_policy": "optional",
            "testing_expectation": "regression-required",
            "gate_profile": "refactor-safe",
        },
        "bugfix": {
            "allowed_templates": ["bugfix-report-template.md"],
            "mandatory_sections": [
                "## 1. Symptom",
                "## 2. Reproduction",
                "## 3. Expected Behavior",
                "## 4. Regression Test Target",
                "## 5. Root Cause",
                "## 6. Fix Strategy",
            ],
            "pattern_selection": "optional",
            "task_policy": "optional",
            "testing_expectation": "regression-required",
            "gate_profile": "bugfix-fast",
        },
        "migration": {
            "allowed_templates": ["system-design-plan-template.md", "patch-plan-template.md"],
            "mandatory_sections": [
                "## 4. Architectural Patterns Applied",
                "## 4b. Code-Level Design Patterns Applied",
                "## 5. DDD Aggregates",
                "## 13. Test Strategy",
            ],
            "pattern_selection": "required",
            "task_policy": "required",
            "testing_expectation": "e2e-required",
            "gate_profile": "feature-strict",
        },
        "tooling": {
            "allowed_templates": ["patch-plan-template.md"],
            "mandatory_sections": [
                "## 1. Problem Statement",
                "## 2. Files / Modules Affected",
            ],
            "pattern_selection": "optional",
            "task_policy": "required",
            "testing_expectation": "regression-required",
            "gate_profile": "patch-safe",
        },
        "spike": {
            "allowed_templates": ["patch-plan-template.md"],
            "mandatory_sections": [
                "## 1. Problem Statement",
                "## 2. Files / Modules Affected",
            ],
            "pattern_selection": "optional",
            "task_policy": "optional",
            "testing_expectation": "advisory",
            "gate_profile": "spike-light",
        },
    },
    "legacy_plan_filename_work_class": {
        "system-design-plan": "feature",
        "patch-plan": "patch",
    },
    "plan_tiers": {
        "system": {
            "match_filename": "system-design-plan",
            "mandatory_sections": [
                "## 4. Architectural Patterns Applied",
                "## 4b. Code-Level Design Patterns Applied",
                "## 5. DDD Aggregates",
                "## 13. Test Strategy",
            ],
            "pattern_selection": "required",
        },
        "patch": {
            "match_filename": "patch-plan",
            "mandatory_sections": [
                "## 1. Problem Statement",
                "## 2. Files / Modules Affected",
            ],
            "pattern_selection": "optional",
        },
    },
    "placeholder_markers": ["_e.g.,", "e.g.,", "MANDATORY"],
    "gate": {"default_max_tier1_retries": 3, "heuristic_retry_escalates": False},
    "rules": {
        "e2e-test-presence": {
            "severity": "tier1",
            "confidence": "deterministic",
            "remediation_owner": "feature-team",
        },
        "e2e-test-empty": {
            "severity": "tier1",
            "confidence": "deterministic",
            "remediation_owner": "feature-team",
        },
        "e2e-test-placeholder": {
            "severity": "tier1",
            "confidence": "heuristic",
            "remediation_owner": "feature-team",
        },
        "e2e-test-family-empty": {
            "severity": "tier1",
            "confidence": "deterministic",
            "remediation_owner": "feature-team",
        },
        "trading-no-float-money": {
            "severity": "tier2",
            "confidence": "deterministic",
            "remediation_owner": "domain-team",
        },
        "trading-idempotency-key-missing": {
            "severity": "tier2",
            "confidence": "deterministic",
            "remediation_owner": "domain-team",
        },
        "trading-order-lifecycle-illegal-transition": {
            "severity": "tier2",
            "confidence": "deterministic",
            "remediation_owner": "domain-team",
        },
        "trading-hotpath-blocking-io": {
            "severity": "tier2",
            "confidence": "deterministic",
            "remediation_owner": "domain-team",
        },
        "trading-replay-protection-missing": {
            "severity": "tier1",
            "confidence": "heuristic",
            "remediation_owner": "domain-team",
        },
        "banking-pci-pan-storage": {
            "severity": "tier1",
            "confidence": "heuristic",
            "remediation_owner": "security-team",
        },
        "banking-ledger-inplace-mutation": {
            "severity": "tier2",
            "confidence": "deterministic",
            "remediation_owner": "domain-team",
        },
        "banking-idempotency-key-missing": {
            "severity": "tier2",
            "confidence": "deterministic",
            "remediation_owner": "domain-team",
        },
        "banking-payment-boundary-controls-missing": {
            "severity": "tier1",
            "confidence": "heuristic",
            "remediation_owner": "security-team",
        },
        "banking-psd2-sca-missing-advisory": {
            "severity": "tier1",
            "confidence": "heuristic",
            "remediation_owner": "domain-team",
        },
        "healthcare-phi-logging": {
            "severity": "tier1",
            "confidence": "heuristic",
            "remediation_owner": "security-team",
        },
        "saas-tenant-filter-missing": {
            "severity": "tier1",
            "confidence": "heuristic",
            "remediation_owner": "domain-team",
        },
        "saas-global-cache-key": {
            "severity": "tier1",
            "confidence": "heuristic",
            "remediation_owner": "domain-team",
        },
        "completion-tasks-unchecked": {
            "severity": "tier1",
            "confidence": "deterministic",
            "remediation_owner": "feature-team",
        },
        "completion-tier2-outstanding": {
            "severity": "tier2",
            "confidence": "deterministic",
            "remediation_owner": "feature-team",
        },
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Itexus spec-kit gate orchestrator")
    parser.add_argument("--event", required=True, help="Lifecycle event (e.g. after_implement)")
    parser.add_argument("--workspace", required=True, help="Target workspace root")
    return parser.parse_args()


def load_config(workspace: Path) -> Dict:
    config_path = workspace / ".itx-config.yml"
    if not config_path.exists():
        raise FileNotFoundError(f"Missing config: {config_path}")
    text = config_path.read_text(encoding="utf-8")
    return yaml.safe_load(text) or {}


def load_policy(workspace: Path) -> Dict[str, Any]:
    """Load policy.yml from the workspace, warning when fallback is used."""
    policy_path = workspace / ".specify" / "policy.yml"
    if not policy_path.exists():
        sys.stderr.write(f"[itx-gates] Warning: missing policy file at {policy_path}; using built-in defaults.\n")
        return dict(_DEFAULT_POLICY)
    try:
        data = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError) as exc:
        sys.stderr.write(f"[itx-gates] Warning: failed to parse policy file at {policy_path}: {exc}; using built-in defaults.\n")
        return dict(_DEFAULT_POLICY)
    if isinstance(data, dict):
        return data
    sys.stderr.write(f"[itx-gates] Warning: policy file at {policy_path} is not a mapping; using built-in defaults.\n")
    return dict(_DEFAULT_POLICY)


def _parse_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    return default


def _parse_retry_limit(raw_value: Any, default: int) -> int:
    try:
        parsed = int(raw_value)
    except (TypeError, ValueError):
        sys.stderr.write(f"[itx-gates] Warning: invalid gate.max_tier1_retries value '{raw_value}'; using default {default}.\n")
        return default
    if parsed < 0:
        sys.stderr.write(f"[itx-gates] Warning: negative gate.max_tier1_retries value '{raw_value}'; using default {default}.\n")
        return default
    return parsed


def load_knowledge_manifest(workspace: Path) -> Dict[str, Any]:
    manifest_path = workspace / ".specify" / "knowledge-manifest.json"
    if not manifest_path.exists():
        return {}
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def ensure_feedback_path(workspace: Path) -> Path:
    feedback_path = workspace / ".specify" / "context" / "gate_feedback.md"
    feedback_path.parent.mkdir(parents=True, exist_ok=True)
    return feedback_path


def _retry_key(event: str, finding: Finding) -> str:
    return f"{event}::{finding.get('rule', 'unspecified')}"


def read_tier1_retry_state(workspace: Path) -> Dict[str, int]:
    feedback_path = ensure_feedback_path(workspace)
    if not feedback_path.exists():
        return {}
    for line in feedback_path.read_text(encoding="utf-8").splitlines():
        if not line.startswith(RETRY_STATE_PREFIX):
            continue
        payload = line.split("`", maxsplit=2)
        if len(payload) < 2:
            continue
        try:
            raw_state = json.loads(payload[1])
        except json.JSONDecodeError:
            continue
        if not isinstance(raw_state, dict):
            continue
        normalized: Dict[str, int] = {}
        for key, value in raw_state.items():
            if isinstance(key, str) and isinstance(value, int) and value >= 0:
                normalized[key] = value
        return normalized
    return {}


def write_gate_feedback(
    workspace: Path,
    event: str,
    tier1_findings: List[Finding],
    tier2_findings: List[Finding],
    retry_state: Dict[str, int],
    retry_limit: int,
) -> None:
    """Write unified feedback for both Tier 1 and Tier 2 findings."""
    feedback_path = ensure_feedback_path(workspace)
    max_retry = max(retry_state.values(), default=0)

    action = "hard-halt" if tier2_findings else "auto-correction requested"
    payload = [
        "# Gate Feedback",
        "",
        f"- Event: `{event}`",
        f"- Action: {action}",
        f"- Retry: `{max_retry} / {retry_limit}`",
        f"- Retry-State: `{json.dumps(retry_state, sort_keys=True)}`",
        "",
    ]

    all_findings = list(tier1_findings) + list(tier2_findings)
    for idx, item in enumerate(all_findings, start=1):
        severity = item.get("severity", TIER_1)
        retry_count = retry_state.get(_retry_key(event, item), 0)
        payload.extend(
            [
                f"## Finding {idx}",
                f"- Severity: `{severity}`",
                f"- Rule: `{item.get('rule', 'unspecified')}`",
                f"- Retry: `{retry_count} / {retry_limit}`",
                f"- Message: {item.get('message', 'No details provided.')}",
                (f"- Confidence: `{item.get('confidence')}`" if item.get("confidence") else ""),
                (f"- Remediation: {item.get('remediation')}" if item.get("remediation") else ""),
                (f"- Remediation Owner: `{item.get('remediation_owner')}`" if item.get("remediation_owner") else ""),
                "",
            ]
        )
    feedback_path.write_text("\n".join(payload), encoding="utf-8")


def run_docker_exec(container_name: str, command: List[str]) -> subprocess.CompletedProcess:
    full_cmd = ["docker", "exec", container_name, *command]
    try:
        return subprocess.run(full_cmd, check=False, capture_output=True, text=True)
    except FileNotFoundError as exc:
        return subprocess.CompletedProcess(
            full_cmd,
            127,
            stdout="",
            stderr=f"Docker CLI not found: {exc}",
        )
    except OSError as exc:
        return subprocess.CompletedProcess(
            full_cmd,
            1,
            stdout="",
            stderr=f"Failed to execute docker command: {exc}",
        )


PATTERN_FILENAME_RE = re.compile(r"\b([a-z0-9][a-z0-9\-]*\.md)\b", re.IGNORECASE)
E2E_FILE_PATTERNS = [
    "e2e_test_*.py",
    "*.e2e-spec.ts",
    "*.e2e-spec.js",
    "*.e2e.test.ts",
    "*.e2e.test.js",
]
E2E_PLACEHOLDER_RE = re.compile(r"\b(todo|tbd|fixme)\b", re.IGNORECASE)
E2E_PY_PASS_RE = re.compile(r"^\s*pass\s*(#.*)?$", re.MULTILINE)
JS_TS_EXPECT_RE = re.compile(r"\bexpect\s*\(.+?\)\s*\.\s*\w+\s*\(", re.DOTALL)
JS_TS_ASSERT_RE = re.compile(r"\bassert\s*\(", re.DOTALL)
JS_TS_SHOULD_RE = re.compile(r"\bshould\s*\.", re.DOTALL)
TASK_UNCHECKED_RE = re.compile(r"^\s*-\s+\[\s\]\s+(.+)$", re.MULTILINE)
TASK_CHECKED_RE = re.compile(r"^\s*-\s+\[[xX]\]\s+(.+)$", re.MULTILINE)
FINDING_RULE_RE = re.compile(r"- Rule:\s+`([^`]+)`")
FINDING_SEVERITY_RE = re.compile(r"- Severity:\s+`([^`]+)`")
FINDING_MESSAGE_RE = re.compile(r"- Message:\s+(.+)")
MARKDOWN_FILE_REF_RE = re.compile(
    r"`([A-Za-z0-9_./-]+\.(?:py|ts|js|tsx|jsx|java|go|rs|rb|php|sql|md|ya?ml|json|toml|sh|ps1))`"
)
PLAIN_FILE_REF_RE = re.compile(
    r"\b([A-Za-z0-9_./-]+\.(?:py|ts|js|tsx|jsx|java|go|rs|rb|php|sql|md|ya?ml|json|toml|sh|ps1))\b"
)
PACKAGE_ACTION_RE = re.compile(
    r"\b(pip install|pip uninstall|npm install|npm uninstall|npm remove|pnpm add|pnpm remove|yarn add|yarn remove|poetry add|poetry remove|uv add|uv remove)\b",
    re.IGNORECASE,
)
PACKAGE_FILE_HINT_RE = re.compile(
    r"\b(requirements(?:-dev)?\.txt|package\.json|pyproject\.toml|poetry\.lock|package-lock\.json|pnpm-lock\.yaml|yarn\.lock)\b",
    re.IGNORECASE,
)

RULE_REMEDIATION_HINTS: Dict[str, str] = {
    "plan-presence": "Generate a plan from the current feature using the appropriate template.",
    "plan-section-missing": "Add all required headings and provide concrete design decisions under each section.",
    "plan-section-placeholder": "Replace placeholder text with implementation-specific content.",
    "tasks-presence": "Generate tasks.md in a supported location (for example specs/**/tasks.md) before continuing.",
    "tasks-checkbox-format": "Convert task items to checkbox syntax: '- [ ]' (pending) / '- [x]' (done).",
    "e2e-test-presence": "Add at least one E2E test file using the documented naming conventions.",
    "e2e-test-empty": "Add explicit assertions that verify behavior outcomes and persisted side-effects.",
    "e2e-test-placeholder": "Replace placeholder TODO/pass bodies with executable test steps and assertions.",
    "e2e-test-family-empty": "Ensure each detected E2E test family has at least one file with assertions.",
    "completion-tasks-unchecked": "Mark all implementation tasks as completed (`- [x]`) before running delivery checks.",
    "completion-tier2-outstanding": "Resolve Tier 2 findings in gate_feedback.md or escalate for explicit human override.",
    "knowledge-pattern-selection-missing": "Declare selected pattern filenames using a structured selection block.",
    "knowledge-pattern-unresolved": "Fix pattern filenames to match entries from .specify/pattern-index.md.",
    "trading-idempotency-key-missing": "Require and persist idempotency keys for trading command entrypoints.",
    "trading-order-lifecycle-illegal-transition": "Enforce order state machine transitions according to documented lifecycle.",
    "trading-hotpath-blocking-io": "Remove blocking I/O from hot paths; use async/non-blocking infra boundaries.",
    "trading-replay-protection-missing": "Add deduplication or replay protection markers (nonce/event_id/sequence).",
    "banking-ledger-inplace-mutation": "Replace in-place balance updates with append-only ledger entries and derived balances.",
    "banking-idempotency-key-missing": "Require and persist idempotency keys for payment commands/endpoints.",
    "banking-payment-boundary-controls-missing": "Add explicit SCA and authorization controls at payment entrypoints.",
    "banking-psd2-sca-missing-advisory": "Document or implement SCA controls (middleware/policy/decorator) for payment flows.",
    "saas-tenant-filter-missing": "Add tenant_id filters or RLS session variables for all tenant-scoped queries.",
    "saas-global-cache-key": "Namespace cache keys with tenant id (e.g. t:{tenant_id}:...) to prevent cross-tenant leakage.",
}
RULE_DEFAULT_META: Dict[str, Dict[str, str]] = {
    "trading-no-float-money": {"confidence": "deterministic", "remediation_owner": "domain-team"},
    "e2e-test-presence": {"confidence": "deterministic", "remediation_owner": "feature-team"},
    "tasks-presence": {"confidence": "deterministic", "remediation_owner": "feature-team"},
    "plan-section-missing": {"confidence": "deterministic", "remediation_owner": "feature-team"},
}


def _extract_markdown_h2_sections(content: str) -> Dict[str, str]:
    """Map H2 heading lines to their body content, excluding fenced code blocks."""
    heading_to_body: Dict[str, str] = {}
    lines = content.splitlines()
    in_code_fence = False
    current_heading: str | None = None
    current_body: List[str] = []

    def flush_current() -> None:
        nonlocal current_heading, current_body
        if current_heading is not None:
            heading_to_body[current_heading] = "\n".join(current_body).strip()
        current_heading = None
        current_body = []

    for raw_line in lines:
        stripped = raw_line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_code_fence = not in_code_fence
            continue
        if in_code_fence:
            continue
        if raw_line.startswith("## "):
            flush_current()
            current_heading = raw_line.strip()
            continue
        if current_heading is not None:
            current_body.append(raw_line)

    flush_current()
    return heading_to_body


def _find_plan_files(workspace: Path) -> List[Path]:
    """Locate plan markdown files produced during /speckit.plan."""
    candidates = [
        workspace.glob("specs/**/system-design-plan*.md"),
        workspace.glob("specs/**/patch-plan*.md"),
        workspace.glob("specs/**/refactor-plan*.md"),
        workspace.glob("specs/**/bugfix-report*.md"),
        workspace.glob("specs/**/migration-plan*.md"),
        workspace.glob("specs/**/tooling-plan*.md"),
        workspace.glob("specs/**/spike-note*.md"),
        workspace.glob("system-design-plan*.md"),
        workspace.glob("patch-plan*.md"),
        workspace.glob("refactor-plan*.md"),
        workspace.glob("bugfix-report*.md"),
        workspace.glob("migration-plan*.md"),
        workspace.glob("tooling-plan*.md"),
        workspace.glob("spike-note*.md"),
    ]
    seen: set[Path] = set()
    results: List[Path] = []
    for gen in candidates:
        for p in gen:
            rel = p.relative_to(workspace)
            if should_skip_path(rel):
                continue
            if p not in seen:
                seen.add(p)
                results.append(p)
    return results


def _find_task_files(workspace: Path) -> List[Path]:
    """Locate tasks markdown files produced during /speckit.tasks."""
    candidates = [
        workspace.glob("specs/**/tasks.md"),
        workspace.glob(".specify/tasks.md"),
        workspace.glob(".specify/tasks/tasks.md"),
        workspace.glob("tasks.md"),
    ]
    seen: set[Path] = set()
    results: List[Path] = []
    for gen in candidates:
        for p in gen:
            rel = p.relative_to(workspace)
            if rel.parts and rel.parts[0] != ".specify" and should_skip_path(rel):
                continue
            if p not in seen:
                seen.add(p)
                results.append(p)
    return results


CHECKBOX_RE = re.compile(r"^\s*-\s+\[([ xX])\]\s+\S", re.MULTILINE)
HEADING_WITH_LEVEL_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*$")
TASK_HEADING_RE = re.compile(r"\b(tasks?|todo|checklist|work items?)\b", re.IGNORECASE)
NON_TASK_HEADING_RE = re.compile(r"\b(notes?|context|references?|links?)\b", re.IGNORECASE)
TASK_ID_RE = re.compile(r"^T\d{3}\b", re.IGNORECASE)


def _is_bare_task_item(line: str) -> bool:
    stripped = line.strip()
    if not stripped.startswith("- "):
        return False
    item_text = stripped[2:].strip()
    if not item_text or item_text.startswith("["):
        return False
    return TASK_ID_RE.match(item_text) is not None


def _classify_heading_scope(heading_text: str) -> str | None:
    if TASK_HEADING_RE.search(heading_text):
        return "task"
    if NON_TASK_HEADING_RE.search(heading_text):
        return "non-task"
    return None


def _validate_tasks_checkbox_format(task_files: List[Path]) -> List[Finding]:
    """Warn when likely task list items in tasks.md are not checkboxes."""
    findings: List[Finding] = []
    for path in task_files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        # Stack entries are (heading_level, scope), where scope is 'task' or 'non-task'.
        scope_stack: List[tuple[int, str]] = []
        bare_task_lines = 0
        for line in text.splitlines():
            heading_match = HEADING_WITH_LEVEL_RE.match(line)
            if heading_match:
                level = len(heading_match.group(1))
                heading_text = heading_match.group(2).strip()
                while scope_stack and scope_stack[-1][0] >= level:
                    scope_stack.pop()
                explicit_scope = _classify_heading_scope(heading_text)
                if explicit_scope is None:
                    inherited_scope = scope_stack[-1][1] if scope_stack else "task"
                    scope_stack.append((level, inherited_scope))
                else:
                    scope_stack.append((level, explicit_scope))
                continue
            current_scope = scope_stack[-1][1] if scope_stack else "task"
            if current_scope == "task" and _is_bare_task_item(line):
                bare_task_lines += 1
        if bare_task_lines:
            findings.append(
                {
                    "severity": TIER_1,
                    "rule": "tasks-checkbox-format",
                    "message": (
                        f"{path.name}: found {bare_task_lines} task item(s) using plain list syntax. Use checkbox "
                        f"format for all task items: `- [ ]` (pending) and `- [x]` (completed). "
                        f"See tasks-template.md."
                    ),
                }
            )
    return findings


def _find_e2e_test_files(workspace: Path) -> List[Path]:
    """Locate E2E test files using the enforced naming conventions."""
    seen: set[Path] = set()
    results: List[Path] = []
    for pattern in E2E_FILE_PATTERNS:
        for path in workspace.rglob(pattern):
            rel = path.relative_to(workspace)
            if should_skip_path(rel):
                continue
            if path in seen:
                continue
            seen.add(path)
            results.append(path)
    return results


def _e2e_family(path: Path) -> str:
    name = path.name
    if name.startswith("e2e_test_") and name.endswith(".py"):
        return "python"
    if name.endswith(".e2e-spec.ts"):
        return "ts-e2e-spec"
    if name.endswith(".e2e-spec.js"):
        return "js-e2e-spec"
    if name.endswith(".e2e.test.ts"):
        return "ts-e2e-test"
    if name.endswith(".e2e.test.js"):
        return "js-e2e-test"
    return "unknown"


def _python_has_assertions(text: str) -> bool:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.Assert):
            return True
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr.startswith("assert"):
                return True
    return False


def _strip_js_ts_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r"//.*?$", "", text, flags=re.MULTILINE)
    return text


def _js_ts_has_assertions(text: str) -> bool:
    stripped = _strip_js_ts_comments(text)
    return bool(JS_TS_EXPECT_RE.search(stripped) or JS_TS_ASSERT_RE.search(stripped) or JS_TS_SHOULD_RE.search(stripped))


def _e2e_has_assertion(path: Path, text: str) -> bool:
    suffix = path.suffix.lower()
    if suffix == ".py":
        return _python_has_assertions(text)
    return _js_ts_has_assertions(text)


def _has_placeholder_test_content(path: Path, text: str) -> bool:
    if E2E_PLACEHOLDER_RE.search(text):
        return True
    if path.suffix.lower() == ".py" and E2E_PY_PASS_RE.search(text):
        return True
    return False


def check_e2e_test_presence(workspace: Path) -> List[Finding]:
    """Validate that at least one E2E test exists and includes assertions."""
    findings: List[Finding] = []
    e2e_files = _find_e2e_test_files(workspace)
    if not e2e_files:
        findings.append(
            {
                "severity": TIER_1,
                "rule": "e2e-test-presence",
                "message": (
                    "No E2E test files found after implementation. Expected file names matching "
                    "`e2e_test_*.py`, `*.e2e-spec.{ts,js}`, or `*.e2e.test.{ts,js}`."
                ),
            }
        )
        return findings

    family_has_assertion: Dict[str, bool] = {}
    for test_file in e2e_files:
        text = test_file.read_text(encoding="utf-8", errors="ignore")
        family = _e2e_family(test_file)
        has_assertion = _e2e_has_assertion(test_file, text)
        family_has_assertion[family] = family_has_assertion.get(family, False) or has_assertion

        has_placeholder = _has_placeholder_test_content(test_file, text)
        if has_placeholder:
            findings.append(
                {
                    "severity": TIER_1,
                    "rule": "e2e-test-placeholder",
                    "message": (f"{test_file}: E2E test appears to contain placeholder content (TODO/TBD/FIXME or pass body)."),
                }
            )

        if not has_assertion and not has_placeholder:
            findings.append(
                {
                    "severity": TIER_1,
                    "rule": "e2e-test-empty",
                    "message": f"{test_file}: E2E test file contains no recognizable assertions.",
                }
            )

    for family, has_assertion in sorted(family_has_assertion.items()):
        if not has_assertion:
            findings.append(
                {
                    "severity": TIER_1,
                    "rule": "e2e-test-family-empty",
                    "message": f"E2E test family '{family}' has files but no assertion-bearing tests.",
                }
            )
    return findings


def _match_plan_tier(plan_path: Path, policy: Dict[str, Any]) -> Dict[str, Any] | None:
    """Return the policy tier definition matching this plan file, or None."""
    lower_name = plan_path.name.lower()
    for tier in (policy.get("plan_tiers") or {}).values():
        match_fn = str(tier.get("match_filename", "")).lower()
        if match_fn and match_fn in lower_name:
            return tier
    return None


def _split_frontmatter(markdown: str) -> tuple[Dict[str, Any], str]:
    if markdown.startswith("\ufeff"):
        markdown = markdown[1:]
    if not markdown.startswith("---\n"):
        return {}, markdown
    match = re.match(r"\A---\n(.*?)\n---\n?", markdown, flags=re.DOTALL)
    if not match:
        return {}, markdown
    raw_frontmatter = match.group(1)
    try:
        parsed = yaml.safe_load(raw_frontmatter)
    except yaml.YAMLError:
        return {}, markdown
    if not isinstance(parsed, dict):
        return {}, markdown
    body = markdown[match.end() :]
    return parsed, body


def _plan_has_work_class_frontmatter(path: Path) -> bool:
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
    frontmatter, _ = _split_frontmatter(content)
    raw_work_class = frontmatter.get("work_class")
    return isinstance(raw_work_class, str) and bool(raw_work_class.strip())


def _policy_work_class_entry(policy: Dict[str, Any], work_class: str) -> Dict[str, Any] | None:
    work_classes = policy.get("work_classes")
    if not isinstance(work_classes, dict):
        return None
    entry = work_classes.get(work_class)
    if isinstance(entry, dict):
        return entry
    return None


def _legacy_tier_for_work_class(policy: Dict[str, Any], work_class: str) -> Dict[str, Any] | None:
    """Resolve legacy plan_tiers entry by work_class for plan_tiers-only policies."""
    plan_tiers = policy.get("plan_tiers")
    if not isinstance(plan_tiers, dict):
        return None

    direct = plan_tiers.get(work_class)
    if isinstance(direct, dict):
        return direct

    # Backward compatibility for pre-Wave-A policies that use plan_tiers.system/patch keys.
    if work_class == "feature":
        system_tier = plan_tiers.get("system")
        if isinstance(system_tier, dict):
            return system_tier

    legacy_map = policy.get("legacy_plan_filename_work_class")
    if not isinstance(legacy_map, dict):
        return None

    expected_matches = [
        match_filename.lower()
        for match_filename, mapped_work_class in legacy_map.items()
        if isinstance(match_filename, str)
        and isinstance(mapped_work_class, str)
        and mapped_work_class.strip().lower() == work_class
    ]
    if not expected_matches:
        return None

    for tier_entry in plan_tiers.values():
        if not isinstance(tier_entry, dict):
            continue
        match_filename = str(tier_entry.get("match_filename", "")).lower()
        if any(expected_match in match_filename for expected_match in expected_matches):
            return tier_entry
    return None


def _resolve_legacy_work_class(plan_path: Path, policy: Dict[str, Any]) -> str | None:
    lower_name = plan_path.name.lower()
    legacy_map = policy.get("legacy_plan_filename_work_class")
    if isinstance(legacy_map, dict):
        for match_filename, work_class in legacy_map.items():
            if not isinstance(match_filename, str) or not isinstance(work_class, str):
                continue
            if match_filename.lower() in lower_name:
                return work_class.strip().lower()

    plan_tiers = policy.get("plan_tiers")
    if isinstance(plan_tiers, dict):
        for tier_name, tier in plan_tiers.items():
            if not isinstance(tier_name, str) or not isinstance(tier, dict):
                continue
            match_filename = str(tier.get("match_filename", "")).lower()
            if match_filename and match_filename in lower_name:
                return tier_name.strip().lower()

    return None


def _resolve_plan_policy_entry(plan_path: Path, policy: Dict[str, Any]) -> tuple[Dict[str, Any] | None, str | None]:
    """Resolve the effective plan policy entry and corresponding work_class."""
    content = plan_path.read_text(encoding="utf-8")
    frontmatter, _ = _split_frontmatter(content)
    raw_work_class = frontmatter.get("work_class")
    legacy_work_class = _resolve_legacy_work_class(plan_path, policy)

    # Preserve legacy filename behavior first for backward compatibility.
    if legacy_work_class:
        if raw_work_class is not None:
            if isinstance(raw_work_class, str):
                parsed_work_class = raw_work_class.strip().lower()
                if parsed_work_class and parsed_work_class != legacy_work_class:
                    sys.stderr.write(
                        f"[itx-gates] Warning: ignoring work_class '{raw_work_class}' in {plan_path}; "
                        f"legacy filename routing requires '{legacy_work_class}'.\n"
                    )
            else:
                sys.stderr.write(
                    f"[itx-gates] Warning: invalid non-string work_class in {plan_path}; using legacy filename fallback.\n"
                )

        entry = _policy_work_class_entry(policy, legacy_work_class)
        if entry is not None:
            return entry, legacy_work_class

        tier = _match_plan_tier(plan_path, policy)
        if tier is not None:
            return tier, None

        return None, None

    # Metadata-first path for non-legacy plan filenames.
    if raw_work_class is not None:
        if isinstance(raw_work_class, str):
            parsed_work_class = raw_work_class.strip().lower()
            entry = _policy_work_class_entry(policy, parsed_work_class)
            if entry is not None:
                return entry, parsed_work_class
            work_classes = policy.get("work_classes")
            if not isinstance(work_classes, dict):
                tier = _legacy_tier_for_work_class(policy, parsed_work_class)
                if tier is not None:
                    return tier, parsed_work_class
            sys.stderr.write(
                f"[itx-gates] Warning: unknown work_class '{raw_work_class}' in {plan_path}; using legacy filename fallback.\n"
            )
        else:
            sys.stderr.write(
                f"[itx-gates] Warning: invalid non-string work_class in {plan_path}; using legacy filename fallback.\n"
            )

    tier = _match_plan_tier(plan_path, policy)
    if tier is not None:
        return tier, None

    return None, None


def _entry_requires_tasks(policy_entry: Mapping[str, Any]) -> bool:
    task_policy = policy_entry.get("task_policy")
    if isinstance(task_policy, str):
        return task_policy.strip().lower() == "required"
    return True


def _load_active_feature_from_workflow_state(workspace: Path) -> str | None:
    state_path = workspace / ".specify" / "context" / "workflow-state.yml"
    if not state_path.exists():
        return None
    try:
        data = yaml.safe_load(state_path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    feature = data.get("feature")
    if not isinstance(feature, str):
        return None
    normalized = feature.strip()
    return normalized or None


def _plan_files_for_task_policy_resolution(workspace: Path) -> List[Path]:
    all_plan_files = _find_plan_files(workspace)
    if not all_plan_files:
        return []

    active_feature = _load_active_feature_from_workflow_state(workspace)
    if not active_feature:
        return all_plan_files

    feature_root = workspace / "specs" / active_feature
    scoped: List[Path] = []
    for plan_file in all_plan_files:
        try:
            plan_file.relative_to(feature_root)
        except ValueError:
            continue
        scoped.append(plan_file)
    return scoped or all_plan_files


def _task_files_for_review_scope(workspace: Path, task_files: Sequence[Path]) -> List[Path]:
    active_feature = _load_active_feature_from_workflow_state(workspace)
    if not active_feature:
        return list(task_files)

    feature_root = workspace / "specs" / active_feature
    scoped: List[Path] = []
    for task_file in task_files:
        try:
            rel = task_file.relative_to(workspace)
        except ValueError:
            continue
        if rel.parts and rel.parts[0] == ".specify":
            scoped.append(task_file)
            continue
        if rel == Path("tasks.md"):
            scoped.append(task_file)
            continue
        try:
            task_file.relative_to(feature_root)
        except ValueError:
            continue
        scoped.append(task_file)
    return scoped


def _task_files_for_execution_brief_scope(workspace: Path, task_files: Sequence[Path], plan_path: Path) -> List[Path]:
    """Scope tasks to the selected brief plan when workflow-state is absent."""
    active_feature = _load_active_feature_from_workflow_state(workspace)
    if active_feature:
        return _task_files_for_review_scope(workspace, task_files)

    try:
        plan_rel = plan_path.relative_to(workspace)
    except ValueError:
        return []
    if len(plan_rel.parts) < 3 or plan_rel.parts[0] != "specs":
        return []

    feature_root = workspace / "specs" / plan_rel.parts[1]
    scoped: List[Path] = []
    for task_file in task_files:
        try:
            task_file.relative_to(feature_root)
        except ValueError:
            continue
        scoped.append(task_file)
    return scoped


def _tasks_required_for_workspace(workspace: Path, policy: Dict[str, Any]) -> bool:
    """Determine whether tasks.md is required for the current workspace context.

    Wave B rule:
    - Preserve strict legacy behavior by default.
    - Resolve context from active feature workflow state when available.
    - If resolvable plan artifacts exist and all of them have optional task_policy,
      tasks.md is not required.
    """
    plan_files = _plan_files_for_task_policy_resolution(workspace)
    if not plan_files:
        return True

    resolved_entries: List[Mapping[str, Any]] = []
    for plan_file in plan_files:
        policy_entry, _ = _resolve_plan_policy_entry(plan_file, policy)
        if policy_entry is not None:
            resolved_entries.append(policy_entry)

    if not resolved_entries:
        return True

    return any(_entry_requires_tasks(entry) for entry in resolved_entries)


def _validate_plan_content(plan_path: Path, policy: Dict[str, Any]) -> List[Finding]:
    """Check that mandatory sections exist and are not just template placeholders."""
    findings: List[Finding] = []
    content = plan_path.read_text(encoding="utf-8")

    frontmatter, _ = _split_frontmatter(content)
    raw_work_class = frontmatter.get("work_class")
    policy_entry, _ = _resolve_plan_policy_entry(plan_path, policy)
    if policy_entry is None:
        if _resolve_legacy_work_class(plan_path, policy) is None:
            if raw_work_class is None:
                findings.append(
                    {
                        "severity": TIER_1,
                        "rule": "plan-work-class-missing",
                        "message": (
                            f"Plan '{plan_path.name}' is missing required frontmatter work_class. "
                            "Declare a work_class from policy.work_classes or use a legacy plan filename."
                        ),
                    }
                )
            else:
                findings.append(
                    {
                        "severity": TIER_1,
                        "rule": "plan-work-class-unresolved",
                        "message": (
                            f"Unable to resolve work_class '{raw_work_class}' for {plan_path.name}. "
                            "Declare a known work_class from policy.work_classes or use a legacy plan filename."
                        ),
                    }
                )
        return findings

    mandatory_headings: List[str] = policy_entry.get("mandatory_sections") or []
    placeholder_markers: List[str] = policy.get("placeholder_markers") or []
    sections = _extract_markdown_h2_sections(content)

    for heading in mandatory_headings:
        section_body = sections.get(heading)
        if section_body is None:
            findings.append(
                {
                    "severity": TIER_1,
                    "rule": "plan-section-missing",
                    "message": f"Plan is missing mandatory section: '{heading}' in {plan_path.name}",
                }
            )
            continue

        content_lines = [
            line for line in section_body.splitlines() if line.strip() and not line.strip().startswith("|--") and not line.strip().startswith("> ")
        ]

        real_content = [line for line in content_lines if not any(marker in line for marker in placeholder_markers)]

        if not real_content:
            findings.append(
                {
                    "severity": TIER_1,
                    "rule": "plan-section-placeholder",
                    "message": f"Section '{heading}' in {plan_path.name} contains only placeholder text — fill it with actual design decisions.",
                }
            )

    return findings


def _now_iso_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _plan_priority(path: Path) -> int:
    lower_name = path.name.lower()
    if "system-design-plan" in lower_name:
        return 0
    if "patch-plan" in lower_name:
        return 1
    if "refactor-plan" in lower_name:
        return 2
    if "bugfix-report" in lower_name:
        return 3
    if "migration-plan" in lower_name:
        return 4
    if "tooling-plan" in lower_name:
        return 5
    if "spike-note" in lower_name:
        return 6
    return 99


def _resolve_plan_for_execution_brief(workspace: Path) -> Path | None:
    active_feature = _load_active_feature_from_workflow_state(workspace)
    if active_feature:
        feature_root = workspace / "specs" / active_feature
        scoped: List[Path] = []
        for plan_file in _find_plan_files(workspace):
            try:
                plan_file.relative_to(feature_root)
            except ValueError:
                continue
            scoped.append(plan_file)
        if scoped:
            return sorted(scoped, key=lambda p: (_plan_priority(p), str(p)))[0]
        return None
    all_plans = sorted(_find_plan_files(workspace), key=lambda p: (_plan_priority(p), str(p)))
    if len(all_plans) == 1:
        return all_plans[0]
    return None


def _infer_feature_from_plan(workspace: Path, plan_path: Path) -> str:
    active_feature = _load_active_feature_from_workflow_state(workspace)
    if active_feature:
        return active_feature
    try:
        rel = plan_path.relative_to(workspace)
    except ValueError:
        return "workspace"
    if len(rel.parts) >= 3 and rel.parts[0] == "specs":
        return rel.parts[1]
    return "workspace"


def _parse_compact_lines(section_body: str, *, limit: int = 8) -> List[str]:
    lines: List[str] = []
    for raw_line in section_body.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped.startswith("|"):
            continue
        if stripped.startswith(">"):
            continue
        stripped = re.sub(r"^\d+\.\s+", "", stripped)
        stripped = re.sub(r"^-+\s+", "", stripped)
        stripped = re.sub(r"^\[[ xX]\]\s+", "", stripped)
        if stripped:
            lines.append(stripped)
        if len(lines) >= limit:
            break
    return lines


def _extract_scope(section_body: str) -> tuple[List[str], List[str]]:
    in_scope: List[str] = []
    out_scope: List[str] = []
    for line in _parse_compact_lines(section_body, limit=20):
        lower = line.lower()
        if "out of scope" in lower or lower.startswith("out:") or lower.startswith("non-scope"):
            cleaned = re.sub(r"^(out:|out of scope:|non-scope:)\s*", "", line, flags=re.IGNORECASE).strip()
            if cleaned:
                out_scope.append(cleaned)
            continue
        if lower.startswith("in:") or "in scope" in lower:
            cleaned = re.sub(r"^(in:|in scope:)\s*", "", line, flags=re.IGNORECASE).strip()
            if cleaned:
                in_scope.append(cleaned)
            continue
        in_scope.append(line)
    return in_scope[:4], out_scope[:4]


def _extract_file_refs(text: str) -> List[str]:
    refs = [*MARKDOWN_FILE_REF_RE.findall(text), *PLAIN_FILE_REF_RE.findall(text)]
    normalized: List[str] = []
    seen: set[str] = set()
    for ref in refs:
        cleaned = ref.strip().strip(".,)")
        if not cleaned:
            continue
        if cleaned.startswith("./"):
            cleaned = cleaned[2:]
        if cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)
    return normalized


def _parse_gate_feedback_summaries(gate_feedback_text: str, *, limit: int = 5) -> tuple[List[str], bool]:
    summaries: List[str] = []
    has_tier2 = False
    blocks = gate_feedback_text.split("## Finding ")
    for block in blocks[1:]:
        sev_match = FINDING_SEVERITY_RE.search(block)
        rule_match = FINDING_RULE_RE.search(block)
        msg_match = FINDING_MESSAGE_RE.search(block)
        if not (sev_match and rule_match and msg_match):
            continue
        severity = sev_match.group(1).strip().lower()
        rule = rule_match.group(1).strip()
        message = msg_match.group(1).strip()
        if severity == TIER_2:
            has_tier2 = True
        summaries.append(f"[{severity}] {rule}: {message}")
        if len(summaries) >= limit:
            break
    return summaries, has_tier2


def _task_lines_for_brief(task_files: Sequence[Path]) -> tuple[List[str], List[str], List[str]]:
    unchecked: List[str] = []
    checked: List[str] = []
    file_refs: List[str] = []
    for path in task_files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in TASK_UNCHECKED_RE.findall(text):
            unchecked.append(match.strip())
        for match in TASK_CHECKED_RE.findall(text):
            checked.append(match.strip())
        file_refs.extend(_extract_file_refs(text))
    return unchecked, checked, file_refs


def _format_execution_brief(
    *,
    feature: str,
    work_class: str,
    domain: str,
    knowledge_mode: str,
    generated_from: List[str],
    objective: List[str],
    in_scope: List[str],
    out_scope: List[str],
    file_refs: List[str],
    selected_patterns: List[str],
    constraints: List[str],
    risks: List[str],
    verification: List[str],
    next_actions: List[str],
    approval_holds: List[str],
) -> str:
    lines = [
        "---",
        'schema_version: "1.0"',
        f'feature: "{feature}"',
        f'work_class: "{work_class}"',
        f'domain: "{domain}"',
        f'knowledge_mode: "{knowledge_mode}"',
        "generated_from:",
    ]
    for item in generated_from:
        lines.append(f'  - "{item}"')
    lines.extend(
        [
            f'generated_at: "{_now_iso_utc()}"',
            "---",
            "",
            "# Execution Brief",
            "",
            "## Behavior Overlay",
            "- Think Before Coding: restate objective, constraints, verification target.",
            "- Simplicity First: choose the smallest change that satisfies the brief.",
            "- Surgical Changes: stay within listed scope and avoid unrelated edits.",
            "- Goal-Driven Execution: verify against named tests and gate signals.",
            "",
            "## Objective",
        ]
    )
    lines.extend([f"- {item}" for item in objective[:3]] or ["- Clarify objective from source plan before implementation."])
    lines.extend(["", "## Scope"])
    lines.extend([f"- In: {item}" for item in (in_scope[:4] or ["Scope not explicitly declared; use listed files/modules as boundary."])])
    lines.extend([f"- Out: {item}" for item in out_scope[:4]])

    if file_refs:
        lines.extend(["", "## Files/Modules In Scope"])
        lines.extend([f"- {item}" for item in file_refs[:10]])
    if selected_patterns:
        lines.extend(["", "## Selected Patterns To Load"])
        lines.extend([f"- {item}" for item in selected_patterns[:8]])
    if constraints:
        lines.extend(["", "## Constraints and Invariants"])
        lines.extend([f"- {item}" for item in constraints[:8]])
    if risks:
        lines.extend(["", "## Active Risks and Gate Signals"])
        lines.extend([f"- {item}" for item in risks[:5]])
    lines.extend(["", "## Verification Targets"])
    lines.extend([f"- {item}" for item in verification[:8]] or ["- Preserve existing gate checks and ensure regression coverage for changed behavior paths."])
    if next_actions:
        lines.extend(["", "## Next Actions"])
        lines.extend([f"- {item}" for item in next_actions[:5]])
    if approval_holds:
        lines.extend(["", "## Human Approval Required"])
        lines.extend([f"- {item}" for item in approval_holds[:4]])
    lines.append("")
    return "\n".join(lines)


def _execution_brief_triggers(
    *,
    work_class: str,
    plan_text: str,
    file_refs: Sequence[str],
    unchecked_tasks: Sequence[str],
) -> List[str]:
    triggers: List[str] = []
    combined_text = "\n".join([plan_text, *unchecked_tasks])

    major_refactor_markers = {"major", "cross-module", "multi-module", "large-scale"}
    if work_class == "refactor":
        has_marker = any(marker in combined_text.lower() for marker in major_refactor_markers)
        if has_marker:
            triggers.append("major-refactor")

    if PACKAGE_ACTION_RE.search(combined_text):
        triggers.append("package-install-remove")

    high_risk_prefixes = (
        ".github/workflows/",
        "extensions/itx-gates/hooks/orchestrator.py",
        ".specify/extensions/",
        "scripts/itx_init.py",
        "scripts/patch.py",
        "scripts/release.py",
        "docker-compose",
        "Dockerfile",
        "migrations/",
    )
    if any(any(ref.startswith(prefix) for prefix in high_risk_prefixes) for ref in file_refs):
        triggers.append("high-risk-ops-change")

    # Preserve insertion order while deduplicating.
    return list(dict.fromkeys(triggers))


def _append_pre_action_audit_log(
    *,
    workspace: Path,
    feature: str,
    plan_path: Path,
    triggers: Sequence[str],
    file_refs: Sequence[str],
    verification_targets: Sequence[str],
) -> None:
    if not triggers:
        return
    log_path = workspace / ".specify" / "context" / "audit-log.md"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    existing = log_path.read_text(encoding="utf-8", errors="ignore") if log_path.exists() else ""

    lines: List[str] = []
    for trigger in triggers:
        signature = f"{feature}:{plan_path.name}:{trigger}"
        if signature in existing:
            continue
        lines.extend(
            [
                f"## Pre-Action Audit ({_now_iso_utc()})",
                f"- Signature: `{signature}`",
                f"- Action: `{trigger}`",
                f"- Trigger Reason: high-risk action detected from planning artifacts",
                f"- Intended Scope: `{', '.join(file_refs[:8]) or plan_path.name}`",
                "- Rollback Note: revert scoped edits and rerun gate checks before retry",
                f"- Verification Target: `{'; '.join(verification_targets[:3]) or 'gate + regression checks'}`",
                "",
            ]
        )
    if lines:
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write("\n".join(lines))


def _generate_execution_brief(workspace: Path, config: Dict[str, Any], policy: Dict[str, Any]) -> None:
    brief_path = workspace / ".specify" / "context" / "execution-brief.md"
    plan_path = _resolve_plan_for_execution_brief(workspace)
    if plan_path is None:
        if brief_path.exists():
            brief_path.unlink()
        return

    plan_text = plan_path.read_text(encoding="utf-8", errors="ignore")
    sections = _extract_markdown_h2_sections(plan_text)
    _, resolved_work_class = _resolve_plan_policy_entry(plan_path, policy)
    work_class = resolved_work_class or _resolve_legacy_work_class(plan_path, policy) or "unknown"
    feature = _infer_feature_from_plan(workspace, plan_path)
    domain = str(config.get("domain", "base")).strip() or "base"
    knowledge_mode = str((config.get("knowledge") or {}).get("mode", "eager")).strip().lower() or "eager"

    manifest = load_knowledge_manifest(workspace)
    manifest_files = manifest.get("files") if isinstance(manifest.get("files"), dict) else {}
    known_names = {str(name).lower() for name in manifest_files} if isinstance(manifest_files, dict) else None
    selected, _ = _extract_selected_patterns(plan_text, known_names or None)
    selected_patterns = sorted(selected) if selected is not None else []
    if selected == set():
        selected_patterns = ["none"]

    objective_headings = (
        "## 1. Problem Statement",
        "## 1. Goal",
        "## 1. Symptom",
    )
    objective: List[str] = []
    for heading in objective_headings:
        body = sections.get(heading)
        if body:
            objective.extend(_parse_compact_lines(body, limit=3))
            break

    in_scope: List[str] = []
    out_scope: List[str] = []
    for scope_heading in ("## 2. Scope / Non-Scope", "## 2. Files / Modules Affected", "## 2. Reproduction"):
        body = sections.get(scope_heading)
        if not body:
            continue
        scoped_in, scoped_out = _extract_scope(body)
        in_scope.extend(scoped_in)
        out_scope.extend(scoped_out)
        if in_scope:
            break

    file_refs: List[str] = []
    file_scope_body = sections.get("## 2. Files / Modules Affected")
    if file_scope_body:
        file_refs.extend(_extract_file_refs(file_scope_body))
    scope_body = sections.get("## 2. Scope / Non-Scope")
    if scope_body:
        file_refs.extend(_extract_file_refs(scope_body))

    constraints: List[str] = []
    for heading in (
        "## 3. Invariants to Preserve",
        "## 4. Public Contract Impact",
        "## 5. Behavioral Equivalence Strategy",
        "## 3. Expected Behavior",
        "## 6. Fix Strategy",
    ):
        body = sections.get(heading)
        if body:
            constraints.extend(_parse_compact_lines(body, limit=3))

    verification: List[str] = []
    for heading in ("## 13. Test Strategy", "## 6. Regression Strategy", "## 5. Regression Testing", "## 4. Regression Test Target"):
        body = sections.get(heading)
        if body:
            verification.extend(_parse_compact_lines(body, limit=4))

    risk_lines: List[str] = []
    for heading, body in sections.items():
        if "risk" in heading.lower():
            risk_lines.extend(_parse_compact_lines(body, limit=3))

    task_files = _task_files_for_execution_brief_scope(workspace, _find_task_files(workspace), plan_path)
    unchecked_tasks, _, task_file_refs = _task_lines_for_brief(task_files)
    file_refs.extend(task_file_refs)
    next_actions = unchecked_tasks[:5]
    if not next_actions and risk_lines:
        next_actions = [f"Mitigate risk: {item}" for item in risk_lines[:3]]

    gate_feedback_path = workspace / ".specify" / "context" / "gate_feedback.md"
    gate_summaries: List[str] = []
    has_tier2 = False
    if gate_feedback_path.exists():
        gate_feedback_text = gate_feedback_path.read_text(encoding="utf-8", errors="ignore")
        gate_summaries, has_tier2 = _parse_gate_feedback_summaries(gate_feedback_text, limit=5)
    risk_lines.extend(gate_summaries)

    approval_holds: List[str] = []
    if has_tier2:
        approval_holds.append("Outstanding Tier 2 gate findings require explicit human decision.")

    generated_from = ["plan"]
    if task_files:
        generated_from.append("tasks")
    if gate_feedback_path.exists():
        generated_from.append("gate_feedback")

    # Deduplicate while preserving order for concise brief output.
    dedup_files = list(dict.fromkeys(file_refs))
    dedup_constraints = list(dict.fromkeys(constraints))
    dedup_risks = list(dict.fromkeys(risk_lines))
    dedup_verification = list(dict.fromkeys(verification))

    brief_text = _format_execution_brief(
        feature=feature,
        work_class=work_class,
        domain=domain,
        knowledge_mode=knowledge_mode,
        generated_from=generated_from,
        objective=objective,
        in_scope=in_scope,
        out_scope=out_scope,
        file_refs=dedup_files,
        selected_patterns=selected_patterns,
        constraints=dedup_constraints,
        risks=dedup_risks,
        verification=dedup_verification,
        next_actions=next_actions,
        approval_holds=approval_holds,
    )

    brief_path.parent.mkdir(parents=True, exist_ok=True)
    brief_path.write_text(brief_text, encoding="utf-8")

    triggers = _execution_brief_triggers(
        work_class=work_class,
        plan_text=plan_text,
        file_refs=dedup_files,
        unchecked_tasks=unchecked_tasks,
    )
    _append_pre_action_audit_log(
        workspace=workspace,
        feature=feature,
        plan_path=plan_path,
        triggers=triggers,
        file_refs=dedup_files,
        verification_targets=dedup_verification,
    )


def _extract_selected_patterns(plan_text: str, known_filenames: set[str] | None = None) -> tuple[set[str] | None, bool]:
    """Extract pattern filenames from a structured selection block, or fall
    back to regex scanning for backward compatibility.

    Structured blocks look like:
        <!-- selected_patterns: domain-driven-design.md, hexagonal-architecture.md -->

    The keyword ``none`` explicitly declares no patterns are needed.
    Returns ``None`` only when no selection mechanism is found at all.
    The boolean return value indicates whether regex fallback parsing was used.
    """
    block_re = re.compile(
        r"<!--\s*selected_patterns\s*:\s*(.*?)\s*-->",
        re.IGNORECASE | re.DOTALL,
    )
    match = block_re.search(plan_text)
    if match:
        raw = match.group(1).strip()
        if raw.lower() == "none":
            return set(), False
        names = {name.strip().lower() for name in raw.split(",") if name.strip()}
        return names, False

    found = {name.lower() for name in PATTERN_FILENAME_RE.findall(plan_text)}
    if known_filenames is not None:
        found = {name for name in found if name in known_filenames}
    return (found if found else None), True


def _sync_lazy_knowledge(
    config: Dict[str, Any],
    workspace: Path,
    policy: Dict[str, Any],
) -> List[Finding]:
    knowledge = config.get("knowledge") or {}
    if str(knowledge.get("mode", "eager")).strip().lower() != "lazy":
        return []

    plan_files = _find_plan_files(workspace)
    if not plan_files:
        return []

    manifest = load_knowledge_manifest(workspace)
    raw_manifest_files = manifest.get("files")
    if raw_manifest_files is not None and not isinstance(raw_manifest_files, dict):
        sys.stderr.write("[itx-gates] Warning: malformed knowledge-manifest.json: 'files' must be a mapping; ignoring.\n")
        manifest_files: Dict[str, Dict[str, Any]] = {}
    else:
        manifest_files = raw_manifest_files or {}
    known_pattern_filenames = {name.lower() for name in manifest_files}
    known_names_for_fallback = known_pattern_filenames or None

    all_requested: set[str] = set()
    has_any_selection = False
    used_regex_fallback = False
    for plan_file in plan_files:
        text = plan_file.read_text(encoding="utf-8", errors="ignore")
        policy_entry, _ = _resolve_plan_policy_entry(plan_file, policy)
        selection_mode = str((policy_entry or {}).get("pattern_selection", "optional")).lower()

        selected, fallback_used = _extract_selected_patterns(text, known_names_for_fallback)
        used_regex_fallback = used_regex_fallback or fallback_used
        if selected is not None:
            has_any_selection = True
            all_requested.update(selected)
        elif selection_mode == "required":
            return [
                {
                    "severity": TIER_1,
                    "rule": "knowledge-pattern-selection-missing",
                    "message": (
                        "Lazy knowledge mode is active but no pattern filenames were selected in the plan. "
                        "Add a structured selection block (<!-- selected_patterns: file.md, ... -->) "
                        "or reference filenames from .specify/pattern-index.md."
                    ),
                }
            ]

    if not has_any_selection:
        return []
    if not all_requested:
        if used_regex_fallback:
            sys.stderr.write(
                "[itx-gates] Warning: detected deprecated inline markdown filename fallback for pattern "
                "selection. Prefer structured selection blocks: <!-- selected_patterns: file.md, ... -->\n"
            )
        return []

    store_root = workspace / ".specify" / ".knowledge-store"
    target_roots = {
        "patterns": workspace / ".specify" / "patterns",
        "design-patterns": workspace / ".specify" / "design-patterns",
        "anti-patterns": workspace / ".specify" / "anti-patterns",
    }

    available: Dict[str, tuple[str, Path]] = {}

    for name_key, entry in manifest_files.items():
        if not isinstance(name_key, str) or not isinstance(entry, dict):
            sys.stderr.write("[itx-gates] Warning: malformed knowledge-manifest.json entry ignored.\n")
            continue
        source_raw = entry.get("source", "")
        category = str(entry.get("category", "")).strip()
        if not isinstance(source_raw, str):
            sys.stderr.write(f"[itx-gates] Warning: malformed manifest source for '{name_key}' ignored.\n")
            continue
        source = Path(source_raw)
        if source.exists() and category in target_roots:
            available[name_key.lower()] = (category, source)

    for category in target_roots:
        source_dir = store_root / category
        if not source_dir.exists():
            continue
        for file_path in source_dir.glob("*.md"):
            key = file_path.name.lower()
            if key not in available:
                available[key] = (category, file_path)

    unresolved = sorted(name for name in all_requested if name not in available)
    findings: List[Finding] = []
    if unresolved:
        findings.append(
            {
                "severity": TIER_1,
                "rule": "knowledge-pattern-unresolved",
                "message": ("Some plan-selected patterns could not be resolved: " + ", ".join(unresolved)),
            }
        )

    promoted: list[str] = []
    for name in sorted(all_requested):
        resolved = available.get(name)
        if resolved is None:
            continue
        category, source_path = resolved
        target_dir = target_roots[category]
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / source_path.name
        try:
            if source_path.resolve() != target_path.resolve():
                shutil.copy2(source_path, target_path)
        except OSError:
            # Fallback to direct string comparison when resolve() is unavailable.
            if str(source_path) != str(target_path):
                shutil.copy2(source_path, target_path)
        promoted.append(name)

    if promoted:
        sys.stdout.write(f"[itx-gates] Lazy knowledge: promoted {len(promoted)} pattern(s): {', '.join(promoted)}\n")
    if used_regex_fallback:
        sys.stderr.write(
            "[itx-gates] Warning: detected deprecated inline markdown filename fallback for pattern "
            "selection. Prefer structured selection blocks: <!-- selected_patterns: file.md, ... -->\n"
        )

    return findings


def run_generic_checks(
    config: Dict[str, Any],
    event: str,
    workspace: Path,
    policy: Dict[str, Any],
) -> List[Finding]:
    findings: List[Finding] = []
    if event == "after_plan":
        plan_files = _find_plan_files(workspace)
        if not plan_files:
            findings.append(
                {
                    "severity": TIER_1,
                    "rule": "plan-presence",
                    "message": (
                        "No supported plan artifact found after plan generation stage. "
                        "Expected one of: system-design-plan*.md, patch-plan*.md, refactor-plan*.md, "
                        "bugfix-report*.md, migration-plan*.md, tooling-plan*.md, spike-note*.md."
                    ),
                }
            )
        for plan_file in plan_files:
            findings.extend(_validate_plan_content(plan_file, policy))
        findings.extend(_sync_lazy_knowledge(config, workspace, policy))

    if event == "after_tasks":
        task_files = _find_task_files(workspace)
        tasks_required = _tasks_required_for_workspace(workspace, policy)
        if not task_files and tasks_required:
            findings.append(
                {
                    "severity": TIER_1,
                    "rule": "tasks-presence",
                    "message": ("No tasks file found after task generation stage. Expected tasks.md under specs/** or legacy fallback locations."),
                }
            )
        elif task_files:
            findings.extend(_validate_tasks_checkbox_format(task_files))

    if event == "after_implement":
        findings.extend(check_e2e_test_presence(workspace))

    if event == "after_review":
        task_files = _task_files_for_review_scope(workspace, _find_task_files(workspace))
        unchecked_count = 0
        for task_file in task_files:
            text = task_file.read_text(encoding="utf-8", errors="ignore")
            unchecked_count += len(re.findall(r"^\s*-\s+\[\s\]\s+", text, flags=re.MULTILINE))
        if unchecked_count > 0:
            findings.append(
                {
                    "severity": TIER_1,
                    "rule": "completion-tasks-unchecked",
                    "message": (f"Found {unchecked_count} unchecked task checkbox item(s). All tasks must be completed before delivery."),
                }
            )

        feedback_path = workspace / ".specify" / "context" / "gate_feedback.md"
        if feedback_path.exists():
            feedback_text = feedback_path.read_text(encoding="utf-8", errors="ignore")
            if "Severity: `tier2" in feedback_text:
                findings.append(
                    {
                        "severity": TIER_2,
                        "rule": "completion-tier2-outstanding",
                        "message": "Outstanding Tier 2 findings detected in .specify/context/gate_feedback.md.",
                    }
                )

        findings.extend(check_e2e_test_presence(workspace))

    if config.get("execution_mode") == "docker-fallback":
        container_name = (config.get("docker") or {}).get("container_name")
        if not container_name:
            findings.append(
                {
                    "severity": TIER_2,
                    "rule": "docker-container-required",
                    "message": "docker-fallback mode requires docker.container_name in .itx-config.yml",
                }
            )
        else:
            result = run_docker_exec(container_name, ["echo", "itx-gates docker check"])
            if result.returncode != 0:
                findings.append(
                    {
                        "severity": TIER_2,
                        "rule": "docker-exec-failed",
                        "message": result.stderr.strip() or "Failed to execute required command via docker exec",
                    }
                )
    return findings


def _normalize_finding(raw: Dict[str, Any], rule_defaults: Dict[str, Any] | None = None) -> Finding | None:
    severity = str(raw.get("severity", "")).strip()
    rule = str(raw.get("rule", "")).strip()
    message = str(raw.get("message", "")).strip()
    if not rule or not message:
        return None
    defaults = (rule_defaults or {}).get(rule) or {}
    if not severity:
        severity = str(defaults.get("severity", "")).strip()
    if severity not in {TIER_1, TIER_2}:
        return None
    tier_severity = cast(Literal["tier1", "tier2"], severity)
    finding: Finding = {"severity": tier_severity, "rule": rule, "message": message}
    confidence = str(raw.get("confidence", "")).strip().lower()
    remediation_owner = str(raw.get("remediation_owner", "")).strip()
    default_meta = {**RULE_DEFAULT_META.get(rule, {}), **defaults}
    if confidence in {"deterministic", "heuristic"}:
        finding["confidence"] = confidence
    elif confidence:
        sys.stderr.write(f"[itx-gates] Warning: invalid confidence '{confidence}' for rule '{rule}', dropping confidence metadata.\n")
    elif default_meta.get("confidence"):
        default_confidence = str(default_meta["confidence"]).strip().lower()
        if default_confidence in {"deterministic", "heuristic"}:
            finding["confidence"] = default_confidence

    if remediation_owner:
        finding["remediation_owner"] = remediation_owner
    elif default_meta.get("remediation_owner"):
        finding["remediation_owner"] = default_meta["remediation_owner"]

    remediation = str(raw.get("remediation", "")).strip()
    if remediation:
        finding["remediation"] = remediation
    elif rule in RULE_REMEDIATION_HINTS:
        finding["remediation"] = RULE_REMEDIATION_HINTS[rule]
    return finding


def validate_findings(raw_findings: Sequence[Mapping[str, Any]], rule_defaults: Dict[str, Any] | None = None) -> List[Finding]:
    validated: List[Finding] = []
    for item in raw_findings:
        if not isinstance(item, dict):
            sys.stderr.write(f"[itx-gates] Warning: malformed finding dropped (not a mapping): {item}\n")
            continue
        normalized = _normalize_finding(item, rule_defaults=rule_defaults)
        if normalized is None:
            sys.stderr.write(f"[itx-gates] Warning: malformed finding dropped: {item}\n")
            continue
        validated.append(normalized)
    return validated


def dedupe_findings(findings: List[Finding]) -> List[Finding]:
    deduped: List[Finding] = []
    seen: set[tuple[str, str]] = set()
    for item in findings:
        key = (str(item.get("rule", "")), str(item.get("message", "")))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def run_domain_checks(domain: str, workspace: Path, rule_defaults: Dict[str, Any] | None = None) -> List[Finding]:
    module_path = DOMAIN_VALIDATORS.get(domain)
    if not module_path:
        return []
    try:
        module = importlib.import_module(module_path)
        run_func = getattr(module, "run")
        raw_findings = run_func(workspace)
    except Exception as exc:
        return [
            {
                "severity": TIER_2,
                "rule": "validator-execution-failed",
                "message": f"Validator '{module_path}' failed: {exc}",
            }
        ]
    if not isinstance(raw_findings, list):
        return [
            {
                "severity": TIER_2,
                "rule": "validator-invalid-output",
                "message": f"Validator '{module_path}' returned non-list output.",
            }
        ]
    return validate_findings(raw_findings, rule_defaults=rule_defaults)


def main() -> int:
    args = parse_args()
    workspace = Path(args.workspace).resolve()
    event = args.event.strip()

    try:
        config = load_config(workspace)
    except Exception as exc:
        sys.stderr.write(f"[itx-gates] {exc}\n")
        return 1

    policy = load_policy(workspace)
    rule_defaults = policy.get("rules") if isinstance(policy.get("rules"), dict) else {}
    domain = config.get("domain", "base")
    findings: List[Finding] = []
    findings.extend(run_generic_checks(config, event, workspace, policy))
    if event == "after_implement":
        findings.extend(run_domain_checks(domain, workspace, rule_defaults=rule_defaults))
    findings = validate_findings(findings, rule_defaults=rule_defaults)
    findings = dedupe_findings(findings)

    tier2 = [f for f in findings if f.get("severity") == TIER_2]
    tier1 = [f for f in findings if f.get("severity") == TIER_1]

    gate_cfg = policy.get("gate") or {}
    default_retry_limit = _parse_retry_limit(gate_cfg.get("default_max_tier1_retries", 3), 3)
    configured_retry_limit = (config.get("gate") or {}).get(
        "max_tier1_retries",
        default_retry_limit,
    )
    tier1_retry_limit = _parse_retry_limit(configured_retry_limit, default_retry_limit)
    heuristic_retry_escalates = _parse_bool(gate_cfg.get("heuristic_retry_escalates", False), default=False)
    prior_retry_state = read_tier1_retry_state(workspace)

    if tier1 and not tier2:
        next_retry_state = dict(prior_retry_state)
        escalated_findings: List[Finding] = []
        processed_retry_keys: set[str] = set()
        for finding in tier1:
            key = _retry_key(event, finding)
            if key in processed_retry_keys:
                continue
            processed_retry_keys.add(key)
            retry_count = next_retry_state.get(key, 0) + 1
            is_heuristic = str(finding.get("confidence", "")).strip().lower() == "heuristic"
            allow_escalation = heuristic_retry_escalates or not is_heuristic
            if allow_escalation and retry_count > tier1_retry_limit:
                escalated_findings.append(
                    {
                        "severity": TIER_2,
                        "rule": f"{finding.get('rule', 'tier1-finding')}-retry-exceeded",
                        "message": (f"{finding.get('message', 'Tier 1 finding retried too many times.')} (retry {retry_count}/{tier1_retry_limit})"),
                    }
                )
            else:
                next_retry_state[key] = retry_count

        if escalated_findings:
            tier2.extend(escalated_findings)
            write_gate_feedback(workspace, event, tier1, tier2, next_retry_state, tier1_retry_limit)
        else:
            write_gate_feedback(workspace, event, tier1, [], next_retry_state, tier1_retry_limit)

    elif tier2:
        write_gate_feedback(workspace, event, tier1, tier2, prior_retry_state, tier1_retry_limit)
    else:
        feedback_path = ensure_feedback_path(workspace)
        if feedback_path.exists():
            feedback_path.unlink()

    if event in {"after_plan", "after_tasks", "after_review"}:
        try:
            _generate_execution_brief(workspace, config, policy)
        except Exception as exc:  # noqa: BLE001 - generation must never break existing gate flow
            sys.stderr.write(f"[itx-gates] Warning: execution-brief generation failed: {exc}\n")

    if tier2:
        sys.stderr.write("[itx-gates] Critical gate failure(s):\n")
        sys.stderr.write(json.dumps(tier2, indent=2) + "\n")
        return 1

    if tier1:
        sys.stdout.write("[itx-gates] Non-critical failures captured for auto-correction.\n")
        return 0

    sys.stdout.write("[itx-gates] Gates passed.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
