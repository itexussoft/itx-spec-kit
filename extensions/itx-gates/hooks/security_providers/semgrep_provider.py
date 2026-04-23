"""Semgrep security provider."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

from validators import Finding


DEFAULT_RULESET_PATH = Path(__file__).resolve().parents[1] / "security_rules" / "semgrep" / "fintech-banking.yml"


def _tier_for_severity(severity: str) -> str:
    normalized = severity.strip().upper()
    if normalized in {"ERROR", "HIGH"}:
        return "tier2"
    return "tier1"


def _resolve_ruleset(settings: Dict[str, Any]) -> Path:
    configured = str(settings.get("semgrep_rules", "")).strip()
    if not configured:
        return DEFAULT_RULESET_PATH
    candidate = Path(configured)
    if candidate.is_absolute():
        return candidate
    return Path(__file__).resolve().parents[1] / configured


def run(workspace: Path, settings: Dict[str, Any]) -> List[Finding]:
    if shutil.which("semgrep") is None:
        if bool(settings.get("compat_heuristic_fallback", False)):
            sys.stderr.write("[itx-gates] Warning: Semgrep unavailable; using compatibility heuristic fallback.\n")
            return []
        mode = str(settings.get("on_missing_binary", "warn")).strip().lower()
        if mode == "warn":
            return [
                {
                    "severity": "tier1",
                    "rule": "sast-provider-unavailable",
                    "message": "Semgrep binary not found; deterministic SAST scan skipped.",
                    "confidence": "heuristic",
                    "remediation_owner": "security-team",
                }
            ]
        return [
            {
                "severity": "tier2",
                "rule": "sast-provider-unavailable",
                "message": "Semgrep binary not found and strict mode is enabled.",
                "confidence": "deterministic",
                "remediation_owner": "security-team",
            }
        ]

    ruleset = _resolve_ruleset(settings)
    if not ruleset.exists():
        return [
            {
                "severity": "tier1",
                "rule": "sast-ruleset-missing",
                "message": f"Semgrep ruleset not found: {ruleset}",
                "confidence": "heuristic",
                "remediation_owner": "security-team",
            }
        ]

    cmd = [
        "semgrep",
        "--config",
        str(ruleset),
        "--json",
        "--quiet",
        str(workspace),
    ]
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if result.returncode not in {0, 1}:
        return [
            {
                "severity": "tier1",
                "rule": "sast-provider-failed",
                "message": (result.stderr or result.stdout or "Semgrep execution failed.").strip(),
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
                "message": "Semgrep returned malformed JSON output.",
                "confidence": "heuristic",
                "remediation_owner": "security-team",
            }
        ]

    findings: List[Finding] = []
    for raw in payload.get("results", []):
        if not isinstance(raw, dict):
            continue
        rule_id = str(raw.get("check_id", "semgrep-finding")).strip() or "semgrep-finding"
        path = str(raw.get("path", "")).strip()
        start = raw.get("start")
        line: str = ""
        if isinstance(start, dict) and isinstance(start.get("line"), int):
            line = f":{start['line']}"
        extra = raw.get("extra") if isinstance(raw.get("extra"), dict) else {}
        message = str(extra.get("message", "")).strip() or f"Semgrep finding ({rule_id})."
        tier = _tier_for_severity(str(extra.get("severity", "")))
        location = f"{path}{line}" if path else "workspace"
        findings.append(
            {
                "severity": tier,
                "rule": rule_id,
                "message": f"{location}: {message}",
                "confidence": "deterministic",
                "remediation_owner": "security-team",
            }
        )
    return findings
