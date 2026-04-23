"""Procurement guarantees domain validators — heuristic lifecycle and evidence checks."""

from __future__ import annotations

import re
from pathlib import Path
from typing import List

from validators import Finding, collect_code_files

_DOMAIN_SIGNAL_RE = re.compile(
    r"\b("
    r"applicationbanktrack|track_status|flowversion|scoringrulesetversion|"
    r"documents_requested|final_docs|issued|rejected_by_bank|track_mode|"
    r"track_field_snapshot|track_document_snapshot|snapshot|document_version|status_history|fallback|"
    r"principal|broker|bank|operator|orgreference|org_ref_id|"
    r"webhook|partner|etp|ukep|api_error|independent guarantee|bank guarantee"
    r")\b",
    re.IGNORECASE,
)

_STATUS_MUTATION_RE = re.compile(
    r"(\b(?:application_status|track_status)\b\s*=\s*['\"A-Z_]|"
    r"\.\s*(?:application_status|track_status)\s*=\s*['\"A-Z_]|"
    r"\bset(?:Application|Track)?Status\s*\()",
    re.IGNORECASE,
)

_FALLBACK_RE = re.compile(
    r"(fallback.*manual|manual.*fallback|switch(?:ed)?_to_manual|mode\s*=\s*['\"]MANUAL['\"]|track_mode\s*=\s*['\"]MANUAL['\"])",
    re.IGNORECASE,
)
_API_ERROR_RE = re.compile(
    r"(\b(api|integration|webhook|delivery|partner).*(error|fail|except|timeout|retry)\b|\bapi[_ ]error\b)",
    re.IGNORECASE,
)

_HISTORY_DELETE_RE = re.compile(
    r"(delete\s+from\s+(?:track_)?(?:field_)?snapshot|"
    r"delete\s+from\s+.*document_version|"
    r"delete\s+from\s+.*status_history|"
    r"\.(?:delete|remove)\s*\(.*(?:snapshot|history|documentversion|trackdocumentsnapshot|trackfieldsnapshot)|"
    r"update\s+.*document_version\s+set\s+)",
    re.IGNORECASE,
)

_PARTNER_ENDPOINT_RE = re.compile(
    r"(@router\.(post|put|patch)|@app\.route\s*\(.*(post|put|patch)|"
    r"/webhook|/partner|broker-gateway|etp)",
    re.IGNORECASE,
)
_PARTNER_AUTH_MARKER_RE = re.compile(r"(hmac|x-api-key|api[-_ ]key|authorization|bot-user)", re.IGNORECASE)
_PARTNER_REPLAY_MARKER_RE = re.compile(r"(nonce|timestamp|replay|idempotency)", re.IGNORECASE)

_ORG_ACCESS_SIGNAL_RE = re.compile(
    r"\b(application|document|notification|track|comment|message)\b",
    re.IGNORECASE,
)
_ROLE_SIGNAL_RE = re.compile(r"\b(principal|broker|bank|operator)\b", re.IGNORECASE)
_ORG_SCOPE_MARKER_RE = re.compile(r"(orgreference|org_ref_id|tenant_id|rls|scope|visibility|current_organization)", re.IGNORECASE)


def run(workspace: Path) -> List[Finding]:
    """Heuristic checks for obvious procurement-guarantee architecture drift."""
    findings: List[Finding] = []
    code_files = collect_code_files(workspace, [".py", ".ts", ".js", ".sql"], skip_test_like=True)

    for file_path in code_files:
        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            findings.append(
                {
                    "severity": "tier1",
                    "rule": "validator-file-read-failed",
                    "message": f"{file_path}: failed to read file during procurement guarantees validation ({exc}).",
                    "confidence": "heuristic",
                    "remediation_owner": "domain-team",
                }
            )
            continue

        if not _DOMAIN_SIGNAL_RE.search(text):
            continue

        if _STATUS_MUTATION_RE.search(text):
            findings.append(
                {
                    "severity": "tier2",
                    "rule": "procurement-status-transition-bypass",
                    "message": (
                        f"{file_path}: detected direct application/track status mutation. "
                        "Use explicit transition guards and append-only history."
                    ),
                    "confidence": "deterministic",
                    "remediation_owner": "domain-team",
                }
            )

        if _FALLBACK_RE.search(text) and _API_ERROR_RE.search(text):
            findings.append(
                {
                    "severity": "tier2",
                    "rule": "procurement-silent-api-manual-fallback",
                    "message": (
                        f"{file_path}: possible hidden API-to-MANUAL fallback detected. "
                        "Keep delivery-mode changes explicit and auditable."
                    ),
                    "confidence": "heuristic",
                    "remediation_owner": "domain-team",
                }
            )

        if _HISTORY_DELETE_RE.search(text):
            findings.append(
                {
                    "severity": "tier2",
                    "rule": "procurement-history-delete",
                    "message": (
                        f"{file_path}: append-only history or snapshot evidence appears to be deleted or overwritten."
                    ),
                    "confidence": "deterministic",
                    "remediation_owner": "domain-team",
                }
            )

        if _PARTNER_ENDPOINT_RE.search(text):
            if not _PARTNER_AUTH_MARKER_RE.search(text):
                findings.append(
                    {
                        "severity": "tier1",
                        "rule": "procurement-partner-auth-missing",
                        "message": (
                            f"{file_path}: partner/webhook endpoint appears to lack explicit API-key or HMAC markers."
                        ),
                        "confidence": "heuristic",
                        "remediation_owner": "security-team",
                    }
                )
            if not _PARTNER_REPLAY_MARKER_RE.search(text):
                findings.append(
                    {
                        "severity": "tier1",
                        "rule": "procurement-partner-replay-protection-missing",
                        "message": (
                            f"{file_path}: partner/webhook endpoint appears to miss replay/idempotency markers."
                        ),
                        "confidence": "heuristic",
                        "remediation_owner": "security-team",
                    }
                )

        if _ORG_ACCESS_SIGNAL_RE.search(text) and _ROLE_SIGNAL_RE.search(text) and not _ORG_SCOPE_MARKER_RE.search(text):
            findings.append(
                {
                    "severity": "tier1",
                    "rule": "procurement-org-scope-marker-missing",
                    "message": (
                        f"{file_path}: role-scoped application or document access appears to miss explicit org-scope markers."
                    ),
                    "confidence": "heuristic",
                    "remediation_owner": "domain-team",
                }
            )

    return findings
