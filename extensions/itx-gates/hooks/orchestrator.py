#!/usr/bin/env python3
"""Itexus gates orchestrator implementing Tier 1/Tier 2 flow control."""

from __future__ import annotations

import argparse
import ast
import importlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validators import Finding, should_skip_path


TIER_1 = "tier1"
TIER_2 = "tier2"
RETRY_STATE_PREFIX = "- Retry-State: `"


DOMAIN_VALIDATORS: Dict[str, str] = {
    "fintech-trading": "validators.trading_ast",
    "fintech-banking": "validators.banking_heuristic",
    "healthcare": "validators.health_regex",
}

# Inline fallback used when policy.yml is not available in the workspace.
_DEFAULT_POLICY: Dict[str, Any] = {
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
        sys.stderr.write(
            f"[itx-gates] Warning: missing policy file at {policy_path}; using built-in defaults.\n"
        )
        return dict(_DEFAULT_POLICY)
    try:
        data = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError) as exc:
        sys.stderr.write(
            f"[itx-gates] Warning: failed to parse policy file at {policy_path}: {exc}; using built-in defaults.\n"
        )
        return dict(_DEFAULT_POLICY)
    if isinstance(data, dict):
        return data
    sys.stderr.write(
        f"[itx-gates] Warning: policy file at {policy_path} is not a mapping; using built-in defaults.\n"
    )
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
        sys.stderr.write(
            f"[itx-gates] Warning: invalid gate.max_tier1_retries value '{raw_value}'; using default {default}.\n"
        )
        return default
    if parsed < 0:
        sys.stderr.write(
            f"[itx-gates] Warning: negative gate.max_tier1_retries value '{raw_value}'; using default {default}.\n"
        )
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
                (
                    f"- Confidence: `{item.get('confidence')}`"
                    if item.get("confidence")
                    else ""
                ),
                (
                    f"- Remediation: {item.get('remediation')}"
                    if item.get("remediation")
                    else ""
                ),
                (
                    f"- Remediation Owner: `{item.get('remediation_owner')}`"
                    if item.get("remediation_owner")
                    else ""
                ),
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
        workspace.glob("system-design-plan*.md"),
        workspace.glob("patch-plan*.md"),
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
                    "message": (
                        f"{test_file}: E2E test appears to contain placeholder content "
                        "(TODO/TBD/FIXME or pass body)."
                    ),
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


def _validate_plan_content(plan_path: Path, policy: Dict[str, Any]) -> List[Finding]:
    """Check that mandatory sections exist and are not just template placeholders."""
    findings: List[Finding] = []
    content = plan_path.read_text(encoding="utf-8")

    tier = _match_plan_tier(plan_path, policy)
    if tier is None:
        return findings

    mandatory_headings: List[str] = tier.get("mandatory_sections") or []
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
            line
            for line in section_body.splitlines()
            if line.strip()
            and not line.strip().startswith("|--")
            and not line.strip().startswith("> ")
        ]

        real_content = [
            line
            for line in content_lines
            if not any(marker in line for marker in placeholder_markers)
        ]

        if not real_content:
            findings.append(
                {
                    "severity": TIER_1,
                    "rule": "plan-section-placeholder",
                    "message": f"Section '{heading}' in {plan_path.name} contains only placeholder text — fill it with actual design decisions.",
                }
            )

    return findings


def _extract_selected_patterns(
    plan_text: str, known_filenames: set[str] | None = None
) -> tuple[set[str] | None, bool]:
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
        names = {
            name.strip().lower()
            for name in raw.split(",")
            if name.strip()
        }
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
        sys.stderr.write(
            "[itx-gates] Warning: malformed knowledge-manifest.json: 'files' must be a mapping; ignoring.\n"
        )
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
        tier = _match_plan_tier(plan_file, policy)
        selection_mode = str((tier or {}).get("pattern_selection", "required")).lower()

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
            sys.stderr.write(
                "[itx-gates] Warning: malformed knowledge-manifest.json entry ignored.\n"
            )
            continue
        source_raw = entry.get("source", "")
        category = str(entry.get("category", "")).strip()
        if not isinstance(source_raw, str):
            sys.stderr.write(
                f"[itx-gates] Warning: malformed manifest source for '{name_key}' ignored.\n"
            )
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
                "message": (
                    "Some plan-selected patterns could not be resolved: "
                    + ", ".join(unresolved)
                ),
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
        sys.stdout.write(
            f"[itx-gates] Lazy knowledge: promoted {len(promoted)} pattern(s): {', '.join(promoted)}\n"
        )
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
                        "No plan file found after plan generation stage. Use either "
                        "system-design-plan-template.md or patch-plan-template.md."
                    ),
                }
            )
        for plan_file in plan_files:
            findings.extend(_validate_plan_content(plan_file, policy))
        findings.extend(_sync_lazy_knowledge(config, workspace, policy))

    if event == "after_tasks":
        task_files = _find_task_files(workspace)
        if not task_files:
            findings.append(
                {
                    "severity": TIER_1,
                    "rule": "tasks-presence",
                    "message": (
                        "No tasks file found after task generation stage. "
                        "Expected tasks.md under specs/** or legacy fallback locations."
                    ),
                }
            )
        else:
            findings.extend(_validate_tasks_checkbox_format(task_files))

    if event == "after_implement":
        findings.extend(check_e2e_test_presence(workspace))

    if event == "after_review":
        task_files = _find_task_files(workspace)
        unchecked_count = 0
        for task_file in task_files:
            text = task_file.read_text(encoding="utf-8", errors="ignore")
            unchecked_count += len(re.findall(r"^\s*-\s+\[\s\]\s+", text, flags=re.MULTILINE))
        if unchecked_count > 0:
            findings.append(
                {
                    "severity": TIER_1,
                    "rule": "completion-tasks-unchecked",
                    "message": (
                        f"Found {unchecked_count} unchecked task checkbox item(s). "
                        "All tasks must be completed before delivery."
                    ),
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
                        "message": result.stderr.strip()
                        or "Failed to execute required command via docker exec",
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
    finding: Finding = {"severity": severity, "rule": rule, "message": message}
    confidence = str(raw.get("confidence", "")).strip().lower()
    remediation_owner = str(raw.get("remediation_owner", "")).strip()
    default_meta = {**RULE_DEFAULT_META.get(rule, {}), **defaults}
    if confidence in {"deterministic", "heuristic"}:
        finding["confidence"] = confidence
    elif confidence:
        sys.stderr.write(
            f"[itx-gates] Warning: invalid confidence '{confidence}' for rule '{rule}', dropping confidence metadata.\n"
        )
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


def validate_findings(raw_findings: List[Dict[str, Any]], rule_defaults: Dict[str, Any] | None = None) -> List[Finding]:
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
    default_retry_limit = _parse_retry_limit(
        gate_cfg.get("default_max_tier1_retries", 3), 3
    )
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
                        "message": (
                            f"{finding.get('message', 'Tier 1 finding retried too many times.')} "
                            f"(retry {retry_count}/{tier1_retry_limit})"
                        ),
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
