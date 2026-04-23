"""Domain SAST validator entrypoint with provider-based execution."""

from __future__ import annotations

from pathlib import Path
from typing import List

from security_providers import resolve_security_settings, run_security_provider
from validators import Finding
from validators import banking_heuristic

def run(workspace: Path) -> List[Finding]:
    settings = resolve_security_settings(workspace, "fintech-banking")
    findings = run_security_provider(workspace, "fintech-banking")
    allow_compat_fallback = bool(settings.get("compat_heuristic_fallback", False))

    if allow_compat_fallback:
        findings.extend(banking_heuristic.run(workspace))
    return findings
