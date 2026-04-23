"""cargo-mutants adapter."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List


def _status_from_outcome(outcome: str) -> str:
    normalized = outcome.strip().lower()
    if normalized in {"caught", "killed", "fail"}:
        return "Killed"
    if normalized in {"missed", "survived", "ok"}:
        return "Survived"
    if normalized in {"timeout", "timedout"}:
        return "Timeout"
    if normalized in {"uncovered", "nocoverage"}:
        return "NoCoverage"
    return "Unknown"


def _parse_outcomes(raw_text: str) -> Dict[str, Any]:
    decoded = json.loads(raw_text)
    items = decoded if isinstance(decoded, list) else decoded.get("outcomes", []) if isinstance(decoded, dict) else []
    mutants: List[Dict[str, Any]] = []
    if isinstance(items, list):
        for index, item in enumerate(items, start=1):
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or item.get("mutant_name") or f"mutant-{index}").strip()
            source = str(item.get("source") or item.get("file") or "").strip() or None
            line = item.get("line")
            line_int = int(line) if isinstance(line, int) else int(line) if isinstance(line, str) and line.isdigit() else None
            outcome = str(item.get("outcome") or item.get("status") or "Unknown")
            mutants.append(
                {
                    "id": str(item.get("id") or name or f"cargo-mutant-{index}"),
                    "mutatorName": str(item.get("mutator") or "cargo-mutants"),
                    "location": {"file": source, "line": line_int, "column": None},
                    "status": _status_from_outcome(outcome),
                    "replacement": str(item.get("diff") or item.get("replacement") or "").strip() or None,
                    "killedBy": [],
                    "coveredBy": [],
                    "duration": item.get("duration_ms"),
                }
            )
    return {"schemaVersion": "1.0", "mutants": mutants}


def run(workspace: Path, config: Dict[str, Any]) -> Dict[str, Any]:
    settings = config.get("cargo-mutants") if isinstance(config.get("cargo-mutants"), dict) else {}
    if not settings and isinstance(config.get("cargo_mutants"), dict):
        settings = config.get("cargo_mutants")
    command = settings.get("command") if isinstance(settings.get("command"), list) else []
    report_file = str(settings.get("report_file", "mutants.out/outcomes.json")).strip() or "mutants.out/outcomes.json"
    try:
        timeout_s = max(1, int(config.get("timeout_s", 120)))
    except (TypeError, ValueError):
        timeout_s = 120
    exit_code = 0
    stdout = ""
    stderr = ""
    cmd_list = [str(part) for part in command if str(part).strip()]
    if cmd_list:
        try:
            result = subprocess.run(
                cmd_list,
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
                "tool": "cargo-mutants",
                "command": cmd_list,
                "report": {},
                "exit_code": 127,
                "error": f"cargo-mutants command binary not found: {exc}",
            }
        except subprocess.TimeoutExpired:
            return {
                "tool": "cargo-mutants",
                "command": cmd_list,
                "report": {},
                "exit_code": 124,
                "error": f"cargo-mutants command timed out after {timeout_s}s.",
            }

    report_path = workspace / report_file
    if not report_path.exists():
        return {
            "tool": "cargo-mutants",
            "command": cmd_list,
            "report": {},
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "error": f"cargo-mutants report file not found: {report_file}",
        }

    parse_error: str | None = None
    report_payload: Dict[str, Any] = {}
    try:
        report_payload = _parse_outcomes(report_path.read_text(encoding="utf-8", errors="ignore"))
    except Exception as exc:  # noqa: BLE001
        parse_error = str(exc)

    return {
        "tool": "cargo-mutants",
        "command": cmd_list,
        "report": report_payload,
        "parse_error": parse_error,
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
    }
