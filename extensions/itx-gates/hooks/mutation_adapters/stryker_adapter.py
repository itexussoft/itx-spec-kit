"""Stryker mutation adapter."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List


def _command(settings: Dict[str, Any]) -> List[str]:
    explicit = settings.get("command")
    if isinstance(explicit, list) and explicit:
        return [str(part) for part in explicit if str(part).strip()]
    return []


def run(workspace: Path, config: Dict[str, Any]) -> Dict[str, Any]:
    settings = config.get("stryker") if isinstance(config.get("stryker"), dict) else {}
    report_file = str(settings.get("report_file", "reports/mutation/mutation.json")).strip() or "reports/mutation/mutation.json"
    try:
        timeout_s = max(1, int(config.get("timeout_s", 120)))
    except (TypeError, ValueError):
        timeout_s = 120
    command = _command(settings)
    exit_code = 0
    stdout = ""
    stderr = ""

    if command:
        try:
            result = subprocess.run(
                command,
                cwd=str(workspace),
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
            exit_code = result.returncode
            stdout = result.stdout or ""
            stderr = result.stderr or ""
        except FileNotFoundError as exc:
            return {
                "tool": "stryker",
                "command": command,
                "report": {},
                "exit_code": 127,
                "error": f"Stryker command binary not found: {exc}",
            }
        except subprocess.TimeoutExpired:
            return {
                "tool": "stryker",
                "command": command,
                "report": {},
                "exit_code": 124,
                "error": f"Stryker command timed out after {timeout_s}s.",
            }

    report_path = workspace / report_file
    if not report_path.exists():
        return {
            "tool": "stryker",
            "command": command,
            "report": {},
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "error": f"Stryker report file not found: {report_file}",
        }

    parse_error: str | None = None
    report_payload: Dict[str, Any] = {}
    try:
        decoded = json.loads(report_path.read_text(encoding="utf-8", errors="ignore"))
        if isinstance(decoded, dict):
            report_payload = decoded
        elif isinstance(decoded, list):
            report_payload = {"schemaVersion": "1.0", "mutants": decoded}
        else:
            report_payload = {}
    except json.JSONDecodeError as exc:
        parse_error = str(exc)

    return {
        "tool": "stryker",
        "command": command,
        "report": report_payload,
        "parse_error": parse_error,
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
    }
