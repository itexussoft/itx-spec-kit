"""Python mutation adapter supporting cosmic-ray JSON and mutmut junitxml output."""

from __future__ import annotations

import json
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List


def _status_from_bool(killed: Any) -> str:
    return "Killed" if bool(killed) else "Survived"


def _line_from_text(value: str) -> int | None:
    match = re.search(r":(\d+)(?::|$)", value)
    if not match:
        return None
    return int(match.group(1))


def _parse_cosmic_ray_json(raw_text: str) -> Dict[str, Any]:
    decoded = json.loads(raw_text)
    items: List[Any]
    if isinstance(decoded, dict):
        if isinstance(decoded.get("results"), list):
            items = decoded.get("results")
        elif isinstance(decoded.get("mutants"), list):
            items = decoded.get("mutants")
        else:
            items = []
    elif isinstance(decoded, list):
        items = decoded
    else:
        items = []

    mutants: List[Dict[str, Any]] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue
        mutator = str(item.get("operator") or item.get("mutator") or "cosmic-ray")
        module = str(item.get("module") or item.get("path") or item.get("file") or "").strip()
        occurrence = item.get("occurrence")
        line = int(occurrence) if isinstance(occurrence, int) else int(occurrence) if isinstance(occurrence, str) and occurrence.isdigit() else None
        mutant_id = str(item.get("id") or item.get("job_id") or f"cosmic-ray-{index}")
        status = str(item.get("status") or "").strip()
        if status:
            normalized_status = status
        else:
            normalized_status = _status_from_bool(item.get("killed"))
        mutants.append(
            {
                "id": mutant_id,
                "mutatorName": mutator,
                "location": {"file": module or None, "line": line, "column": None},
                "status": normalized_status,
                "replacement": None,
                "killedBy": [],
                "coveredBy": [],
                "duration": item.get("duration"),
            }
        )
    return {"schemaVersion": "1.0", "mutants": mutants}


def _parse_mutmut_junit(raw_text: str) -> Dict[str, Any]:
    root = ET.fromstring(raw_text)
    mutants: List[Dict[str, Any]] = []
    for index, testcase in enumerate(root.findall(".//testcase"), start=1):
        name = str(testcase.attrib.get("name", "")).strip()
        classname = str(testcase.attrib.get("classname", "")).strip()
        failure = testcase.find("failure")
        error = testcase.find("error")
        skipped = testcase.find("skipped")
        status = "Killed"
        if skipped is not None:
            status = "Ignored"
        elif failure is not None or error is not None:
            # mutmut junit output commonly reports surviving mutants as failing testcases.
            status = "Survived"
        file_hint = classname.replace(".", "/") + ".py" if classname else None
        line = _line_from_text(name) if name else None
        mutant_id = name or f"mutmut-{index}"
        mutants.append(
            {
                "id": mutant_id,
                "mutatorName": "mutmut",
                "location": {"file": file_hint, "line": line, "column": None},
                "status": status,
                "replacement": None,
                "killedBy": [],
                "coveredBy": [],
                "duration": None,
            }
        )
    return {"schemaVersion": "1.0", "mutants": mutants}


def _normalize_command(raw: Any) -> List[str]:
    if isinstance(raw, list):
        return [str(part) for part in raw if str(part).strip()]
    if isinstance(raw, str) and raw.strip():
        return [raw.strip()]
    return []


def _detect_format(explicit: str, raw_text: str) -> str:
    if explicit and explicit in {"cosmic-ray", "junit"}:
        return explicit
    stripped = raw_text.lstrip()
    if stripped.startswith("<"):
        return "junit"
    return "cosmic-ray"


def run(workspace: Path, config: Dict[str, Any]) -> Dict[str, Any]:
    settings = config.get("python") if isinstance(config.get("python"), dict) else {}
    command = _normalize_command(settings.get("command"))
    report_file = settings.get("report_file")
    fmt = str(settings.get("format", "auto")).strip().lower()
    try:
        timeout_s = max(1, int(config.get("timeout_s", 120)))
    except (TypeError, ValueError):
        timeout_s = 120

    exit_code = 0
    stdout = ""
    stderr = ""
    if command:
        try:
            result = subprocess.run(
                command,
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
                "tool": "python",
                "command": command,
                "report": {},
                "exit_code": 127,
                "error": f"Python mutation command binary not found: {exc}",
            }
        except subprocess.TimeoutExpired:
            return {
                "tool": "python",
                "command": command,
                "report": {},
                "exit_code": 124,
                "error": f"Python mutation command timed out after {timeout_s}s.",
            }

    raw_text = stdout
    if isinstance(report_file, str) and report_file.strip():
        candidate = workspace / report_file.strip()
        if candidate.exists():
            raw_text = candidate.read_text(encoding="utf-8", errors="ignore")

    if not raw_text.strip():
        return {
            "tool": "python",
            "command": command,
            "report": {},
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "parse_error": "Empty mutation report output.",
        }

    parse_error: str | None = None
    report_payload: Dict[str, Any] = {}
    try:
        detected = _detect_format(fmt, raw_text)
        if detected == "junit":
            report_payload = _parse_mutmut_junit(raw_text)
        else:
            report_payload = _parse_cosmic_ray_json(raw_text)
    except Exception as exc:  # noqa: BLE001
        parse_error = str(exc)

    return {
        "tool": "python",
        "command": command,
        "report": report_payload,
        "parse_error": parse_error,
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
    }
