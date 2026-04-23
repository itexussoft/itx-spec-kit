"""Mutation testing runner for itx-gates."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import yaml

from mutation_adapters import run as run_adapter
from mutation_remediation import remediation_for
from orchestrator_common import TIER_1, TIER_2, Finding, ensure_context_dir


_DEFAULT_SETTINGS: Dict[str, Any] = {
    "enabled": False,
    "mode": "advisory",
    "threshold": 60,
    "strict_threshold": 80,
    "runner": "auto",
    "command": None,
    "incremental": True,
    "flaky_reruns": 2,
    "ignore_file": ".specify/mutation-ignore.yml",
    "scope": "core_modules",
    "baseline_file": ".specify/context/mutation-baseline.json",
    "events": ["after_implement"],
    "exit_code_signals": "report",
    "timeout_s": 120,
    "stryker": {"command": None, "report_file": "reports/mutation/mutation.json"},
    "pitest": {"command": None, "report_glob": "target/pit-reports/*/mutations.xml"},
    "cargo-mutants": {"command": None, "report_file": "mutants.out/outcomes.json"},
    "python": {"command": None, "report_file": None, "format": "auto"},
    "generic": {"report_file": None},
}

_SCORABLE_STATUSES = {"Killed", "Survived", "NoCoverage", "Timeout", "CompileError", "RuntimeError", "Unknown"}


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
    mutation = quality.get("mutation_testing") if isinstance(quality.get("mutation_testing"), dict) else {}
    merged = _merge(_DEFAULT_SETTINGS, mutation)
    # Backward-compatible alias support.
    cargo_alias = merged.get("cargo_mutants")
    if isinstance(cargo_alias, dict) and not isinstance(merged.get("cargo-mutants"), dict):
        merged["cargo-mutants"] = cargo_alias
    return merged


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


def _as_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed


def _as_event_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return ["after_implement"]


def _resolve_path(workspace: Path, raw_path: Any, default_rel: str) -> Path:
    if isinstance(raw_path, str) and raw_path.strip():
        candidate = Path(raw_path.strip())
        return candidate if candidate.is_absolute() else workspace / candidate
    return workspace / default_rel


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


def _load_ignore(path: Path) -> Tuple[set[str], set[str]]:
    if not path.exists():
        return set(), set()
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError):
        return set(), set()
    mutant_ids: set[str] = set()
    fingerprints: set[str] = set()
    if isinstance(payload, dict):
        ids_raw = payload.get("mutant_ids")
        if isinstance(ids_raw, list):
            mutant_ids.update(str(item).strip() for item in ids_raw if str(item).strip())
        fp_raw = payload.get("fingerprints")
        if isinstance(fp_raw, list):
            fingerprints.update(str(item).strip() for item in fp_raw if str(item).strip())
    elif isinstance(payload, list):
        mutant_ids.update(str(item).strip() for item in payload if str(item).strip())
    return mutant_ids, fingerprints


def _normalize_mode(value: Any) -> str:
    mode = str(value or "advisory").strip().lower()
    return mode if mode in {"advisory", "strict"} else "advisory"


def _is_command_list(value: Any) -> bool:
    return isinstance(value, list) and any(str(item).strip() for item in value)


def _settings_dict(settings: Dict[str, Any], key: str, alt_key: str | None = None) -> Dict[str, Any]:
    value = settings.get(key)
    if isinstance(value, dict):
        return value
    if alt_key:
        alt_value = settings.get(alt_key)
        if isinstance(alt_value, dict):
            return alt_value
    return {}


def _select_runner(settings: Dict[str, Any], workspace: Path) -> str | None:
    runner = str(settings.get("runner", "auto")).strip().lower() or "auto"
    if runner != "auto":
        return runner
    if _is_command_list(settings.get("command")):
        return "generic"

    stryker_cfg = _settings_dict(settings, "stryker")
    if _is_command_list(stryker_cfg.get("command")):
        return "stryker"
    stryker_report = str(stryker_cfg.get("report_file", "reports/mutation/mutation.json")).strip()
    if stryker_report and (workspace / stryker_report).exists():
        return "stryker"

    pitest_cfg = _settings_dict(settings, "pitest")
    if _is_command_list(pitest_cfg.get("command")):
        return "pitest"
    pitest_glob = str(pitest_cfg.get("report_glob", "target/pit-reports/*/mutations.xml")).strip()
    if pitest_glob and list(workspace.glob(pitest_glob)):
        return "pitest"

    cargo_cfg = _settings_dict(settings, "cargo-mutants", "cargo_mutants")
    if _is_command_list(cargo_cfg.get("command")):
        return "cargo-mutants"
    cargo_report = str(cargo_cfg.get("report_file", "mutants.out/outcomes.json")).strip()
    if cargo_report and (workspace / cargo_report).exists():
        return "cargo-mutants"

    python_cfg = _settings_dict(settings, "python")
    if _is_command_list(python_cfg.get("command")):
        return "python"
    python_report = python_cfg.get("report_file")
    if isinstance(python_report, str) and python_report.strip() and (workspace / python_report.strip()).exists():
        return "python"

    return None


def _status_from(value: Any) -> str:
    raw = str(value or "Unknown").strip().lower()
    if raw in {"killed", "caught", "fail", "failed"}:
        return "Killed"
    if raw in {"survived", "alive", "missed", "ok", "notkilled"}:
        return "Survived"
    if raw in {"nocoverage", "no_coverage", "uncovered"}:
        return "NoCoverage"
    if raw in {"timeout", "timedout"}:
        return "Timeout"
    if raw in {"ignored", "skip", "skipped"}:
        return "Ignored"
    if raw in {"compileerror", "compile_error"}:
        return "CompileError"
    if raw in {"runtimeerror", "runtime_error"}:
        return "RuntimeError"
    return "Unknown"


def _to_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str) and value.strip().isdigit():
        parsed = int(value.strip())
        return parsed if parsed > 0 else None
    return None


def _mutant_fingerprint(item: Dict[str, Any]) -> str:
    location = item.get("location") if isinstance(item.get("location"), dict) else {}
    components = [
        str(item.get("id") or "").strip().lower(),
        str(item.get("mutatorName") or "").strip().lower(),
        str(location.get("file") or "").strip().lower(),
        str(location.get("line") or ""),
        str(item.get("replacement") or "").strip().lower(),
    ]
    raw = "::".join(components)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _normalize_mutants(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw_mutants = report.get("mutants") if isinstance(report.get("mutants"), list) else []
    normalized: List[Dict[str, Any]] = []
    for index, raw in enumerate(raw_mutants, start=1):
        if not isinstance(raw, dict):
            continue
        location = raw.get("location") if isinstance(raw.get("location"), dict) else {}
        file_path = raw.get("file") if isinstance(raw.get("file"), str) else location.get("file")
        line = raw.get("line") if raw.get("line") is not None else location.get("line")
        col = raw.get("column") if raw.get("column") is not None else location.get("column")
        status_reason = raw.get("statusReason") if raw.get("statusReason") is not None else raw.get("status_reason")
        entry: Dict[str, Any] = {
            "id": str(raw.get("id") or f"mutant-{index}"),
            "mutatorName": str(raw.get("mutatorName") or raw.get("mutator") or "unknown"),
            "location": {
                "file": str(file_path).strip() if isinstance(file_path, str) and file_path.strip() else None,
                "line": _to_int(line),
                "column": _to_int(col),
            },
            "status": _status_from(raw.get("status")),
            "replacement": str(raw.get("replacement")).strip() if isinstance(raw.get("replacement"), str) and raw.get("replacement").strip() else None,
            "killedBy": raw.get("killedBy") if isinstance(raw.get("killedBy"), list) else [],
            "coveredBy": raw.get("coveredBy") if isinstance(raw.get("coveredBy"), list) else [],
            "duration": raw.get("duration"),
        }
        if isinstance(status_reason, str) and status_reason.strip():
            entry["statusReason"] = status_reason.strip().lower()
        entry["fingerprint"] = str(raw.get("fingerprint")).strip() if isinstance(raw.get("fingerprint"), str) and raw.get("fingerprint").strip() else _mutant_fingerprint(entry)
        normalized.append(entry)
    return normalized


def _scorable(mutant: Dict[str, Any]) -> bool:
    if mutant.get("baselineMatch"):
        return False
    if str(mutant.get("statusReason", "")).strip().lower() == "flaky":
        return False
    status = str(mutant.get("status", "Unknown"))
    return status in _SCORABLE_STATUSES


def _score(mutants: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    total = 0
    killed = 0
    survived = 0
    no_coverage = 0
    timeout = 0
    errors = 0
    for mutant in mutants:
        if not _scorable(mutant):
            continue
        total += 1
        status = str(mutant.get("status", "Unknown"))
        if status == "Killed":
            killed += 1
        elif status == "Survived":
            survived += 1
        elif status == "NoCoverage":
            no_coverage += 1
        elif status == "Timeout":
            timeout += 1
        elif status in {"CompileError", "RuntimeError", "Unknown"}:
            errors += 1
    value = 100.0 if total == 0 else round((killed * 100.0) / total, 2)
    return {
        "value": value,
        "total": total,
        "killed": killed,
        "survived": survived,
        "noCoverage": no_coverage,
        "timeout": timeout,
        "errors": errors,
    }


def _candidate_flaky(mutant: Dict[str, Any]) -> bool:
    return str(mutant.get("status", "Unknown")) in {"Survived", "NoCoverage", "Timeout"}


def _mark_baseline_and_ignore(
    mutants: List[Dict[str, Any]],
    *,
    baseline_fingerprints: set[str],
    ignore_ids: set[str],
    ignore_fingerprints: set[str],
) -> None:
    for mutant in mutants:
        fingerprint = str(mutant.get("fingerprint", "")).strip()
        mutant_id = str(mutant.get("id", "")).strip()
        baseline_match = fingerprint in baseline_fingerprints
        ignored = mutant_id in ignore_ids or fingerprint in ignore_fingerprints
        mutant["baselineMatch"] = baseline_match
        if ignored:
            mutant["status"] = "Ignored"
            mutant["statusReason"] = "ignored"


def _apply_flaky_reruns(
    *,
    adapter: str,
    workspace: Path,
    settings: Dict[str, Any],
    mutants: List[Dict[str, Any]],
    reruns: int,
) -> int:
    if reruns <= 0:
        return 0
    mutable_candidates = {str(item.get("fingerprint")): str(item.get("status")) for item in mutants if _candidate_flaky(item)}
    if not mutable_candidates:
        return 0

    flipped: set[str] = set()
    for _ in range(reruns):
        rerun = run_adapter(adapter, workspace, settings)
        report = rerun.get("report") if isinstance(rerun.get("report"), dict) else {}
        rerun_mutants = _normalize_mutants(report)
        rerun_status_by_fp = {str(item.get("fingerprint")): str(item.get("status")) for item in rerun_mutants}
        for fingerprint, original_status in mutable_candidates.items():
            new_status = rerun_status_by_fp.get(fingerprint)
            if new_status and new_status != original_status:
                flipped.add(fingerprint)

    for mutant in mutants:
        fingerprint = str(mutant.get("fingerprint", ""))
        if fingerprint in flipped:
            mutant["statusReason"] = "flaky"
    return len(flipped)


def _normalize_rule(raw: str) -> str:
    base = raw.strip().lower() or "mutation-finding"
    cleaned = "".join(ch if ch.isalnum() else "-" for ch in base).strip("-")
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned or "mutation-finding"


def _base_finding(rule: str, message: str) -> Finding:
    return {
        "severity": TIER_1,
        "rule": _normalize_rule(rule),
        "message": message,
        "confidence": "heuristic",
        "remediation_owner": "feature-team",
    }


def _mutation_message(mutant: Dict[str, Any], *, pre_existing: bool) -> str:
    location = mutant.get("location") if isinstance(mutant.get("location"), dict) else {}
    file_path = str(location.get("file") or "").strip()
    line = location.get("line")
    status = str(mutant.get("status", "Unknown"))
    mutator = str(mutant.get("mutatorName", "unknown"))
    prefix = "[pre-existing] " if pre_existing else ""
    if file_path and isinstance(line, int):
        return f"{prefix}{status} mutant from '{mutator}' at {file_path}:{line}."
    if file_path:
        return f"{prefix}{status} mutant from '{mutator}' at {file_path}."
    return f"{prefix}{status} mutant from '{mutator}'."


def _write_report(workspace: Path, payload: Dict[str, Any]) -> None:
    path = ensure_context_dir(workspace) / "mutation-report.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_summary(
    workspace: Path,
    *,
    mode: str,
    threshold: int,
    score: Dict[str, Any],
    adapter: str,
    mutants: List[Dict[str, Any]],
) -> None:
    path = ensure_context_dir(workspace) / "mutation-summary.md"
    flaky_count = sum(1 for item in mutants if str(item.get("statusReason", "")).strip().lower() == "flaky")
    baseline_count = sum(1 for item in mutants if bool(item.get("baselineMatch")))
    lines = [
        "# Mutation Summary",
        "",
        f"- Mode: `{mode}`",
        f"- Adapter: `{adapter}`",
        f"- Threshold: `{threshold}%`",
        f"- Score: `{score['value']}%`",
        f"- Scored Mutants: `{score['total']}`",
        f"- Killed: `{score['killed']}`",
        f"- Survived: `{score['survived']}`",
        f"- NoCoverage: `{score['noCoverage']}`",
        f"- Timeout: `{score['timeout']}`",
        f"- Errors: `{score['errors']}`",
        f"- Baseline Excluded: `{baseline_count}`",
        f"- Flaky Excluded: `{flaky_count}`",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def run(*, event: str, workspace: Path, policy: Dict[str, Any]) -> List[Finding]:
    settings = _resolve_settings(policy)
    if not _as_bool(settings.get("enabled"), default=False):
        return []
    if event not in _as_event_list(settings.get("events")):
        return []

    adapter = _select_runner(settings, workspace)
    if not adapter:
        return [
            _base_finding(
                "mutation-config-missing",
                "Mutation testing is enabled but no runnable adapter configuration was found.",
            )
        ]

    result = run_adapter(adapter, workspace, settings)
    if result.get("error"):
        return [
            _base_finding(
                "mutation-runner-error",
                f"Mutation adapter '{adapter}' failed: {result.get('error')}",
            )
        ]

    raw_report = result.get("report")
    report = raw_report if isinstance(raw_report, dict) else {}
    mutants = _normalize_mutants(report)

    baseline_path = _resolve_path(workspace, settings.get("baseline_file"), ".specify/context/mutation-baseline.json")
    baseline_fingerprints = _load_baseline_fingerprints(baseline_path)
    ignore_path = _resolve_path(workspace, settings.get("ignore_file"), ".specify/mutation-ignore.yml")
    ignore_ids, ignore_fingerprints = _load_ignore(ignore_path)
    _mark_baseline_and_ignore(
        mutants,
        baseline_fingerprints=baseline_fingerprints,
        ignore_ids=ignore_ids,
        ignore_fingerprints=ignore_fingerprints,
    )

    reruns = max(0, _as_int(settings.get("flaky_reruns"), 2))
    flaky_count = _apply_flaky_reruns(
        adapter=adapter,
        workspace=workspace,
        settings=settings,
        mutants=mutants,
        reruns=reruns,
    )

    mode = _normalize_mode(settings.get("mode"))
    threshold = _as_int(settings.get("strict_threshold"), 80) if mode == "strict" else _as_int(settings.get("threshold"), 60)
    score = _score(mutants)

    findings: List[Finding] = []
    for mutant in mutants:
        status = str(mutant.get("status", "Unknown"))
        if status not in {"Survived", "NoCoverage"}:
            continue
        is_flaky = str(mutant.get("statusReason", "")).strip().lower() == "flaky"
        if is_flaky:
            continue
        pre_existing = bool(mutant.get("baselineMatch"))
        rule = "mutation-no-coverage" if status == "NoCoverage" else "mutation-survived"
        findings.append(
            {
                "severity": TIER_1,
                "rule": rule,
                "message": _mutation_message(mutant, pre_existing=pre_existing),
                "confidence": "heuristic",
                "remediation_owner": "feature-team",
                "remediation": remediation_for(str(mutant.get("mutatorName", "")), status),
            }
        )

    if score["value"] < float(threshold):
        strict = mode == "strict"
        findings.append(
            {
                "severity": TIER_2 if strict else TIER_1,
                "rule": "mutation-score-below-threshold",
                "message": (
                    f"Mutation score {score['value']}% is below the configured "
                    f"{mode} threshold of {threshold}% (scored mutants: {score['total']})."
                ),
                "confidence": "deterministic" if strict else "heuristic",
                "remediation_owner": "feature-team",
                "remediation": "Increase killed mutants by adding behavior-focused assertions and boundary tests.",
            }
        )

    parse_error = str(result.get("parse_error") or "").strip()
    if parse_error:
        findings.append(
            _base_finding(
                "mutation-report-parse-failed",
                f"Mutation adapter '{adapter}' produced unreadable output: {parse_error}",
            )
        )

    exit_code = result.get("exit_code")
    if (
        isinstance(exit_code, int)
        and exit_code != 0
        and str(settings.get("exit_code_signals", "report")).strip().lower() == "violations"
        and score["total"] == 0
    ):
        findings.append(
            _base_finding(
                "mutation-command-failed",
                f"Mutation adapter '{adapter}' exited with code {exit_code} and no parseable report.",
            )
        )

    report_payload = {
        "schemaVersion": "1.0",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "tool": str(result.get("tool", adapter)),
        "adapter": adapter,
        "mode": mode,
        "threshold": threshold,
        "flakyReruns": reruns,
        "flakyExcluded": flaky_count,
        "score": score,
        "mutants": mutants,
    }
    _write_report(workspace, report_payload)
    _write_summary(workspace, mode=mode, threshold=threshold, score=score, adapter=adapter, mutants=mutants)
    return findings
