"""ArchUnit adapter (JUnit XML-oriented)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Dict, List

from architecture_parsers.junit_xml import parse_junit_xml_text


def _default_command(workspace: Path) -> List[str]:
    if (workspace / "pom.xml").exists():
        return ["mvn", "test", "-q"]
    if (workspace / "build.gradle").exists() or (workspace / "build.gradle.kts").exists():
        return ["gradle", "test"]
    return []


def run(workspace: Path, config: Dict[str, Any]) -> Dict[str, Any]:
    arch_cfg = config.get("archunit") if isinstance(config.get("archunit"), dict) else {}
    try:
        timeout_s = max(1, int(config.get("timeout_s", 120)))
    except (TypeError, ValueError):
        timeout_s = 120
    explicit_command = arch_cfg.get("command") if isinstance(arch_cfg.get("command"), list) else None
    command = [str(part) for part in explicit_command] if explicit_command else _default_command(workspace)
    reports_glob = str(arch_cfg.get("reports_glob", "target/surefire-reports/TEST-*.xml")).strip() or "target/surefire-reports/TEST-*.xml"

    if not command:
        return {
            "tool": "archunit",
            "violations": [],
            "exit_code": 0,
            "error": "ArchUnit adapter requires 'archunit.command' or a Maven/Gradle build file in the workspace.",
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
            "tool": "archunit",
            "command": command,
            "violations": [],
            "exit_code": 127,
            "error": f"ArchUnit command binary not found: {exc}",
        }
    except subprocess.TimeoutExpired:
        return {
            "tool": "archunit",
            "command": command,
            "violations": [],
            "exit_code": 124,
            "error": f"ArchUnit command timed out after {timeout_s}s.",
        }

    findings: List[Dict[str, Any]] = []
    parse_error: str | None = None
    report_files = sorted(workspace.glob(reports_glob))
    try:
        if report_files:
            for report in report_files:
                findings.extend(parse_junit_xml_text(report.read_text(encoding="utf-8", errors="ignore")))
        elif (result.stdout or "").lstrip().startswith("<"):
            findings.extend(parse_junit_xml_text(result.stdout or ""))
    except Exception as exc:  # noqa: BLE001
        parse_error = str(exc)

    return {
        "tool": "archunit",
        "command": command,
        "violations": findings,
        "parse_error": parse_error,
        "exit_code": result.returncode,
        "stdout": result.stdout or "",
        "stderr": result.stderr or "",
    }
