"""PIT mutation adapter."""

from __future__ import annotations

import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List


def _parse_mutations_xml(raw_text: str) -> Dict[str, Any]:
    root = ET.fromstring(raw_text)
    mutants: List[Dict[str, Any]] = []
    for mutation in root.findall(".//mutation"):
        status = str(mutation.attrib.get("status", "Unknown")).strip()
        mutator = (mutation.findtext("mutator") or "").strip()
        source_file = (mutation.findtext("sourceFile") or "").strip()
        line_number = (mutation.findtext("lineNumber") or "").strip()
        description = (mutation.findtext("description") or "").strip()
        index = (mutation.findtext("index") or "").strip()
        mutant_id = f"{source_file}:{line_number}:{index}" if source_file or line_number else f"pitest:{len(mutants)+1}"
        line_int = int(line_number) if line_number.isdigit() else None
        mutants.append(
            {
                "id": mutant_id,
                "mutatorName": mutator or "pitest",
                "location": {"file": source_file or None, "line": line_int, "column": None},
                "status": status,
                "replacement": description or None,
                "killedBy": [],
                "coveredBy": [],
                "duration": None,
            }
        )
    return {"schemaVersion": "1.0", "mutants": mutants}


def run(workspace: Path, config: Dict[str, Any]) -> Dict[str, Any]:
    settings = config.get("pitest") if isinstance(config.get("pitest"), dict) else {}
    report_glob = str(settings.get("report_glob", "target/pit-reports/*/mutations.xml")).strip() or "target/pit-reports/*/mutations.xml"
    command = settings.get("command") if isinstance(settings.get("command"), list) else []
    try:
        timeout_s = max(1, int(config.get("timeout_s", 120)))
    except (TypeError, ValueError):
        timeout_s = 120
    exit_code = 0
    stdout = ""
    stderr = ""
    cmd_list = [str(part) for part in command if str(part).strip()]
    if cmd_list:
        try:
            result = subprocess.run(
                cmd_list,
                cwd=str(workspace),
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
            exit_code = result.returncode
            stdout = result.stdout or ""
            stderr = result.stderr or ""
        except FileNotFoundError as exc:
            return {
                "tool": "pitest",
                "command": cmd_list,
                "report": {},
                "exit_code": 127,
                "error": f"PIT command binary not found: {exc}",
            }
        except subprocess.TimeoutExpired:
            return {
                "tool": "pitest",
                "command": cmd_list,
                "report": {},
                "exit_code": 124,
                "error": f"PIT command timed out after {timeout_s}s.",
            }

    candidates = sorted(workspace.glob(report_glob))
    if not candidates:
        return {
            "tool": "pitest",
            "command": cmd_list,
            "report": {},
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "error": f"PIT report file not found for glob: {report_glob}",
        }

    parse_error: str | None = None
    report_payload: Dict[str, Any] = {}
    try:
        latest = candidates[-1]
        report_payload = _parse_mutations_xml(latest.read_text(encoding="utf-8", errors="ignore"))
    except Exception as exc:  # noqa: BLE001
        parse_error = str(exc)

    return {
        "tool": "pitest",
        "command": cmd_list,
        "report": report_payload,
        "parse_error": parse_error,
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
    }

