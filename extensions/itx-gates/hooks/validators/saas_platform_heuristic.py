"""SaaS platform domain validators — heuristic tenant isolation checks."""

from __future__ import annotations

import re
from pathlib import Path
from typing import List

from validators import Finding, collect_code_files

# File must mention multi-tenant concepts before we emit tenant-scoping findings.
_TENANT_DOMAIN_SIGNAL_RE = re.compile(
    r"\b(tenant_id|TenantId|tenant_context|TenantContext|multi[-_]?tenant|rls\b|row[-_]?level)",
    re.IGNORECASE,
)

# Raw SQL segments (heuristic): SELECT ... FROM <table> without tenant filter in same segment.
_RAW_SQL_BLOCK_RE = re.compile(r'("""|\'\'\')(.*?)\1', re.DOTALL)
_SELECT_FROM_RE = re.compile(
    r"(?is)\bselect\b.+?\bfrom\b\s+[`\"']?(\w+)[`\"']?",
)
_TENANT_SCOPED_TABLE_HINTS = frozenset(
    {
        "users",
        "user",
        "orders",
        "order",
        "accounts",
        "account",
        "subscriptions",
        "subscription",
        "invoices",
        "invoice",
        "tenants",
        "tenant",
    }
)

# SQLAlchemy-style session.query(...).all() on one line without filter/tenant.
_SESSION_QUERY_ALL_RE = re.compile(
    r"session\.query\s*\([^)]+\)\s*\.(all|first|one|scalar)\s*\(",
    re.IGNORECASE,
)

# Cache/redis get/set with a string literal key.
_CACHE_LITERAL_RE = re.compile(
    r"\b(?:cache|redis|redis_client)\s*\.\s*(?:get|set|mget|mset|delete)\s*\(\s*[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)


def _segment_has_tenant_filter(segment: str) -> bool:
    lower = segment.lower()
    return "tenant_id" in lower or "app.tenant_id" in lower or "current_setting" in lower


def _cache_key_has_tenant_token(key: str) -> bool:
    k = key.lower()
    return any(
        token in k
        for token in (
            "tenant",
            "tenant_id",
            "tid",
            ":t:",
            "t:",
            "{tenant",
            "${tenant",
            'f"t:',
            "f't:",
        )
    )


def run(workspace: Path) -> List[Finding]:
    """Heuristic checks for obvious multi-tenant isolation gaps."""
    findings: List[Finding] = []
    code_files = collect_code_files(workspace, [".py", ".ts", ".js"], skip_test_like=True)

    for file_path in code_files:
        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            findings.append(
                {
                    "severity": "tier1",
                    "rule": "validator-file-read-failed",
                    "message": f"{file_path}: failed to read file during SaaS validation ({exc}).",
                    "confidence": "heuristic",
                    "remediation_owner": "domain-team",
                }
            )
            continue

        if not _TENANT_DOMAIN_SIGNAL_RE.search(text):
            continue

        tenant_filter_issue = False
        for match in _RAW_SQL_BLOCK_RE.finditer(text):
            block = match.group(2)
            if not re.search(r"(?i)\bselect\b", block):
                continue
            for from_match in _SELECT_FROM_RE.finditer(block):
                table = from_match.group(1).lower()
                if table not in _TENANT_SCOPED_TABLE_HINTS:
                    continue
                segment = block[max(0, from_match.start() - 200) : from_match.end() + 400]
                if not _segment_has_tenant_filter(segment):
                    tenant_filter_issue = True
                    break
            if tenant_filter_issue:
                break

        if not tenant_filter_issue:
            for line in text.splitlines():
                if _SESSION_QUERY_ALL_RE.search(line) and "filter" not in line.lower() and "tenant" not in line.lower():
                    tenant_filter_issue = True
                    break

        if tenant_filter_issue:
            findings.append(
                {
                    "severity": "tier1",
                    "rule": "saas-tenant-filter-missing",
                    "message": (
                        f"{file_path}: possible tenant-scoped query without explicit tenant_id filter "
                        "(raw SQL or session.query). Read docs/knowledge-base/saas-platform-constraints.md."
                    ),
                    "confidence": "heuristic",
                    "remediation_owner": "domain-team",
                }
            )

        cache_issue = False
        for cache_match in _CACHE_LITERAL_RE.finditer(text):
            key = cache_match.group(1)
            if key and not _cache_key_has_tenant_token(key):
                cache_issue = True
                break

        if cache_issue:
            findings.append(
                {
                    "severity": "tier1",
                    "rule": "saas-global-cache-key",
                    "message": (
                        f"{file_path}: cache/redis call uses a literal key that may omit tenant scope. "
                        "Prefix keys with tenant id or namespace. See multi-tenant-data-isolation.md."
                    ),
                    "confidence": "heuristic",
                    "remediation_owner": "domain-team",
                }
            )

    return findings
