"""Architecture assurance runner for itx-gates."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from architecture_adapters import run as run_adapter
from orchestrator_common import TIER_1, TIER_2, Finding, ensure_context_dir
from rule_to_pattern_mapper import map_rule_to_pattern


_DEFAULT_SETTINGS: Dict[str, Any] = {
    "enabled": False,
    "mode": "advisory",
    "runner": "auto",
    "command": None,
    "parse": None,
    "events": ["after_implement"],
    "baseline_file": ".specify/context/architecture-baseline.json",
    "fail_on_unmapped_violation": False,
    "exit_code_signals": "report",
    "timeout_s": 120,
    "spectral": {"files": []},
    "archunit": {"command": None, "reports_glob": "target/surefire-reports/TEST-*.xml"},
    "modulith": {"command": None, "report_file": None},
}


def _merge(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in update.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _resolve_settings(policy: Dict[str, Any]) -> Dict[str, Any]:
    quality = policy.get("quality") if isinstance(policy.get("quality"), dict) else {}
    architecture = quality.get("architecture") if isinstance(quality.get("architecture"), dict) else {}
    return _merge(_DEFAULT_SETTINGS, architecture)


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return default


def _as_event_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return ["after_implement"]


def _resolve_path(workspace: Path, raw_path: Any) -> Path:
    if isinstance(raw_path, str) and raw_path.strip():
        candidate = Path(raw_path.strip())
        return candidate if candidate.is_absolute() else workspace / candidate
    return workspace / ".specify" / "context" / "architecture-baseline.json"


def _fingerprint(item: Dict[str, Any]) -> str:
    components = [
        str(item.get("rule_id") or "").strip().lower(),
        str(item.get("file") or "").strip().lower(),
        str(item.get("line") or ""),
        str(item.get("message") or "").strip().lower(),
    ]
    raw = "::".join(components)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _normalize_rule(rule_id: str) -> str:
    base = rule_id.strip().lower() or "architecture-violation"
    cleaned = "".join(ch if ch.isalnum() else "-" for ch in base).strip("-")
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return f"architecture-{cleaned or 'violation'}"


def _normalize_mode(value: Any) -> str:
    mode = str(value or "advisory").strip().lower()
    return mode if mode in {"advisory", "strict"} else "advisory"


def _load_baseline_fingerprints(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return set()
    if isinstance(payload, dict):
        values = payload.get("fingerprints")
        if isinstance(values, list):
            return {str(value).strip() for value in values if isinstance(value, str) and value.strip()}
    return set()


def _select_runner(settings: Dict[str, Any]) -> str | None:
    runner = str(settings.get("runner", "auto")).strip().lower() or "auto"
    if runner != "auto":
        return runner
    command = settings.get("command")
    if isinstance(command, list) and command:
        return "generic"
    spectral_cfg = settings.get("spectral") if isinstance(settings.get("spectral"), dict) else {}
    if isinstance(spectral_cfg.get("files"), list) and spectral_cfg.get("files"):
        return "spectral"
    arch_cfg = settings.get("archunit") if isinstance(settings.get("archunit"), dict) else {}
    if isinstance(arch_cfg.get("command"), list) and arch_cfg.get("command"):
        return "archunit"
    modulith_cfg = settings.get("modulith") if isinstance(settings.get("modulith"), dict) else {}
    report_file = modulith_cfg.get("report_file")
    if isinstance(report_file, str) and report_file.strip():
        return "modulith"
    return None


def _severity_for(level: str, mode: str, baseline_match: bool) -> str:
    if baseline_match:
        return TIER_1
    if mode == "strict":
        return TIER_2
    return TIER_1


def _confidence_for(severity: str) -> str:
    return "deterministic" if severity == TIER_2 else "heuristic"


def _to_sarif_level(raw: str) -> str:
    normalized = raw.strip().lower()
    if normalized in {"error", "high", "tier2"}:
        return "error"
    if normalized in {"warning", "warn", "medium", "tier1"}:
        return "warning"
    return "note"


def _build_sarif_report(*, tool: str, adapter: str, results: List[Dict[str, Any]]) -> Dict[str, Any]:
    sarif_results: List[Dict[str, Any]] = []
    for item in results:
        result_entry: Dict[str, Any] = {
            "ruleId": str(item.get("rule_id", "architecture-violation")),
            "level": _to_sarif_level(str(item.get("severity", "warning"))),
            "message": {"text": str(item.get("message", "Architecture rule violation."))},
            "properties": {
                "fingerprint": str(item.get("fingerprint", "")),
                "baselineMatch": bool(item.get("baseline_match")),
                "adapter": adapter,
            },
        }
        file_path = item.get("file")
        line = item.get("line")
        column = item.get("column")
        if isinstance(file_path, str) and file_path.strip():
            physical_location: Dict[str, Any] = {
                "artifactLocation": {"uri": file_path.strip()},
            }
            region: Dict[str, Any] = {}
            if isinstance(line, int) and line > 0:
                region["startLine"] = line
            if isinstance(column, int) and column > 0:
                region["startColumn"] = column
            if region:
                physical_location["region"] = region
            result_entry["locations"] = [{"physicalLocation": physical_location}]
        sarif_results.append(result_entry)

    return {
        "version": "2.1.0",
        "$schema": "https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.json",
        "runs": [
            {
                "tool": {"driver": {"name": "itx-gates-architecture", "informationUri": "https://refactoring.com/catalog/"}},
                "invocations": [{"executionSuccessful": True}],
                "properties": {"sourceTool": tool, "adapter": adapter, "generatedAt": datetime.now(timezone.utc).isoformat()},
                "results": sarif_results,
            }
        ],
    }


def _write_report(workspace: Path, payload: Dict[str, Any]) -> None:
    path = ensure_context_dir(workspace) / "architecture-report.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _base_finding(rule: str, message: str) -> Finding:
    return {
        "severity": TIER_1,
        "rule": rule,
        "message": message,
        "confidence": "heuristic",
        "remediation_owner": "feature-team",
    }


def run(*, event: str, workspace: Path, policy: Dict[str, Any]) -> List[Finding]:
    settings = _resolve_settings(policy)
    if not _as_bool(settings.get("enabled"), default=False):
        return []
    if event not in _as_event_list(settings.get("events")):
        return []

    adapter = _select_runner(settings)
    if not adapter:
        return [
            _base_finding(
                "architecture-config-missing",
                "Architecture checks are enabled but no runnable adapter configuration was found.",
            )
        ]

    result = run_adapter(adapter, workspace, settings)
    if result.get("error"):
        return [
            _base_finding(
                "architecture-runner-error",
                f"Architecture adapter '{adapter}' failed: {result.get('error')}",
            )
        ]

    mode = _normalize_mode(settings.get("mode"))
    baseline_path = _resolve_path(workspace, settings.get("baseline_file"))
    baseline_fingerprints = _load_baseline_fingerprints(baseline_path)
    parsed_violations = result.get("violations")
    violations = parsed_violations if isinstance(parsed_violations, list) else []
    findings: List[Finding] = []
    normalized_results: List[Dict[str, Any]] = []

    for raw in violations:
        if not isinstance(raw, dict):
            continue
        rule_id = str(raw.get("rule_id", "")).strip() or "architecture-violation"
        message = str(raw.get("message", "")).strip() or "Architecture rule violation."
        file_path = str(raw.get("file", "")).strip() or None
        line = raw.get("line")
        column = raw.get("column")
        line_int = int(line) if isinstance(line, int) and line > 0 else None
        col_int = int(column) if isinstance(column, int) and column > 0 else None
        fingerprint = _fingerprint({"rule_id": rule_id, "message": message, "file": file_path, "line": line_int})
        baseline_match = fingerprint in baseline_fingerprints
        severity = _severity_for(str(raw.get("severity", "warning")), mode, baseline_match)

        location_suffix = ""
        if file_path and line_int:
            location_suffix = f" ({file_path}:{line_int})"
        elif file_path:
            location_suffix = f" ({file_path})"
        prefix = "[pre-existing] " if baseline_match else ""
        finding_message = f"{prefix}{message}{location_suffix}"
        mapping = map_rule_to_pattern(rule_id)
        remediation = (
            f"Suggested pattern: {mapping.get('pattern')} | Anti-pattern: {mapping.get('anti_pattern')} | Reference: {mapping.get('reference')}"
            if mapping.get("matched")
            else f"Reference: {mapping.get('reference')}"
        )
        finding: Finding = {
            "severity": severity,
            "rule": _normalize_rule(rule_id),
            "message": finding_message,
            "confidence": _confidence_for(severity),
            "remediation_owner": "feature-team",
            "remediation": remediation,
        }
        findings.append(finding)
        normalized_results.append(
            {
                "rule_id": rule_id,
                "severity": str(raw.get("severity", "warning")),
                "message": message,
                "file": file_path,
                "line": line_int,
                "column": col_int,
                "fingerprint": fingerprint,
                "baseline_match": baseline_match,
            }
        )

        if _as_bool(settings.get("fail_on_unmapped_violation"), default=False) and not mapping.get("matched") and not baseline_match:
            findings.append(
                {
                    "severity": TIER_2,
                    "rule": "architecture-unmapped-rule",
                    "message": f"Architecture rule '{rule_id}' has no remediation mapping.",
                    "confidence": "deterministic",
                    "remediation_owner": "feature-team",
                    "remediation": f"Add deterministic mapping entry in rule_to_pattern_mapper.py. Reference: {mapping.get('reference')}",
                }
            )

    parse_error = str(result.get("parse_error") or "").strip()
    if parse_error:
        findings.append(
            _base_finding(
                "architecture-report-parse-failed",
                f"Architecture adapter '{adapter}' produced unreadable output: {parse_error}",
            )
        )

    exit_code = result.get("exit_code")
    if (
        isinstance(exit_code, int)
        and exit_code != 0
        and str(settings.get("exit_code_signals", "report")).strip().lower() == "violations"
        and not normalized_results
    ):
        findings.append(
            _base_finding(
                "architecture-command-failed",
                f"Architecture adapter '{adapter}' exited with code {exit_code} and no parseable report.",
            )
        )

    report_payload = _build_sarif_report(
        tool=str(result.get("tool", adapter)),
        adapter=adapter,
        results=normalized_results,
    )
    _write_report(workspace, report_payload)
    return findings

