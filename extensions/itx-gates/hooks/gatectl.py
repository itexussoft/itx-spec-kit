#!/usr/bin/env python3
"""Manual/hybrid host helper for ensuring itx-gates have run recently."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

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
        if json_mode:
            try:
                payload = json.loads(result.stdout or "{}")
            except json.JSONDecodeError:
                payload = {}
            if isinstance(payload, dict):
                payload["action"] = "executed"
                payload["fresh_before_run"] = fresh
                payload["freshness_reason"] = freshness_reason
                sys.stdout.write(json.dumps(payload, indent=2) + "\n")
                if result.stderr:
                    sys.stderr.write(result.stderr)
                return result.returncode
        if not json_mode:
            _print_passthrough(result)
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
