"""Spring Modulith adapter (JSON report stub)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List


def _parse_report(raw_text: str) -> List[Dict[str, Any]]:
    payload = json.loads(raw_text)
    items: List[Any]
    if isinstance(payload, dict) and isinstance(payload.get("violations"), list):
        items = payload["violations"]
    elif isinstance(payload, list):
        items = payload
    else:
        raise ValueError("Modulith report must be a list or an object with a 'violations' list.")

    findings: List[Dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        findings.append(
            {
                "rule_id": str(item.get("rule") or item.get("rule_id") or "modulith-violation").strip(),
                "severity": str(item.get("severity") or "error").strip().lower(),
                "message": str(item.get("message") or "Modulith architecture violation.").strip(),
                "file": str(item.get("file")).strip() if item.get("file") else None,
                "line": int(item["line"]) if isinstance(item.get("line"), int) else None,
                "column": int(item["column"]) if isinstance(item.get("column"), int) else None,
            }
        )
    return findings


def run(workspace: Path, config: Dict[str, Any]) -> Dict[str, Any]:
    modulith_cfg = config.get("modulith") if isinstance(config.get("modulith"), dict) else {}
    try:
        timeout_s = max(1, int(config.get("timeout_s", 120)))
    except (TypeError, ValueError):
        timeout_s = 120
    command = modulith_cfg.get("command") if isinstance(modulith_cfg.get("command"), list) else []
    report_file = str(modulith_cfg.get("report_file", "")).strip()
    if not report_file:
        return {
            "tool": "modulith",
            "violations": [],
            "exit_code": 0,
            "error": "Modulith adapter requires 'modulith.report_file'.",
        }

    exit_code = 0
    stdout = ""
    stderr = ""
    if command:
        command_list = [str(part) for part in command if str(part).strip()]
        try:
            result = subprocess.run(
                command_list,
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
                "tool": "modulith",
                "command": command_list,
                "violations": [],
                "exit_code": 127,
                "error": f"Modulith command binary not found: {exc}",
            }
        except subprocess.TimeoutExpired:
            return {
                "tool": "modulith",
                "command": command_list,
                "violations": [],
                "exit_code": 124,
                "error": f"Modulith command timed out after {timeout_s}s.",
            }

    report_path = workspace / report_file
    if not report_path.exists():
        return {
            "tool": "modulith",
            "violations": [],
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "error": f"Modulith report file not found: {report_file}",
        }

    parse_error: str | None = None
    findings: List[Dict[str, Any]] = []
    try:
        findings = _parse_report(report_path.read_text(encoding="utf-8", errors="ignore"))
    except Exception as exc:  # noqa: BLE001
        parse_error = str(exc)

    return {
        "tool": "modulith",
        "command": [str(part) for part in command] if command else [],
        "violations": findings,
        "parse_error": parse_error,
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
    }
