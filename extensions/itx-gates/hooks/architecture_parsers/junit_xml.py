"""JUnit XML parser for architecture-related test failures."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any, Dict, List


def _collect_failures(case: ET.Element) -> List[Dict[str, Any]]:
    outputs: List[Dict[str, Any]] = []
    for tag in ("failure", "error"):
        for node in case.findall(tag):
            message_attr = (node.attrib.get("message") or "").strip()
            text = (node.text or "").strip()
            message = message_attr or text or "Architecture rule failure."
            outputs.append(
                {
                    "tag": tag,
                    "message": message,
                    "line": node.attrib.get("line"),
                    "type": (node.attrib.get("type") or "").strip(),
                }
            )
    return outputs


def parse_junit_xml_text(raw_text: str) -> List[Dict[str, Any]]:
    try:
        root = ET.fromstring(raw_text)
    except ET.ParseError as exc:
        raise ValueError(f"Invalid JUnit XML: {exc}") from exc

    findings: List[Dict[str, Any]] = []
    testcases = root.findall(".//testcase")
    for case in testcases:
        class_name = (case.attrib.get("classname") or "").strip()
        test_name = (case.attrib.get("name") or "").strip()
        file_path = (case.attrib.get("file") or "").strip() or None
        case_line = case.attrib.get("line")
        case_line_int = int(case_line) if isinstance(case_line, str) and case_line.isdigit() else None
        failures = _collect_failures(case)
        for failure in failures:
            line_value: int | None = None
            raw_line = failure.get("line")
            if isinstance(raw_line, str) and raw_line.isdigit():
                line_value = int(raw_line)
            elif case_line_int is not None:
                line_value = case_line_int
            rule_bits = [part for part in (class_name, test_name) if part]
            rule_id = ".".join(rule_bits) if rule_bits else "junit-violation"
            findings.append(
                {
                    "rule_id": rule_id,
                    "severity": "error",
                    "message": str(failure.get("message", "")).strip() or "Architecture rule failure.",
                    "file": file_path,
                    "line": line_value,
                    "column": None,
                }
            )
    return findings

