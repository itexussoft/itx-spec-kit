"""Trading domain validators."""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import List

from validators import Finding, collect_code_files

TS_MONEY_NUMBER_RE = re.compile(r"\b(price|amount)\b\s*:\s*number\b", re.IGNORECASE)
TS_PARSE_FLOAT_RE = re.compile(r"\b(price|amount)\b\s*=\s*parseFloat\(", re.IGNORECASE)
TS_NUMBER_CAST_RE = re.compile(r"\b(price|amount)\b\s*=\s*Number\(", re.IGNORECASE)
ENTRYPOINT_RE = re.compile(
    r"(@router\.(post|put|patch)|@app\.route\s*\(.*(post|put|patch)|\bdef\s+(create|submit|place)_?order)",
    re.IGNORECASE,
)
IDEMPOTENCY_RE = re.compile(r"(idempotency[-_ ]?key|x-idempotency-key)", re.IGNORECASE)
REPLAY_MARKER_RE = re.compile(r"(dedup|replay|nonce|sequence|seq_no|event_id|message_id)", re.IGNORECASE)
BLOCKING_IO_RE = re.compile(r"\b(requests\.(get|post|put|delete)|time\.sleep|subprocess\.)", re.IGNORECASE)
LIFECYCLE_ASSIGN_RE = re.compile(r"(status|state)\s*=\s*[\"']([A-Z_]+)[\"']")
ALLOWED_TRANSITIONS = {
    ("NEW", "PENDING"),
    ("PENDING", "OPEN"),
    ("OPEN", "PARTIALLY_FILLED"),
    ("PARTIALLY_FILLED", "FILLED"),
    ("OPEN", "FILLED"),
    ("OPEN", "CANCELLED"),
    ("PARTIALLY_FILLED", "CANCELLED"),
    ("PENDING", "REJECTED"),
    ("NEW", "REJECTED"),
}


def run(workspace: Path) -> List[Finding]:
    """Tier 2 check: reject float monetary logic for price/amount fields."""
    findings: List[Finding] = []
    candidate_names = {"price", "amount"}
    for file_path in collect_code_files(workspace, [".py"], skip_test_like=True):
        source = file_path.read_text(encoding="utf-8")
        lower_source = source.lower()
        try:
            tree = ast.parse(source)
        except Exception as exc:
            findings.append(
                {
                    "severity": "tier1",
                    "rule": "trading-parse-failed",
                    "message": f"{file_path}: validator skipped unparsable file ({exc}).",
                    "confidence": "heuristic",
                    "remediation_owner": "domain-team",
                }
            )
            continue

        if ENTRYPOINT_RE.search(source) and not IDEMPOTENCY_RE.search(source):
            findings.append(
                {
                    "severity": "tier2",
                    "rule": "trading-idempotency-key-missing",
                    "message": f"{file_path}: trading entrypoint appears to miss idempotency-key handling.",
                    "confidence": "deterministic",
                    "remediation_owner": "domain-team",
                }
            )

        if ("event" in lower_source or "execution" in lower_source) and not REPLAY_MARKER_RE.search(source):
            findings.append(
                {
                    "severity": "tier1",
                    "rule": "trading-replay-protection-missing",
                    "message": (
                        f"{file_path}: execution/event handling appears without explicit replay/dedup markers."
                    ),
                    "confidence": "heuristic",
                    "remediation_owner": "domain-team",
                }
            )

        if (
            "matching" in lower_source or "orderbook" in lower_source or "execution" in lower_source
        ) and BLOCKING_IO_RE.search(source):
            findings.append(
                {
                    "severity": "tier2",
                    "rule": "trading-hotpath-blocking-io",
                    "message": (f"{file_path}: blocking I/O detected in potential trading hot path."),
                    "confidence": "deterministic",
                    "remediation_owner": "domain-team",
                }
            )

        transitions = []
        for match in LIFECYCLE_ASSIGN_RE.finditer(source):
            transitions.append(match.group(2))
        for idx in range(len(transitions) - 1):
            edge = (transitions[idx], transitions[idx + 1])
            if edge not in ALLOWED_TRANSITIONS:
                findings.append(
                    {
                        "severity": "tier2",
                        "rule": "trading-order-lifecycle-illegal-transition",
                        "message": (
                            f"{file_path}: order lifecycle transition {edge[0]} -> {edge[1]} is not in allowed trading transitions."
                        ),
                        "confidence": "deterministic",
                        "remediation_owner": "domain-team",
                    }
                )
                break

        for node in ast.walk(tree):
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                if node.target.id.lower() in candidate_names:
                    if isinstance(node.annotation, ast.Name) and node.annotation.id == "float":
                        findings.append(
                            {
                                "severity": "tier2",
                                "rule": "trading-no-float-money",
                                "message": (
                                    f"{file_path}: '{node.target.id}' uses float annotation. "
                                    "Read docs/knowledge-base/trading-constraints.md for required controls."
                                ),
                                "confidence": "deterministic",
                                "remediation_owner": "domain-team",
                            }
                        )
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id.lower() in candidate_names:
                        if isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Name):
                            if node.value.func.id == "float":
                                findings.append(
                                    {
                                        "severity": "tier2",
                                        "rule": "trading-no-float-money",
                                        "message": (
                                            f"{file_path}: '{target.id}' assigned via float(). "
                                            "Read docs/knowledge-base/trading-constraints.md for required controls."
                                        ),
                                        "confidence": "deterministic",
                                        "remediation_owner": "domain-team",
                                    }
                                )

    for file_path in collect_code_files(workspace, [".ts"], skip_test_like=True):
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        lower_text = text.lower()
        if ENTRYPOINT_RE.search(text) and not IDEMPOTENCY_RE.search(text):
            findings.append(
                {
                    "severity": "tier2",
                    "rule": "trading-idempotency-key-missing",
                    "message": f"{file_path}: trading entrypoint appears to miss idempotency-key handling.",
                    "confidence": "deterministic",
                    "remediation_owner": "domain-team",
                }
            )
        if ("event" in lower_text or "execution" in lower_text) and not REPLAY_MARKER_RE.search(text):
            findings.append(
                {
                    "severity": "tier1",
                    "rule": "trading-replay-protection-missing",
                    "message": (
                        f"{file_path}: execution/event handling appears without explicit replay/dedup markers."
                    ),
                    "confidence": "heuristic",
                    "remediation_owner": "domain-team",
                }
            )
        if (
            "matching" in lower_text or "orderbook" in lower_text or "execution" in lower_text
        ) and BLOCKING_IO_RE.search(text):
            findings.append(
                {
                    "severity": "tier2",
                    "rule": "trading-hotpath-blocking-io",
                    "message": (f"{file_path}: blocking I/O detected in potential trading hot path."),
                    "confidence": "deterministic",
                    "remediation_owner": "domain-team",
                }
            )
        transitions = [m.group(2) for m in LIFECYCLE_ASSIGN_RE.finditer(text)]
        for idx in range(len(transitions) - 1):
            edge = (transitions[idx], transitions[idx + 1])
            if edge not in ALLOWED_TRANSITIONS:
                findings.append(
                    {
                        "severity": "tier2",
                        "rule": "trading-order-lifecycle-illegal-transition",
                        "message": (
                            f"{file_path}: order lifecycle transition {edge[0]} -> {edge[1]} is not in allowed trading transitions."
                        ),
                        "confidence": "deterministic",
                        "remediation_owner": "domain-team",
                    }
                )
                break
        if TS_MONEY_NUMBER_RE.search(text) or TS_PARSE_FLOAT_RE.search(text) or TS_NUMBER_CAST_RE.search(text):
            findings.append(
                {
                    "severity": "tier2",
                    "rule": "trading-no-float-money",
                    "message": (
                        f"{file_path}: potential floating-point monetary usage for 'price/amount'. "
                        "Read docs/knowledge-base/trading-constraints.md for required controls."
                    ),
                    "confidence": "heuristic",
                    "remediation_owner": "domain-team",
                }
            )
    return findings
