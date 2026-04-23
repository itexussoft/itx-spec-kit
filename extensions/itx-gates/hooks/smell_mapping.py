"""Smell-to-refactoring guidance mapping for execution briefs."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

import yaml

_RULE_RE = re.compile(r"- Rule:\s+`([^`]+)`")
_MSG_RE = re.compile(r"- Message:\s+(.+)")
_RULE_ID_HINT_RE = re.compile(r"\b([A-Za-z]+:[A-Za-z0-9_-]+)\b")
_DEFAULT_REF = "https://refactoring.com/catalog/"


def _normalize(value: str) -> str:
    return value.strip().lower()


def _catalog_path(workspace: Path) -> Path:
    return workspace / ".specify" / "smell-catalog.yml"


def load_smell_catalog(workspace: Path) -> Dict[str, Any]:
    path = _catalog_path(workspace)
    if not path.exists():
        return {"version": 1, "smells": []}
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return {"version": 1, "smells": []}
    if not isinstance(raw, dict):
        return {"version": 1, "smells": []}
    smells = raw.get("smells")
    if not isinstance(smells, list):
        raw["smells"] = []
    return raw


def build_reverse_index(catalog: Dict[str, Any]) -> Dict[str, str]:
    index: Dict[str, str] = {}
    smells = catalog.get("smells") if isinstance(catalog.get("smells"), list) else []
    for raw in smells:
        if not isinstance(raw, dict):
            continue
        smell_id = str(raw.get("id", "")).strip()
        if not smell_id:
            continue
        canonical = smell_id
        index[_normalize(smell_id)] = canonical
        fowler_name = str(raw.get("fowler_name", "")).strip()
        if fowler_name:
            index[_normalize(fowler_name)] = canonical
        aliases = raw.get("aliases") if isinstance(raw.get("aliases"), list) else []
        for alias in aliases:
            alias_text = str(alias).strip()
            if alias_text:
                index[_normalize(alias_text)] = canonical
        detectors = raw.get("detectors") if isinstance(raw.get("detectors"), dict) else {}
        for values in detectors.values():
            if not isinstance(values, list):
                continue
            for detector_rule in values:
                detector_text = str(detector_rule).strip()
                if detector_text:
                    index[_normalize(detector_text)] = canonical
    return index


def _smell_by_id(catalog: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    mapping: Dict[str, Dict[str, Any]] = {}
    smells = catalog.get("smells") if isinstance(catalog.get("smells"), list) else []
    for raw in smells:
        if not isinstance(raw, dict):
            continue
        smell_id = str(raw.get("id", "")).strip()
        if smell_id:
            mapping[smell_id] = raw
    return mapping


def _candidate_rules(rule_id: str, message: str) -> List[str]:
    candidates: set[str] = set()
    raw_rule = rule_id.strip()
    if raw_rule:
        normalized_rule = _normalize(raw_rule)
        candidates.add(normalized_rule)
        if "-" in normalized_rule:
            split_once = normalized_rule.split("-", maxsplit=1)[1]
            candidates.add(split_once)
        if "_" in normalized_rule:
            candidates.add(normalized_rule.replace("_", "-"))
    for match in _RULE_ID_HINT_RE.findall(message):
        candidates.add(_normalize(match))
    return sorted(candidates)


def map_rule_to_smell(workspace: Path, rule_id: str, message: str = "") -> Dict[str, Any] | None:
    catalog = load_smell_catalog(workspace)
    reverse = build_reverse_index(catalog)
    smells = _smell_by_id(catalog)
    for candidate in _candidate_rules(rule_id, message):
        smell_id = reverse.get(candidate)
        if not smell_id:
            continue
        smell = smells.get(smell_id)
        if isinstance(smell, dict):
            return smell
    return None


def _primary_refactoring(smell: Dict[str, Any]) -> Dict[str, Any] | None:
    refactorings = smell.get("refactorings")
    if not isinstance(refactorings, list) or not refactorings:
        return None
    ranked = sorted(
        [item for item in refactorings if isinstance(item, dict)],
        key=lambda item: int(item.get("priority")) if isinstance(item.get("priority"), int) else 999,
    )
    return ranked[0] if ranked else None


def _test_first_summary(smell: Dict[str, Any]) -> str:
    test_first = smell.get("test_first") if isinstance(smell.get("test_first"), dict) else {}
    strategy = str(test_first.get("strategy", "")).strip()
    hint = str(test_first.get("hint", "")).strip()
    if strategy and hint:
        return f"Test-first: {strategy} - {hint}"
    if strategy:
        return f"Test-first: {strategy}"
    if hint:
        return f"Test-first: {hint}"
    return ""


def _guidance_line(*, smell: Dict[str, Any], rule_id: str) -> str:
    smell_id = str(smell.get("id", "UNKNOWN")).strip() or "UNKNOWN"
    fowler_name = str(smell.get("fowler_name", "")).strip() or smell_id
    advisory = str(smell.get("advisory", "")).strip()
    primary = _primary_refactoring(smell)
    if primary:
        intent = str(primary.get("intent", "")).strip() or "Apply the mapped refactoring intent."
        ref_name = str(primary.get("id", "refactoring")).strip()
        url = str(primary.get("url", "")).strip() or _DEFAULT_REF
        base = f"{fowler_name} ({smell_id}) via `{rule_id}`: {ref_name} - {intent} ({url})"
    else:
        base = f"{fowler_name} ({smell_id}) via `{rule_id}`: see {_DEFAULT_REF}"
    test_first = _test_first_summary(smell)
    if test_first:
        base = f"{base}. {test_first}"
    if advisory:
        base = f"{base}. {advisory}"
    return base


def _parse_gate_feedback(gate_feedback_text: str) -> List[Dict[str, str]]:
    findings: List[Dict[str, str]] = []
    for block in gate_feedback_text.split("## Finding ")[1:]:
        rule_match = _RULE_RE.search(block)
        msg_match = _MSG_RE.search(block)
        if not rule_match or not msg_match:
            continue
        rule = rule_match.group(1).strip()
        message = msg_match.group(1).strip()
        findings.append({"rule": rule, "message": message})
    return findings


def guidance_from_findings(workspace: Path, findings: Sequence[Dict[str, str]]) -> List[str]:
    guidance: List[str] = []
    seen: set[str] = set()
    for item in findings:
        rule = str(item.get("rule", "")).strip()
        message = str(item.get("message", "")).strip()
        if not rule:
            continue
        smell = map_rule_to_smell(workspace, rule, message)
        if smell is not None:
            smell_id = str(smell.get("id", "")).strip()
            key = f"smell:{smell_id}:{rule.lower()}"
            if key in seen:
                continue
            seen.add(key)
            guidance.append(_guidance_line(smell=smell, rule_id=rule))
            continue
        if _normalize(rule).startswith("smell-"):
            key = f"unknown:{rule.lower()}"
            if key in seen:
                continue
            seen.add(key)
            guidance.append(f"Unmapped smell rule `{rule}`: use the Fowler catalog at {_DEFAULT_REF} for deterministic guidance.")
    return guidance


def guidance_from_gate_feedback(workspace: Path, gate_feedback_text: str) -> List[str]:
    parsed = _parse_gate_feedback(gate_feedback_text)
    return guidance_from_findings(workspace, parsed)


def reverse_index_for_workspace(workspace: Path) -> Dict[str, str]:
    return build_reverse_index(load_smell_catalog(workspace))

