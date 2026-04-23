#!/usr/bin/env python3
"""Manual/hybrid host helper for ensuring itx-gates have run recently."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from orchestrator_common import evaluate_gate_freshness, last_gate_summary_path, load_config, load_gate_state, load_policy


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ensure an itx-gates lifecycle event is fresh for the current workspace")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ensure = subparsers.add_parser("ensure", help="Ensure a lifecycle gate has executed and is fresh")
    ensure.add_argument("--event", required=True, help="Lifecycle event (for example after_plan)")
    ensure.add_argument("--workspace", required=True, help="Target workspace root")
    ensure.add_argument("--json", action="store_true", help="Emit machine-readable JSON result")
    ensure.add_argument("--force", action="store_true", help="Force rerun even when a fresh gate state exists")

    return parser.parse_args(argv)


def _run_orchestrator(workspace: Path, event: str, json_mode: bool) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(Path(__file__).resolve().parent / "orchestrator.py"), "--event", event, "--workspace", str(workspace)]
    if json_mode:
        cmd.append("--json")
    return subprocess.run(cmd, check=False, capture_output=True, text=True)


def _print_passthrough(result: subprocess.CompletedProcess[str]) -> None:
    if result.stdout:
        sys.stdout.write(result.stdout)
    if result.stderr:
        sys.stderr.write(result.stderr)


def _context_dir(workspace: Path) -> Path:
    root = workspace / ".specify" / "context"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _gate_failure_report_path(workspace: Path) -> Path:
    return _context_dir(workspace) / "gate-failure-report.md"


def _auto_retry_state_path(workspace: Path) -> Path:
    return _context_dir(workspace) / "auto-retry-state.yml"


def _audit_log_path(workspace: Path) -> Path:
    return _context_dir(workspace) / "audit-log.md"


def _load_yaml_mapping(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return {}
    return data if isinstance(data, dict) else {}


def _parse_positive_int(raw: object, default: int) -> int:
    try:
        parsed = int(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 0 else default


def _resolve_auto_retry_limit(workspace: Path, config: dict, policy: dict) -> int:
    default_limit = 3
    input_contracts = _load_yaml_mapping(workspace / ".specify" / "input-contracts.yml")
    contracts_gate = input_contracts.get("gate") if isinstance(input_contracts.get("gate"), dict) else {}
    contracts_retry = contracts_gate.get("auto_retry") if isinstance(contracts_gate, dict) else {}
    if isinstance(contracts_retry, dict):
        default_limit = _parse_positive_int(contracts_retry.get("max_attempts", default_limit), default_limit)

    policy_gate = policy.get("gate") if isinstance(policy.get("gate"), dict) else {}
    policy_retry = policy_gate.get("auto_retry") if isinstance(policy_gate, dict) else {}
    if isinstance(policy_retry, dict):
        default_limit = _parse_positive_int(policy_retry.get("max_attempts", default_limit), default_limit)

    config_gate = config.get("gate") if isinstance(config.get("gate"), dict) else {}
    config_retry = config_gate.get("auto_retry") if isinstance(config_gate, dict) else {}
    if isinstance(config_retry, dict):
        return _parse_positive_int(config_retry.get("max_attempts", default_limit), default_limit)
    return default_limit


def _load_auto_retry_state(workspace: Path) -> dict[str, int]:
    raw = _load_yaml_mapping(_auto_retry_state_path(workspace))
    retries = raw.get("attempts")
    if not isinstance(retries, dict):
        return {}
    state: dict[str, int] = {}
    for key, value in retries.items():
        if isinstance(key, str):
            state[key] = _parse_positive_int(value, 0)
    return state


def _write_auto_retry_state(workspace: Path, attempts: dict[str, int]) -> None:
    payload = {"schema_version": "1.0", "attempts": attempts}
    _auto_retry_state_path(workspace).write_text(
        yaml.safe_dump(payload, sort_keys=True, allow_unicode=False),
        encoding="utf-8",
    )


def _summarize_feedback(gate_feedback_text: str) -> list[str]:
    summary: list[str] = []
    for block in gate_feedback_text.split("## Finding ")[1:]:
        rule_match = re.search(r"- Rule:\s+`([^`]+)`", block)
        message_match = re.search(r"- Message:\s+(.+)", block)
        if not rule_match or not message_match:
            continue
        summary.append(f"- {rule_match.group(1)}: {message_match.group(1).strip()}")
        if len(summary) >= 8:
            break
    return summary


def _write_gate_failure_report(
    *,
    workspace: Path,
    event: str,
    attempt_count: int,
    max_attempts: int,
    retry_requested: bool,
    orchestrator_stdout: str,
    orchestrator_stderr: str,
) -> Path:
    feedback_path = workspace / ".specify" / "context" / "gate_feedback.md"
    gate_feedback_text = feedback_path.read_text(encoding="utf-8", errors="ignore") if feedback_path.exists() else ""
    finding_lines = _summarize_feedback(gate_feedback_text) or ["- No structured findings were parsed from gate_feedback.md."]
    status = "retry_requested" if retry_requested else "human_escalation_required"
    rerun_cmd = f"python extensions/itx-gates/hooks/gatectl.py ensure --event {event} --workspace ."
    report_text = "\n".join(
        [
            "---",
            'schema_version: "1.0"',
            f'event: "{event}"',
            f"attempt_count: {attempt_count}",
            f"max_attempts: {max_attempts}",
            f'status: "{status}"',
            f'generated_at: "{datetime.now(timezone.utc).replace(microsecond=0).isoformat()}"',
            "---",
            "",
            "# Gate Failure Report",
            "",
            "## Findings Snapshot",
            *finding_lines,
            "",
            "## Diagnostics",
            "```text",
            (orchestrator_stdout or "").strip()[:4000],
            (orchestrator_stderr or "").strip()[:4000],
            "```",
            "",
            "## <SYSTEM_CORRECTION>",
            "Resolve all Tier 1 findings listed above, then rerun the gate command.",
            f"Retry budget status: attempt {attempt_count} of {max_attempts}.",
            "</SYSTEM_CORRECTION>",
            "",
            "## Rerun Command",
            f"`{rerun_cmd}`",
            "",
        ]
    )
    report_path = _gate_failure_report_path(workspace)
    report_path.write_text(report_text, encoding="utf-8")
    return report_path


def _append_auto_retry_audit(
    *,
    workspace: Path,
    event: str,
    attempt_count: int,
    max_attempts: int,
    retry_requested: bool,
    report_path: Path,
) -> None:
    audit_path = _audit_log_path(workspace)
    action = "retry" if retry_requested else "escalate"
    lines = [
        f"## Gate Auto-Retry ({datetime.now(timezone.utc).replace(microsecond=0).isoformat()})",
        f"- Event: `{event}`",
        f"- Action: `{action}`",
        f"- Attempt: `{attempt_count}/{max_attempts}`",
        f"- Report: `{report_path.relative_to(workspace)}`",
        "",
    ]
    with audit_path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def _status_from_result(workspace: Path, result: subprocess.CompletedProcess[str]) -> str:
    try:
        payload = json.loads(result.stdout or "{}")
        if isinstance(payload, dict):
            status = str(payload.get("status", "")).strip()
            if status:
                return status
    except json.JSONDecodeError:
        pass
    state = load_gate_state(workspace) or {}
    return str(state.get("status", "")).strip()


def ensure_gate(event: str, workspace: Path, *, json_mode: bool, force: bool) -> int:
    config = load_config(workspace)
    policy = load_policy(workspace)
    hook_mode = str(config.get("hook_mode", "hybrid")).strip() or "hybrid"
    fresh, freshness_reason = evaluate_gate_freshness(workspace, event, policy)

    should_execute = force or not fresh or hook_mode in {"manual", "hybrid"}
    if should_execute and not force and hook_mode in {"manual", "hybrid"} and fresh:
        # Fresh state exists, so preserve the last successful result instead of rerunning needlessly.
        should_execute = False

    if should_execute:
        result = _run_orchestrator(workspace, event, json_mode=json_mode)
        status = _status_from_result(workspace, result)
        auto_retry_payload: dict[str, object] = {}
        if event == "after_implement" and status == "tier1":
            max_attempts = _resolve_auto_retry_limit(workspace, config, policy)
            attempt_state = _load_auto_retry_state(workspace)
            attempt_count = attempt_state.get(event, 0) + 1
            attempt_state[event] = attempt_count
            _write_auto_retry_state(workspace, attempt_state)

            retry_requested = attempt_count <= max_attempts
            report_path = _write_gate_failure_report(
                workspace=workspace,
                event=event,
                attempt_count=attempt_count,
                max_attempts=max_attempts,
                retry_requested=retry_requested,
                orchestrator_stdout=result.stdout,
                orchestrator_stderr=result.stderr,
            )
            _append_auto_retry_audit(
                workspace=workspace,
                event=event,
                attempt_count=attempt_count,
                max_attempts=max_attempts,
                retry_requested=retry_requested,
                report_path=report_path,
            )
            auto_retry_payload = {
                "retry_requested": retry_requested,
                "auto_retry_attempt": attempt_count,
                "auto_retry_max_attempts": max_attempts,
                "auto_retry_remaining_attempts": max(0, max_attempts - attempt_count),
                "human_action_required": not retry_requested,
                "gate_failure_report_path": str(report_path.relative_to(workspace)),
            }
        elif status in {"passed", "tier2"}:
            attempt_state = _load_auto_retry_state(workspace)
            if event in attempt_state:
                attempt_state.pop(event, None)
                _write_auto_retry_state(workspace, attempt_state)

        if json_mode:
            try:
                payload = json.loads(result.stdout or "{}")
            except json.JSONDecodeError:
                payload = {}
            if isinstance(payload, dict):
                payload["action"] = "executed"
                payload["fresh_before_run"] = fresh
                payload["freshness_reason"] = freshness_reason
                payload.update(auto_retry_payload)
                sys.stdout.write(json.dumps(payload, indent=2) + "\n")
                if result.stderr:
                    sys.stderr.write(result.stderr)
                return result.returncode
        if not json_mode:
            _print_passthrough(result)
            if auto_retry_payload:
                if auto_retry_payload.get("retry_requested"):
                    sys.stdout.write(
                        "[itx-gates] Auto-retry requested. See .specify/context/gate-failure-report.md for <SYSTEM_CORRECTION> context.\n"
                    )
                elif auto_retry_payload.get("human_action_required"):
                    sys.stdout.write(
                        "[itx-gates] Auto-retry budget exhausted. Human escalation is required; see .specify/context/gate-failure-report.md.\n"
                    )
        return result.returncode

    gate_state = load_gate_state(workspace) or {}
    payload = {
        "event": event,
        "status": str(gate_state.get("status", "unknown")),
        "exit_code": int(gate_state.get("exit_code", 0)) if isinstance(gate_state.get("exit_code"), int) else 0,
        "hook_mode": hook_mode,
        "fresh": fresh,
        "freshness_reason": freshness_reason,
        "action": "skipped-fresh",
        "gate_state_path": str((workspace / ".specify" / "context" / "gate-state.yml").relative_to(workspace)),
        "last_gate_summary_path": str(last_gate_summary_path(workspace).relative_to(workspace)),
    }
    if json_mode:
        sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    else:
        sys.stdout.write(f"[itx-gates] {event} already fresh ({hook_mode}); skipping rerun.\n")
    return int(payload["exit_code"])


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    workspace = Path(args.workspace).resolve()
    if args.command == "ensure":
        return ensure_gate(args.event.strip(), workspace, json_mode=args.json, force=args.force)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
