"""Bandit security provider."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from validators import Finding


def _tier_for_severity(severity: str) -> str:
    normalized = severity.strip().upper()
    return "tier2" if normalized in {"HIGH"} else "tier1"


def run(workspace: Path, settings: Dict[str, Any]) -> List[Finding]:
    if shutil.which("bandit") is None:
        mode = str(settings.get("on_missing_binary", "warn")).strip().lower()
        if mode == "warn":
            return [
                {
                    "severity": "tier1",
                    "rule": "sast-provider-unavailable",
                    "message": "Bandit binary not found; skipping deterministic SAST scan.",
                    "confidence": "heuristic",
                    "remediation_owner": "security-team",
                }
            ]
        return [
            {
                "severity": "tier2",
                "rule": "sast-provider-unavailable",
                "message": "Bandit binary not found and strict mode is enabled.",
                "confidence": "deterministic",
                "remediation_owner": "security-team",
            }
        ]

    cmd = ["bandit", "-r", str(workspace), "-f", "json", "-q"]
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if result.returncode not in {0, 1}:
        return [
            {
                "severity": "tier1",
                "rule": "sast-provider-failed",
                "message": (result.stderr or result.stdout or "Bandit execution failed.").strip(),
                "confidence": "heuristic",
                "remediation_owner": "security-team",
            }
        ]
    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError:
        return [
            {
                "severity": "tier1",
                "rule": "sast-provider-output-invalid",
                "message": "Bandit returned malformed JSON output.",
                "confidence": "heuristic",
                "remediation_owner": "security-team",
            }
        ]

    findings: List[Finding] = []
    for issue in payload.get("results", []):
        if not isinstance(issue, dict):
            continue
        filename = str(issue.get("filename", "")).strip()
        line_number = issue.get("line_number")
        issue_text = str(issue.get("issue_text", "")).strip()
        test_id = str(issue.get("test_id", "bandit-finding")).strip() or "bandit-finding"
        severity = _tier_for_severity(str(issue.get("issue_severity", "")))
        if not issue_text:
            continue
        location = f"{filename}:{line_number}" if filename and isinstance(line_number, int) else filename or "workspace"
        findings.append(
            {
                "severity": severity,
                "rule": f"bandit-{test_id.lower()}",
                "message": f"{location}: {issue_text}",
                "confidence": "deterministic",
                "remediation_owner": "security-team",
            }
        )
    return findings

