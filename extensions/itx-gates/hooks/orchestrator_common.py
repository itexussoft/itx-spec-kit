#!/usr/bin/env python3
"""Shared gate orchestrator helpers and policy-driven validation primitives."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Mapping, Sequence, cast

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validators import Finding, should_skip_path

TIER_1: Literal["tier1"] = "tier1"
TIER_2: Literal["tier2"] = "tier2"
RETRY_STATE_PREFIX = "- Retry-State: `"
HOOK_MODES = {"auto", "manual", "hybrid"}


DOMAIN_VALIDATORS: Dict[str, str] = {
    "fintech-trading": "validators.trading_ast",
    "fintech-banking": "validators.sast_validator",
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
            "traceability_modes": ["requirement", "adr"],
            "traceability_required": False,
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
            "traceability_modes": ["requirement", "invariant", "risk", "incident", "adr"],
            "traceability_required": False,
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
            "traceability_modes": ["invariant", "risk", "adr"],
            "traceability_required": False,
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
            "traceability_modes": ["incident", "risk", "requirement"],
            "traceability_required": False,
        },
        "migration": {
            "allowed_templates": ["migration-plan-template.md"],
            "mandatory_sections": [
                "## 1. Migration Goal",
                "## 2. Current State / Target State",
                "## 3. Transition Plan",
                "## 4. Compatibility Window",
                "## 5. Rollback Strategy",
                "## 7. Regression and Verification",
            ],
            "pattern_selection": "required",
            "task_policy": "required",
            "testing_expectation": "e2e-required",
            "gate_profile": "migration-safe",
            "traceability_modes": ["invariant", "risk", "adr"],
            "traceability_required": True,
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
            "traceability_modes": ["requirement", "risk", "adr"],
            "traceability_required": False,
        },
        "spike": {
            "allowed_templates": ["spike-note-template.md"],
            "mandatory_sections": [
                "## 1. Question",
                "## 2. Constraints",
                "## 3. Options Explored",
                "## 4. Recommendation",
                "## 5. Next Decision",
            ],
            "pattern_selection": "optional",
            "task_policy": "optional",
            "testing_expectation": "advisory",
            "gate_profile": "spike-light",
            "traceability_modes": ["risk", "invariant"],
            "traceability_required": False,
        },
        "modify": {
            "allowed_templates": ["modify-plan-template.md"],
            "mandatory_sections": [
                "## 1. Problem Statement",
                "## 2. Files / Modules Affected",
                "## 5. Regression Testing",
            ],
            "pattern_selection": "optional",
            "task_policy": "optional",
            "testing_expectation": "regression-required",
            "gate_profile": "patch-safe",
            "traceability_modes": ["requirement", "invariant", "risk"],
            "traceability_required": True,
        },
        "hotfix": {
            "allowed_templates": ["hotfix-report-template.md"],
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
            "gate_profile": "hotfix-fast",
            "traceability_modes": ["incident"],
            "traceability_required": True,
        },
        "deprecate": {
            "allowed_templates": ["deprecate-plan-template.md"],
            "mandatory_sections": [
                "## 1. Migration Goal",
                "## 2. Current State / Target State",
                "## 3. Transition Plan",
                "## 4. Compatibility Window",
                "## 5. Rollback Strategy",
                "## 6. Dependency Impact and Consumer Rollout",
                "## 7. Regression and Verification",
            ],
            "pattern_selection": "optional",
            "task_policy": "required",
            "testing_expectation": "e2e-required",
            "gate_profile": "migration-safe",
            "traceability_modes": ["adr", "requirement"],
            "traceability_required": True,
        },
    },
    "traceability_modes": {
        "requirement": {"id_field": "requirement_id"},
        "invariant": {"id_field": "invariant_id"},
        "risk": {"id_field": "risk_id"},
        "incident": {"id_field": "incident_id"},
        "adr": {"id_field": "adr_id"},
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
    "gate": {"default_max_tier1_retries": 3, "heuristic_retry_escalates": False, "auto_retry": {"max_attempts": 3}},
    "quality": {
        "security": {
            "enabled": False,
            "provider": "noop",
            "on_missing_binary": "warn",
            "compat_heuristic_fallback": False,
            "domains": {
                "fintech-banking": {
                    "enabled": True,
                    "provider": "semgrep",
                    "on_missing_binary": "warn",
                    "compat_heuristic_fallback": True,
                }
            },
        }
    },
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
        "banking-sql-injection-ledger-query": {
            "severity": "tier2",
            "confidence": "deterministic",
            "remediation_owner": "security-team",
        },
        "banking-raw-pan-storage": {
            "severity": "tier1",
            "confidence": "deterministic",
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
        "sast-provider-unavailable": {
            "severity": "tier1",
            "confidence": "heuristic",
            "remediation_owner": "security-team",
        },
        "sast-provider-failed": {
            "severity": "tier1",
            "confidence": "heuristic",
            "remediation_owner": "security-team",
        },
        "sast-provider-output-invalid": {
            "severity": "tier1",
            "confidence": "heuristic",
            "remediation_owner": "security-team",
        },
        "sast-ruleset-missing": {
            "severity": "tier1",
            "confidence": "heuristic",
            "remediation_owner": "security-team",
        },
        "sast-provider-unknown": {
            "severity": "tier1",
            "confidence": "heuristic",
            "remediation_owner": "security-team",
        },
        "sast-provider-fallback-active": {
            "severity": "tier1",
            "confidence": "heuristic",
            "remediation_owner": "security-team",
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
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON result")
    return parser.parse_args()


def load_config(workspace: Path) -> Dict:
    config_path = workspace / ".itx-config.yml"
    if not config_path.exists():
        raise FileNotFoundError(f"Missing config: {config_path}")
    text = config_path.read_text(encoding="utf-8")
    config = yaml.safe_load(text) or {}
    if not isinstance(config, dict):
        return {}
    if not isinstance(config.get("hook_mode"), str) or config.get("hook_mode", "").strip() not in HOOK_MODES:
        config["hook_mode"] = "hybrid"
    return config


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


def ensure_context_dir(workspace: Path) -> Path:
    context_dir = workspace / ".specify" / "context"
    context_dir.mkdir(parents=True, exist_ok=True)
    return context_dir


def ensure_feedback_path(workspace: Path) -> Path:
    return ensure_context_dir(workspace) / "gate_feedback.md"


def execution_brief_path(workspace: Path) -> Path:
    return ensure_context_dir(workspace) / "execution-brief.md"


def audit_log_path(workspace: Path) -> Path:
    return ensure_context_dir(workspace) / "audit-log.md"


def gate_state_path(workspace: Path) -> Path:
    return ensure_context_dir(workspace) / "gate-state.yml"


def gate_events_path(workspace: Path) -> Path:
    return ensure_context_dir(workspace) / "gate-events.jsonl"


def last_gate_summary_path(workspace: Path) -> Path:
    return ensure_context_dir(workspace) / "last-gate-summary.md"


def _artifact_record(workspace: Path, path: Path) -> Dict[str, Any] | None:
    try:
        resolved = path.resolve()
        resolved.relative_to(workspace.resolve())
    except (OSError, ValueError):
        return None
    if not resolved.exists() or not resolved.is_file():
        return None
    stat = resolved.stat()
    try:
        sha256 = hashlib.sha256(resolved.read_bytes()).hexdigest()
    except OSError:
        return None
    return {
        "path": str(resolved.relative_to(workspace)),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "sha256": sha256,
    }


def _dedupe_paths(paths: Sequence[Path]) -> List[Path]:
    deduped: List[Path] = []
    seen: set[Path] = set()
    for path in paths:
        try:
            resolved = path.resolve()
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        deduped.append(resolved)
    return deduped


def collect_artifact_records(workspace: Path, paths: Sequence[Path]) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for path in _dedupe_paths(paths):
        record = _artifact_record(workspace, path)
        if record is not None:
            records.append(record)
    records.sort(key=lambda item: str(item.get("path", "")))
    return records


def load_gate_state(workspace: Path) -> Dict[str, Any] | None:
    state_path = gate_state_path(workspace)
    if not state_path.exists():
        return None
    try:
        data = yaml.safe_load(state_path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def _gate_generic_input_files(workspace: Path) -> List[Path]:
    files = [
        workspace / ".itx-config.yml",
        workspace / ".specify" / "policy.yml",
        workspace / ".specify" / "context" / "workflow-state.yml",
    ]
    return [path for path in files if path.exists()]


def resolve_gate_input_files(workspace: Path, event: str, policy: Dict[str, Any]) -> List[Path]:
    paths: List[Path] = list(_gate_generic_input_files(workspace))
    if event == "after_plan":
        paths.extend(_plan_files_for_task_policy_resolution(workspace))
    elif event == "after_tasks":
        paths.extend(_plan_files_for_task_policy_resolution(workspace))
        paths.extend(_task_files_for_review_scope(workspace, _find_task_files(workspace)))
    elif event == "after_implement":
        paths.extend(_task_files_for_review_scope(workspace, _find_task_files(workspace)))
        paths.extend(_find_e2e_test_files(workspace))
    elif event == "after_review":
        paths.extend(_task_files_for_review_scope(workspace, _find_task_files(workspace)))
        feedback = ensure_feedback_path(workspace)
        if feedback.exists():
            paths.append(feedback)
    return _dedupe_paths(paths)


def resolve_gate_output_files(workspace: Path, event: str) -> List[Path]:
    paths = [last_gate_summary_path(workspace)]
    feedback = ensure_feedback_path(workspace)
    if feedback.exists():
        paths.append(feedback)
    if event in {"after_plan", "after_tasks", "after_review"}:
        brief = execution_brief_path(workspace)
        if brief.exists():
            paths.append(brief)
    audit = audit_log_path(workspace)
    if audit.exists():
        paths.append(audit)
    return _dedupe_paths(paths)


def build_gate_state_payload(
    *,
    workspace: Path,
    event: str,
    status: str,
    exit_code: int,
    hook_mode: str,
    started_at: str,
    completed_at: str,
    findings: Sequence[Finding],
    input_files: Sequence[Path],
    output_files: Sequence[Path],
) -> Dict[str, Any]:
    metadata = _load_active_workstream_metadata(workspace)
    return {
        "event": event,
        "status": status,
        "exit_code": exit_code,
        "hook_mode": hook_mode,
        "started_at": started_at,
        "completed_at": completed_at,
        "feature": metadata.get("feature"),
        "workstream_id": metadata.get("workstream_id"),
        "work_class": metadata.get("work_class"),
        "artifact_root": metadata.get("artifact_root"),
        "parent_feature": metadata.get("parent_feature"),
        "branch": metadata.get("branch"),
        "tier1_count": sum(1 for finding in findings if finding.get("severity") == TIER_1),
        "tier2_count": sum(1 for finding in findings if finding.get("severity") == TIER_2),
        "input_artifacts": collect_artifact_records(workspace, input_files),
        "output_artifacts": collect_artifact_records(workspace, output_files),
        "findings": list(findings),
    }


def write_gate_state(workspace: Path, payload: Mapping[str, Any]) -> None:
    state_path = gate_state_path(workspace)
    state_path.write_text(yaml.safe_dump(dict(payload), sort_keys=False, allow_unicode=True), encoding="utf-8")


def append_gate_event(workspace: Path, payload: Mapping[str, Any]) -> None:
    events_path = gate_events_path(workspace)
    with events_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(payload), ensure_ascii=False, sort_keys=False) + "\n")


def write_last_gate_summary(
    workspace: Path,
    *,
    event: str,
    status: str,
    exit_code: int,
    hook_mode: str,
    tier1_count: int,
    tier2_count: int,
    workstream_id: str | None,
    artifact_root: str | None,
) -> None:
    summary_path = last_gate_summary_path(workspace)
    next_action = "Inspect .specify/context/gate_feedback.md before continuing." if tier1_count or tier2_count else "No remediation required."
    if tier2_count:
        next_action = "Stop delivery and resolve Tier 2 findings before proceeding."
    lines = [
        "# Last Gate Summary",
        "",
        f"- Event: `{event}`",
        f"- Status: `{status}`",
        f"- Exit Code: `{exit_code}`",
        f"- Hook Mode: `{hook_mode}`",
        f"- Tier 1 Findings: `{tier1_count}`",
        f"- Tier 2 Findings: `{tier2_count}`",
        f"- Workstream: `{workstream_id or 'workspace'}`",
        f"- Artifact Root: `{artifact_root or 'workspace'}`",
        "",
        "## Next Action",
        next_action,
        "",
    ]
    summary_path.write_text("\n".join(lines), encoding="utf-8")


def evaluate_gate_freshness(
    workspace: Path,
    event: str,
    policy: Dict[str, Any],
) -> tuple[bool, str]:
    state = load_gate_state(workspace)
    if state is None:
        return False, "missing-state"
    if str(state.get("event", "")).strip() != event:
        return False, "event-mismatch"

    current_inputs = collect_artifact_records(workspace, resolve_gate_input_files(workspace, event, policy))
    recorded_inputs = state.get("input_artifacts")
    if not isinstance(recorded_inputs, list):
        return False, "missing-input-snapshot"
    if current_inputs != recorded_inputs:
        return False, "inputs-changed"

    recorded_outputs = state.get("output_artifacts")
    if isinstance(recorded_outputs, list):
        for record in recorded_outputs:
            if not isinstance(record, dict):
                return False, "invalid-output-snapshot"
            rel_path = record.get("path")
            if not isinstance(rel_path, str) or not rel_path.strip():
                return False, "invalid-output-snapshot"
            if not (workspace / rel_path).exists():
                return False, "output-missing"

    summary = last_gate_summary_path(workspace)
    if not summary.exists():
        return False, "summary-missing"
    return True, "fresh"


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
        return subprocess.CompletedProcess(full_cmd, 127, stdout="", stderr=f"Docker CLI not found: {exc}")
    except OSError as exc:
        return subprocess.CompletedProcess(full_cmd, 1, stdout="", stderr=f"Failed to execute docker command: {exc}")


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
    "banking-sql-injection-ledger-query": "Use parameterized queries for ledger/account SQL paths and remove string interpolation.",
    "banking-raw-pan-storage": "Remove raw PAN persistence and enforce tokenization/masking controls.",
    "sast-provider-unavailable": "Install and expose the configured SAST binary locally or switch provider for this workspace.",
    "sast-provider-failed": "Inspect SAST stderr output and fix provider configuration before rerunning gates.",
    "sast-provider-output-invalid": "Validate provider output format and pinned version compatibility.",
    "sast-ruleset-missing": "Restore the configured SAST ruleset path or configure a valid ruleset location.",
    "sast-provider-unknown": "Set quality.security.provider to one of: semgrep, bandit, noop.",
    "sast-provider-fallback-active": "Install/fix Semgrep to remove compatibility fallback and rely on deterministic SAST output.",
    "saas-tenant-filter-missing": "Add tenant_id filters or RLS session variables for all tenant-scoped queries.",
    "saas-global-cache-key": "Namespace cache keys with tenant id (e.g. t:{tenant_id}:...) to prevent cross-tenant leakage.",
}
RULE_DEFAULT_META: Dict[str, Dict[str, str]] = {
    "trading-no-float-money": {"confidence": "deterministic", "remediation_owner": "domain-team"},
    "e2e-test-presence": {"confidence": "deterministic", "remediation_owner": "feature-team"},
    "tasks-presence": {"confidence": "deterministic", "remediation_owner": "feature-team"},
    "plan-section-missing": {"confidence": "deterministic", "remediation_owner": "feature-team"},
    "banking-sql-injection-ledger-query": {"confidence": "deterministic", "remediation_owner": "security-team"},
    "sast-provider-unavailable": {"confidence": "heuristic", "remediation_owner": "security-team"},
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
    plan_files: List[Path] = []
    for pattern in ("*plan*.md", "*report*.md", "*note*.md"):
        for path in sorted((workspace / "specs").glob(f"**/{pattern}")) if (workspace / "specs").exists() else []:
            try:
                rel = path.relative_to(workspace)
            except ValueError:
                continue
            if should_skip_path(rel):
                continue
            lower_name = path.name.lower()
            if (
                "system-design-plan" in lower_name
                or "patch-plan" in lower_name
                or "refactor-plan" in lower_name
                or "bugfix-report" in lower_name
                or "migration-plan" in lower_name
                or "tooling-plan" in lower_name
                or "spike-note" in lower_name
                or "modify-plan" in lower_name
                or "hotfix-report" in lower_name
                or "deprecate-plan" in lower_name
            ):
                plan_files.append(path)
    deduped: List[Path] = []
    seen: set[Path] = set()
    for path in plan_files:
        if path not in seen:
            deduped.append(path)
            seen.add(path)
    return deduped


def _find_task_files(workspace: Path) -> List[Path]:
    task_files: List[Path] = []
    for path in sorted(workspace.glob("**/tasks.md")):
        try:
            rel = path.relative_to(workspace)
        except ValueError:
            continue
        if rel.parts and rel.parts[0] != ".specify" and should_skip_path(rel):
            continue
        task_files.append(path)
    return task_files


def _is_bare_task_item(line: str) -> bool:
    stripped = line.lstrip()
    if not stripped.startswith("- "):
        return False
    if re.match(r"^-\s+\[[ xX]\]\s+", stripped):
        return False
    return bool(re.match(r"^-\s+[A-Za-z0-9T]", stripped))


def _classify_heading_scope(heading_text: str) -> str | None:
    normalized = heading_text.strip().lower()
    if normalized == "tasks" or normalized.endswith(" tasks"):
        return "tasks"
    if normalized in {"notes", "context", "references", "links", "metadata", "background", "format rules"}:
        return "notes"
    return None


def _validate_tasks_checkbox_format(task_files: List[Path]) -> List[Finding]:
    findings: List[Finding] = []
    for task_file in task_files:
        lines = task_file.read_text(encoding="utf-8", errors="ignore").splitlines()
        heading_stack: List[str] = []
        scoped_mode: str | None = None
        for line in lines:
            stripped = line.strip()
            heading_match = re.match(r"^(#{1,6})\s+(.*)$", line)
            if heading_match:
                level = len(heading_match.group(1))
                text = heading_match.group(2).strip()
                while len(heading_stack) >= level:
                    heading_stack.pop()
                heading_stack.append(text)
                scope = _classify_heading_scope(text)
                if scope == "tasks":
                    scoped_mode = "tasks"
                elif scope == "notes":
                    scoped_mode = "notes"
                continue

            if not stripped:
                continue
            if scoped_mode == "notes":
                continue
            if _is_bare_task_item(line):
                findings.append(
                    {
                        "severity": TIER_1,
                        "rule": "tasks-checkbox-format",
                        "message": (
                            f"Tasks file '{task_file.relative_to(task_file.parents[2] if len(task_file.parents) > 2 else task_file.parent)}' "
                            "contains bare list items. Use '- [ ]' or '- [x]' checkbox syntax for every task."
                        ),
                    }
                )
                break
    return findings


def _find_e2e_test_files(workspace: Path) -> List[Path]:
    files: List[Path] = []
    for pattern in E2E_FILE_PATTERNS:
        for path in sorted(workspace.glob(f"**/{pattern}")):
            try:
                rel = path.relative_to(workspace)
            except ValueError:
                continue
            if should_skip_path(rel):
                continue
            files.append(path)
    deduped: List[Path] = []
    seen: set[Path] = set()
    for path in files:
        if path not in seen:
            deduped.append(path)
            seen.add(path)
    return deduped


def _e2e_family(path: Path) -> str:
    name = path.name
    if name.startswith("e2e_test_") and name.endswith(".py"):
        return name[len("e2e_test_") : -len(".py")]
    suffixes = (".e2e-spec.ts", ".e2e-spec.js", ".e2e.test.ts", ".e2e.test.js")
    for suffix in suffixes:
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def _python_has_assertions(text: str) -> bool:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.Assert):
            return True
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr.startswith("assert"):
                return True
    return False


def _strip_js_ts_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r"//.*", "", text)
    return text


def _js_ts_has_assertions(text: str) -> bool:
    stripped = _strip_js_ts_comments(text)
    return bool(JS_TS_EXPECT_RE.search(stripped) or JS_TS_ASSERT_RE.search(stripped) or JS_TS_SHOULD_RE.search(stripped))


def _e2e_has_assertion(path: Path, text: str) -> bool:
    if path.suffix == ".py":
        return _python_has_assertions(text)
    if path.suffix in {".ts", ".js"}:
        return _js_ts_has_assertions(text)
    return False


def _has_placeholder_test_content(path: Path, text: str) -> bool:
    if E2E_PLACEHOLDER_RE.search(text):
        return True
    if path.suffix == ".py" and E2E_PY_PASS_RE.search(text):
        return True
    return False


def check_e2e_test_presence(workspace: Path) -> List[Finding]:
    findings: List[Finding] = []
    test_files = _find_e2e_test_files(workspace)
    if not test_files:
        return [
            {
                "severity": TIER_1,
                "rule": "e2e-test-presence",
                "message": "No E2E tests found. Add at least one E2E test file before implementation completes.",
            }
        ]

    family_has_assertion: Dict[str, bool] = {}
    for path in test_files:
        family = _e2e_family(path)
        family_has_assertion.setdefault(family, False)
        text = path.read_text(encoding="utf-8", errors="ignore")
        has_assertion = _e2e_has_assertion(path, text)
        if has_assertion:
            family_has_assertion[family] = True
        else:
            findings.append(
                {
                    "severity": TIER_1,
                    "rule": "e2e-test-empty",
                    "message": f"E2E test '{path.name}' does not contain explicit assertions.",
                }
            )
        if _has_placeholder_test_content(path, text):
            findings.append(
                {
                    "severity": TIER_1,
                    "rule": "e2e-test-placeholder",
                    "message": f"E2E test '{path.name}' appears to contain placeholder content.",
                }
            )

    for family, has_assertion in family_has_assertion.items():
        if not has_assertion:
            findings.append(
                {
                    "severity": TIER_1,
                    "rule": "e2e-test-family-empty",
                    "message": f"E2E family '{family}' has no test file with assertions.",
                }
            )
    return findings


def _match_plan_tier(plan_path: Path, policy: Dict[str, Any]) -> Dict[str, Any] | None:
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
    plan_tiers = policy.get("plan_tiers")
    if not isinstance(plan_tiers, dict):
        return None

    direct = plan_tiers.get(work_class)
    if isinstance(direct, dict):
        return direct

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
    content = plan_path.read_text(encoding="utf-8")
    frontmatter, _ = _split_frontmatter(content)
    raw_work_class = frontmatter.get("work_class")
    legacy_work_class = _resolve_legacy_work_class(plan_path, policy)

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


def _entry_requires_e2e_checks(policy_entry: Mapping[str, Any]) -> bool:
    testing_expectation = str(policy_entry.get("testing_expectation", "")).strip().lower()
    return testing_expectation != "advisory"


def _traceability_mode_id_fields(policy: Dict[str, Any]) -> Dict[str, str]:
    raw_modes = policy.get("traceability_modes")
    if not isinstance(raw_modes, dict):
        raw_modes = _DEFAULT_POLICY.get("traceability_modes", {})
    mapping: Dict[str, str] = {}
    if not isinstance(raw_modes, dict):
        return mapping
    for mode, details in raw_modes.items():
        if not isinstance(mode, str) or not isinstance(details, dict):
            continue
        id_field = details.get("id_field")
        if isinstance(id_field, str) and id_field.strip():
            mapping[mode.strip().lower()] = id_field.strip()
    return mapping


def _validate_plan_traceability(
    *,
    plan_path: Path,
    frontmatter: Mapping[str, Any],
    policy_entry: Mapping[str, Any],
    policy: Dict[str, Any],
) -> List[Finding]:
    findings: List[Finding] = []
    mode_to_id = _traceability_mode_id_fields(policy)
    if not mode_to_id:
        return findings

    required = bool(policy_entry.get("traceability_required", False))
    allowed_raw = policy_entry.get("traceability_modes")
    allowed_modes: set[str] = set()
    if isinstance(allowed_raw, list):
        for item in allowed_raw:
            if isinstance(item, str) and item.strip():
                allowed_modes.add(item.strip().lower())
    if not allowed_modes:
        allowed_modes = set(mode_to_id.keys())

    raw_mode = frontmatter.get("traceability_mode")
    traceability_mode: str | None = None
    if isinstance(raw_mode, str) and raw_mode.strip():
        traceability_mode = raw_mode.strip().lower()
    elif raw_mode is not None:
        findings.append(
            {
                "severity": TIER_1,
                "rule": "plan-traceability-mode-unresolved",
                "message": f"Plan '{plan_path.name}' has invalid non-string traceability_mode.",
            }
        )
        return findings

    known_id_fields = set(mode_to_id.values())
    present_id_fields = []
    for field in known_id_fields:
        value = frontmatter.get(field)
        if isinstance(value, str) and value.strip():
            present_id_fields.append(field)

    if required and not traceability_mode:
        findings.append(
            {
                "severity": TIER_1,
                "rule": "plan-traceability-missing",
                "message": (
                    f"Plan '{plan_path.name}' is missing required traceability_mode. "
                    "Declare one mode from policy.traceability_modes with the matching id field."
                ),
            }
        )
        return findings

    if not traceability_mode:
        return findings

    if traceability_mode not in mode_to_id:
        findings.append(
            {
                "severity": TIER_1,
                "rule": "plan-traceability-mode-unresolved",
                "message": (
                    f"Plan '{plan_path.name}' has unknown traceability_mode '{traceability_mode}'. "
                    "Use one of: requirement, invariant, risk, incident, adr."
                ),
            }
        )
        return findings

    if traceability_mode not in allowed_modes:
        findings.append(
            {
                "severity": TIER_1,
                "rule": "plan-traceability-mode-disallowed",
                "message": (
                    f"Plan '{plan_path.name}' uses traceability_mode '{traceability_mode}' "
                    "which is not allowed for this work_class."
                ),
            }
        )
        return findings

    expected_id_field = mode_to_id[traceability_mode]
    expected_id = frontmatter.get(expected_id_field)
    if not (isinstance(expected_id, str) and expected_id.strip()):
        findings.append(
            {
                "severity": TIER_1,
                "rule": "plan-traceability-id-missing",
                "message": (
                    f"Plan '{plan_path.name}' declares traceability_mode '{traceability_mode}' "
                    f"but is missing '{expected_id_field}'."
                ),
            }
        )
        return findings

    if len(present_id_fields) > 1:
        findings.append(
            {
                "severity": TIER_1,
                "rule": "plan-traceability-id-ambiguous",
                "message": (
                    f"Plan '{plan_path.name}' declares multiple traceability id fields ({', '.join(sorted(present_id_fields))}). "
                    "Keep only one primary id field matching traceability_mode."
                ),
            }
        )
    return findings


def _load_workflow_state_data(workspace: Path) -> Dict[str, Any] | None:
    state_path = workspace / ".specify" / "context" / "workflow-state.yml"
    if not state_path.exists():
        return None
    try:
        data = yaml.safe_load(state_path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    return data


def _workflow_state_string(data: Mapping[str, Any], key: str) -> str | None:
    raw_value = data.get(key)
    if not isinstance(raw_value, str):
        return None
    normalized = raw_value.strip()
    return normalized or None


def _normalize_workspace_relative_path(workspace: Path, raw_path: str) -> Path | None:
    candidate = Path(raw_path.strip())
    if not raw_path.strip() or candidate.is_absolute():
        return None
    workspace_root = workspace.resolve()
    resolved_candidate = (workspace / candidate).resolve()
    try:
        resolved_candidate.relative_to(workspace_root)
    except ValueError:
        return None
    return resolved_candidate


def _load_active_workstream_metadata(workspace: Path) -> Dict[str, str]:
    data = _load_workflow_state_data(workspace)
    if data is None:
        return {}
    metadata: Dict[str, str] = {}
    for key in ("feature", "workstream_id", "work_class", "artifact_root", "parent_feature", "branch"):
        value = _workflow_state_string(data, key)
        if value:
            metadata[key] = value
    return metadata


def _resolve_active_artifact_root_from_workflow_state(workspace: Path) -> Path | None:
    metadata = _load_active_workstream_metadata(workspace)
    raw_artifact_root = metadata.get("artifact_root")
    if raw_artifact_root:
        normalized = _normalize_workspace_relative_path(workspace, raw_artifact_root)
        if normalized is not None:
            return normalized

    workstream_id = metadata.get("workstream_id")
    if workstream_id:
        inferred = _normalize_workspace_relative_path(workspace, f"specs/{workstream_id}")
        if inferred is not None:
            return inferred

    feature = metadata.get("feature")
    if feature:
        inferred = _normalize_workspace_relative_path(workspace, f"specs/{feature}")
        if inferred is not None:
            return inferred

    return None


def _load_active_feature_from_workflow_state(workspace: Path) -> str | None:
    metadata = _load_active_workstream_metadata(workspace)
    feature = metadata.get("feature") or metadata.get("parent_feature")
    return feature or None


def _plan_files_for_task_policy_resolution(workspace: Path) -> List[Path]:
    all_plan_files = _find_plan_files(workspace)
    if not all_plan_files:
        return []

    active_artifact_root = _resolve_active_artifact_root_from_workflow_state(workspace)
    if active_artifact_root is None:
        return all_plan_files

    scoped: List[Path] = []
    for plan_file in all_plan_files:
        try:
            plan_file.relative_to(active_artifact_root)
        except ValueError:
            continue
        scoped.append(plan_file)
    return scoped or all_plan_files


def _task_files_for_review_scope(workspace: Path, task_files: Sequence[Path]) -> List[Path]:
    active_artifact_root = _resolve_active_artifact_root_from_workflow_state(workspace)
    if active_artifact_root is None:
        return list(task_files)

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
            task_file.relative_to(active_artifact_root)
        except ValueError:
            continue
        scoped.append(task_file)
    return scoped


def _task_files_for_execution_brief_scope(workspace: Path, task_files: Sequence[Path], plan_path: Path) -> List[Path]:
    active_artifact_root = _resolve_active_artifact_root_from_workflow_state(workspace)
    if active_artifact_root is not None:
        return _task_files_for_review_scope(workspace, task_files)

    try:
        plan_rel = plan_path.relative_to(workspace)
    except ValueError:
        return []
    if len(plan_rel.parts) < 2 or plan_rel.parts[0] != "specs":
        return []

    artifact_root = plan_path.parent
    scoped: List[Path] = []
    for task_file in task_files:
        try:
            task_file.relative_to(artifact_root)
        except ValueError:
            continue
        scoped.append(task_file)
    return scoped


def _tasks_required_for_workspace(workspace: Path, policy: Dict[str, Any]) -> bool:
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


def _e2e_required_for_workspace(workspace: Path, policy: Dict[str, Any]) -> bool:
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

    return any(_entry_requires_e2e_checks(entry) for entry in resolved_entries)


def _validate_plan_content(plan_path: Path, policy: Dict[str, Any]) -> List[Finding]:
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

    findings.extend(
        _validate_plan_traceability(
            plan_path=plan_path,
            frontmatter=frontmatter,
            policy_entry=policy_entry,
            policy=policy,
        )
    )

    mandatory_headings: List[str] = policy_entry.get("mandatory_sections") or []
    placeholder_markers: List[str] = policy.get("placeholder_markers") or []
    sections = _extract_markdown_h2_sections(content)

    generic_table_headers = {
        "option",
        "pros",
        "cons",
        "risk",
        "mitigation",
        "behavior path",
        "changed behavior",
        "changed area",
        "test type",
        "file",
        "dependent consumer",
        "owner",
        "rollout action",
        "target date",
        "pattern",
        "file reference",
        "why it applies",
    }
    template_instruction_italics = {
        "state the target state and why this migration is needed now.",
        "describe the before and after states at a system level.",
        "list phased steps for safe rollout, including sequencing and checkpoints.",
        "list only the patterns needed for this migration design.",
        "in lazy knowledge mode, use a structured selection block to materialize",
        "needed files. use `none` if no patterns are required:",
        "define temporary compatibility behavior and exit criteria.",
        "define rollback triggers, mechanics, and recovery path.",
        "describe data integrity checks, backup safeguards, and migration safety controls.",
        "list regression and verification checks required before and after cutover.",
        "state the decision question the spike is intended to answer.",
        "list hard constraints (time, architecture, compliance, interfaces, performance).",
        "summarize options explored and key findings.",
        "state the preferred option and rationale.",
        "state the immediate follow-up decision or implementation step.",
        "one short paragraph describing the behavior change request.",
        "list impacted files, modules, or services and the expected scope of edits.",
        "if any existing patterns from `.specify/patterns/` or `.specify/design-patterns/`",
        "are relevant, list them. if not, write \"n/a\".",
        "capture only concrete risks introduced by this behavior change.",
        "at minimum, declare one regression test that covers the changed behavior path.",
        "describe the observed failure, including user/system impact.",
        "provide deterministic reproduction steps and environment context.",
        "step one",
        "step two",
        "observed result",
        "state the expected correct behavior for the same flow.",
        "name the concrete regression test(s) that will prevent recurrence.",
        "summarize the technical root cause and affected code path.",
        "describe the minimal correction approach and why it is safe.",
        "state what is being deprecated and the target replacement state.",
        "list phased steps for warn -> disable -> remove rollout.",
        "define compatibility duration and explicit exit criteria.",
        "list dependent services, clients, and owners, plus their migration order and communication plan.",
    }

    def _is_placeholder_line(raw_line: str) -> bool:
        stripped = raw_line.strip()
        if any(marker in raw_line for marker in placeholder_markers):
            return True

        # Treat known template instruction text as placeholders.
        if stripped.startswith("_") and stripped.endswith("_"):
            inner = stripped.strip("_").strip().lower()
            if inner in template_instruction_italics:
                return True

        # Ignore template table headers and empty scaffold rows.
        if stripped.startswith("|"):
            cells = [cell.strip().lower() for cell in stripped.strip("|").split("|")]
            if cells and all(not cell for cell in cells):
                return True
            non_empty = [cell for cell in cells if cell]
            if non_empty and all(cell in generic_table_headers for cell in non_empty):
                return True

        return False

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
        real_content = [line for line in content_lines if not _is_placeholder_line(line)]

        if not real_content:
            findings.append(
                {
                    "severity": TIER_1,
                    "rule": "plan-section-placeholder",
                    "message": f"Section '{heading}' in {plan_path.name} contains only placeholder text — fill it with actual design decisions.",
                }
            )

    return findings
