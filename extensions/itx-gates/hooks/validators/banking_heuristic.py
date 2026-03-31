"""Banking domain validators based on deterministic heuristics.

Interim implementation -- Milestone 2 (docs/roadmap.md) will introduce a
pluggable LLM-judge adapter for semantic PCI/PSD2 validation. Until then,
these regex/heuristic checks cover the most common surface-level risks.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List

from validators import Finding, collect_code_files


TEST_FILE_RE = re.compile(r"(^test_.*\.py$|.*_test\.py$|.*\.spec\.(ts|js)$|.*\.test\.(ts|js)$)")
PAYMENT_KEYWORD_RE = re.compile(
    r"\b(payment\w*|transfer\w*|payout\w*|iban|card)\b",
    re.IGNORECASE,
)
FLOW_SIGNAL_RE = re.compile(r"(\bdef\s+\w+\b|\bclass\s+\w+\b|@app\.route|@router\.(get|post|put|patch|delete))")
PAYMENT_ENTRYPOINT_RE = re.compile(
    r"(@router\.(post|put|patch)|@app\.route\s*\(.*(post|put|patch)|\bdef\s+\w*(payment|transfer|payout)\w*\b)",
    re.IGNORECASE,
)
RAW_PAN_RE = re.compile(r"\b(cardpan|raw_card_number|full_pan)\b", re.IGNORECASE)
IDEMPOTENCY_MARKER_RE = re.compile(r"(idempotency[-_ ]?key|x-idempotency-key)", re.IGNORECASE)
BALANCE_MUTATION_RE = re.compile(
    r"(\bbalance\b\s*(\+=|-=)|\bbalance\b\s*=\s*\bbalance\b\s*[+\-])",
    re.IGNORECASE,
)


def run(workspace: Path) -> List[Finding]:
    """Heuristic checks for obvious PCI/PSD2 risks in payment-related code."""
    findings: List[Finding] = []
    code_files = collect_code_files(workspace, [".py", ".ts", ".js"], skip_test_like=True)
    for file_path in code_files:
        if TEST_FILE_RE.match(file_path.name):
            continue
        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            findings.append(
                {
                    "severity": "tier1",
                    "rule": "validator-file-read-failed",
                    "message": f"{file_path}: failed to read file during banking validation ({exc}).",
                    "confidence": "heuristic",
                    "remediation_owner": "domain-team",
                }
            )
            continue
        text_lower = text.lower()

        if RAW_PAN_RE.search(text):
            findings.append(
                {
                    "severity": "tier1",
                    "rule": "banking-pci-pan-storage",
                    "message": (
                        f"{file_path}: possible raw PAN storage pattern detected. "
                        "Read docs/knowledge-base/banking-constraints.md for required controls."
                    ),
                    "confidence": "heuristic",
                    "remediation_owner": "security-team",
                }
            )

        if BALANCE_MUTATION_RE.search(text):
            findings.append(
                {
                    "severity": "tier2",
                    "rule": "banking-ledger-inplace-mutation",
                    "message": (
                        f"{file_path}: detected in-place balance mutation pattern. "
                        "Use append-only ledger entries and derived balances."
                    ),
                    "confidence": "deterministic",
                    "remediation_owner": "domain-team",
                }
            )

        looks_like_payment_flow = bool(PAYMENT_KEYWORD_RE.search(text) and FLOW_SIGNAL_RE.search(text))
        payment_entrypoint = bool(PAYMENT_ENTRYPOINT_RE.search(text))
        has_sca = any(marker in text_lower for marker in ("sca", "strong customer authentication", "step-up", "2fa", "mfa"))
        has_authz = any(
            marker in text_lower
            for marker in (
                "authorize",
                "authorization",
                "requires_auth",
                "permission",
                "scope",
                "rbac",
                "jwt",
            )
        )
        has_idempotency = bool(IDEMPOTENCY_MARKER_RE.search(text))

        if payment_entrypoint and not has_idempotency:
            findings.append(
                {
                    "severity": "tier2",
                    "rule": "banking-idempotency-key-missing",
                    "message": (
                        f"{file_path}: payment entrypoint appears to be missing idempotency-key handling."
                    ),
                    "confidence": "deterministic",
                    "remediation_owner": "domain-team",
                }
            )

        if payment_entrypoint and (not has_sca or not has_authz):
            findings.append(
                {
                    "severity": "tier1",
                    "rule": "banking-payment-boundary-controls-missing",
                    "message": (
                        f"{file_path}: payment entrypoint appears to miss explicit SCA/authz boundary markers."
                    ),
                    "confidence": "heuristic",
                    "remediation_owner": "security-team",
                }
            )

        if looks_like_payment_flow and not has_sca:
            findings.append(
                {
                    "severity": "tier1",
                    "rule": "banking-psd2-sca-missing-advisory",
                    "message": (
                        f"{file_path}: payment flow found without explicit SCA markers. "
                        "Verify SCA controls are enforced via middleware/policy. "
                        "Read docs/knowledge-base/banking-constraints.md for required controls."
                    ),
                    "confidence": "heuristic",
                    "remediation_owner": "domain-team",
                }
            )
    return findings
