"""Healthcare domain validators."""

from __future__ import annotations

import re
from pathlib import Path
from typing import List

from validators import Finding, collect_code_files


def run(workspace: Path) -> List[Finding]:
    """Tier 1 regex scan for potential PHI in logs."""
    findings: List[Finding] = []
    log_stmt = re.compile(r"(logger\.(info|debug|warning|error)|console\.log)\s*\((.*?)\)", re.IGNORECASE)
    phi_tokens = {
        "email",
        "ssn",
        "dob",
        "phone",
        "patient_name",
        "legal_name",
        "first_name",
        "last_name",
        "full_name",
        "mrn",
        "medical_record",
        "diagnosis",
        "address",
    }
    safe_markers = {"masked", "redacted", "hash", "hashed", "tokenized"}
    identifier_re = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

    code_files = collect_code_files(workspace, [".py", ".ts", ".js"], skip_test_like=True)
    for file_path in code_files:
        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            findings.append(
                {
                    "severity": "tier1",
                    "rule": "validator-file-read-failed",
                    "message": f"{file_path}: failed to read file during healthcare validation ({exc}).",
                    "confidence": "heuristic",
                    "remediation_owner": "security-team",
                }
            )
            continue
        for match in log_stmt.finditer(text):
            payload = match.group(3)
            tokens = {token.lower() for token in identifier_re.findall(payload)}
            if tokens.intersection(safe_markers):
                continue
            if tokens.intersection(phi_tokens):
                findings.append(
                    {
                        "severity": "tier1",
                        "rule": "healthcare-phi-logging",
                        "message": (
                            f"{file_path}: possible PHI in logging statement. "
                            "Read .specify/anti-patterns/logging-phi-data.md for required controls."
                        ),
                        "confidence": "heuristic",
                        "remediation_owner": "security-team",
                    }
                )
    return findings
