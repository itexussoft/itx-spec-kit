#!/usr/bin/env python3
"""Runtime gate flow for the Itexus gates orchestrator."""

from __future__ import annotations

import importlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, cast

from orchestrator_brief import _generate_execution_brief, _sync_lazy_knowledge
from orchestrator_common import (
    DOMAIN_VALIDATORS,
    RULE_DEFAULT_META,
    RULE_REMEDIATION_HINTS,
    TIER_1,
    TIER_2,
    Finding,
    _parse_bool,
    _parse_retry_limit,
    _retry_key,
    _task_files_for_review_scope,
    _tasks_required_for_workspace,
    _validate_plan_content,
    _validate_tasks_checkbox_format,
    check_e2e_test_presence,
    ensure_feedback_path,
    load_config,
    load_policy,
    parse_args,
    read_tier1_retry_state,
    run_docker_exec,
    write_gate_feedback,
    _find_plan_files,
    _find_task_files,
)


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
                    "message": "No tasks file found after task generation stage. Expected tasks.md under specs/** or legacy fallback locations.",
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
                    "message": f"Found {unchecked_count} unchecked task checkbox item(s). All tasks must be completed before delivery.",
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
    tier_severity = cast(type(TIER_1), severity)
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
        return [{"severity": TIER_2, "rule": "validator-execution-failed", "message": f"Validator '{module_path}' failed: {exc}"}]
    if not isinstance(raw_findings, list):
        return [{"severity": TIER_2, "rule": "validator-invalid-output", "message": f"Validator '{module_path}' returned non-list output."}]
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
    configured_retry_limit = (config.get("gate") or {}).get("max_tier1_retries", default_retry_limit)
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
                        "message": f"{finding.get('message', 'Tier 1 finding retried too many times.')} (retry {retry_count}/{tier1_retry_limit})",
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
        except Exception as exc:  # noqa: BLE001
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
