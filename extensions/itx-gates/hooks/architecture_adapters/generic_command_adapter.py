"""Generic command adapter for architecture tools."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from architecture_parsers.jsonpath import resolve_all, resolve_first
from architecture_parsers.junit_xml import parse_junit_xml_text
from architecture_parsers.sarif import parse_sarif_text


def _normalize_command(command: Any) -> List[str]:
    if isinstance(command, list):
        return [str(part) for part in command if str(part).strip()]
    if isinstance(command, str) and command.strip():
        return [command.strip()]
    return []


def _parse_custom_json(raw_text: str, parse_cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    payload = json.loads(raw_text)
    iterate_expr = str(parse_cfg.get("iterate", "$[*]")).strip() or "$[*]"
    mapping = parse_cfg.get("map") if isinstance(parse_cfg.get("map"), dict) else {}
    items = resolve_all(payload, iterate_expr)
    findings: List[Dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        rule_expr = str(mapping.get("rule_id", "rule_id"))
        sev_expr = str(mapping.get("severity", "severity"))
        file_expr = str(mapping.get("file", "file"))
        msg_expr = str(mapping.get("message", "message"))
        line_expr = str(mapping.get("line", "line"))

        rule_id = resolve_first(item, rule_expr)
        severity = resolve_first(item, sev_expr)
        file_path = resolve_first(item, file_expr)
        message = resolve_first(item, msg_expr)
        line = resolve_first(item, line_expr)
        line_int = int(line) if isinstance(line, int) or (isinstance(line, str) and line.isdigit()) else None
        findings.append(
            {
                "rule_id": str(rule_id).strip() if rule_id is not None else "json-violation",
                "severity": str(severity).strip().lower() if severity is not None else "warning",
                "file": str(file_path).strip() if file_path is not None else None,
                "message": str(message).strip() if message is not None else "Architecture violation.",
                "line": line_int,
                "column": None,
            }
        )
    return findings


def _detect_format(parse_cfg: Dict[str, Any], raw_text: str) -> str:
    explicit = str(parse_cfg.get("format", "")).strip().lower()
    if explicit:
        return explicit
    stripped = raw_text.lstrip()
    if stripped.startswith("{") and '"version"' in stripped and '"runs"' in stripped:
        return "sarif"
    if stripped.startswith("<"):
        return "junit_xml"
    return "json"


def _parse_output(raw_text: str, parse_cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    fmt = _detect_format(parse_cfg, raw_text)
    if fmt == "sarif":
        return parse_sarif_text(raw_text)
    if fmt in {"junit", "junit_xml"}:
        return parse_junit_xml_text(raw_text)
    if fmt == "json":
        return _parse_custom_json(raw_text, parse_cfg)
    raise ValueError(f"Unsupported parse format '{fmt}'.")


def run(workspace: Path, config: Dict[str, Any]) -> Dict[str, Any]:
    command = _normalize_command(config.get("command"))
    parse_cfg = config.get("parse") if isinstance(config.get("parse"), dict) else {}
    try:
        timeout_s = max(1, int(config.get("timeout_s", 120)))
    except (TypeError, ValueError):
        timeout_s = 120
    if not command:
        return {
            "tool": "generic",
            "violations": [],
            "exit_code": 0,
            "error": "Generic architecture runner requires a non-empty 'command' list.",
        }

    try:
        result = subprocess.run(
            command,
            cwd=str(workspace),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except FileNotFoundError as exc:
        return {
            "tool": "generic",
            "command": command,
            "violations": [],
            "exit_code": 127,
            "error": f"Command binary not found: {exc}",
        }
    except subprocess.TimeoutExpired:
        return {
            "tool": "generic",
            "command": command,
            "violations": [],
            "exit_code": 124,
            "error": f"Command timed out after {timeout_s}s.",
        }

    source_text = result.stdout or ""
    report_file = config.get("report_file")
    if isinstance(report_file, str) and report_file.strip():
        candidate = workspace / report_file
        if candidate.exists():
            source_text = candidate.read_text(encoding="utf-8", errors="ignore")

    parsed: List[Dict[str, Any]] = []
    parse_error: str | None = None
    if source_text.strip():
        try:
            parsed = _parse_output(source_text, parse_cfg)
        except Exception as exc:  # noqa: BLE001
            parse_error = str(exc)

    return {
        "tool": "generic",
        "command": command,
        "violations": parsed,
        "parse_error": parse_error,
        "exit_code": result.returncode,
        "stdout": result.stdout or "",
        "stderr": result.stderr or "",
    }
