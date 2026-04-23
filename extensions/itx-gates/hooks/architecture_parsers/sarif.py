"""Minimal SARIF 2.1.0 parser for architecture findings."""

from __future__ import annotations

import json
from typing import Any, Dict, List


def _message_text(result: Dict[str, Any]) -> str:
    message = result.get("message")
    if isinstance(message, dict):
        text = message.get("text")
        if isinstance(text, str) and text.strip():
            return text.strip()
        markdown = message.get("markdown")
        if isinstance(markdown, str) and markdown.strip():
            return markdown.strip()
    return "Architecture rule violation."


def _primary_location(result: Dict[str, Any]) -> tuple[str | None, int | None, int | None]:
    locations = result.get("locations")
    if not isinstance(locations, list) or not locations:
        return None, None, None
    first = locations[0] if isinstance(locations[0], dict) else {}
    physical = first.get("physicalLocation") if isinstance(first, dict) else {}
    artifact = physical.get("artifactLocation") if isinstance(physical, dict) else {}
    uri = artifact.get("uri") if isinstance(artifact, dict) else None
    region = physical.get("region") if isinstance(physical, dict) else {}
    start_line = region.get("startLine") if isinstance(region, dict) else None
    start_col = region.get("startColumn") if isinstance(region, dict) else None
    file_path = str(uri).strip() if isinstance(uri, str) and uri.strip() else None
    line = int(start_line) if isinstance(start_line, int) and start_line > 0 else None
    col = int(start_col) if isinstance(start_col, int) and start_col > 0 else None
    return file_path, line, col


def parse_sarif_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    version = payload.get("version")
    if version != "2.1.0":
        raise ValueError(f"Unsupported SARIF version '{version}'. Expected '2.1.0'.")
    runs = payload.get("runs")
    if not isinstance(runs, list):
        raise ValueError("SARIF payload is missing a valid 'runs' array.")

    findings: List[Dict[str, Any]] = []
    for run in runs:
        if not isinstance(run, dict):
            continue
        results = run.get("results")
        if not isinstance(results, list):
            continue
        for result in results:
            if not isinstance(result, dict):
                continue
            rule_id = str(result.get("ruleId", "")).strip() or "sarif-violation"
            level = str(result.get("level", "")).strip().lower() or "warning"
            message = _message_text(result)
            file_path, line, col = _primary_location(result)
            findings.append(
                {
                    "rule_id": rule_id,
                    "severity": level,
                    "message": message,
                    "file": file_path,
                    "line": line,
                    "column": col,
                }
            )
    return findings


def parse_sarif_text(raw_text: str) -> List[Dict[str, Any]]:
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid SARIF JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("SARIF payload must be a JSON object.")
    return parse_sarif_payload(payload)

