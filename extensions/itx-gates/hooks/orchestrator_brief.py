#!/usr/bin/env python3
"""Execution-brief and lazy-knowledge helpers for the gates orchestrator."""

from __future__ import annotations

import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Sequence

from orchestrator_common import (
    FINDING_MESSAGE_RE,
    FINDING_RULE_RE,
    FINDING_SEVERITY_RE,
    MARKDOWN_FILE_REF_RE,
    PACKAGE_ACTION_RE,
    PATTERN_FILENAME_RE,
    PLAIN_FILE_REF_RE,
    TASK_CHECKED_RE,
    TASK_UNCHECKED_RE,
    TIER_1,
    TIER_2,
    Finding,
    _extract_markdown_h2_sections,
    _find_plan_files,
    _find_task_files,
    _load_active_workstream_metadata,
    _resolve_legacy_work_class,
    _resolve_plan_policy_entry,
    _resolve_active_artifact_root_from_workflow_state,
    _split_frontmatter,
    _task_files_for_execution_brief_scope,
    _traceability_mode_id_fields,
    load_knowledge_manifest,
)


def _now_iso_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _plan_priority(path: Path) -> int:
    lower_name = path.name.lower()
    if "system-design-plan" in lower_name:
        return 0
    if "patch-plan" in lower_name:
        return 1
    if "refactor-plan" in lower_name:
        return 2
    if "bugfix-report" in lower_name:
        return 3
    if "migration-plan" in lower_name:
        return 4
    if "tooling-plan" in lower_name:
        return 5
    if "spike-note" in lower_name:
        return 6
    if "modify-plan" in lower_name:
        return 7
    if "hotfix-report" in lower_name:
        return 8
    if "deprecate-plan" in lower_name:
        return 9
    return 99


def _resolve_plan_for_execution_brief(workspace: Path) -> Path | None:
    active_artifact_root = _resolve_active_artifact_root_from_workflow_state(workspace)
    if active_artifact_root is not None:
        scoped: List[Path] = []
        for plan_file in _find_plan_files(workspace):
            try:
                plan_file.relative_to(active_artifact_root)
            except ValueError:
                continue
            scoped.append(plan_file)
        if scoped:
            return sorted(scoped, key=lambda p: (_plan_priority(p), str(p)))[0]
        return None
    all_plans = sorted(_find_plan_files(workspace), key=lambda p: (_plan_priority(p), str(p)))
    if len(all_plans) == 1:
        return all_plans[0]
    return None


def _infer_workstream_context_from_plan(workspace: Path, plan_path: Path) -> dict[str, str]:
    metadata = _load_active_workstream_metadata(workspace)
    artifact_root_path = _resolve_active_artifact_root_from_workflow_state(workspace)
    if artifact_root_path is None:
        try:
            rel_plan = plan_path.relative_to(workspace)
        except ValueError:
            rel_plan = None
        if rel_plan is not None and len(rel_plan.parts) >= 2 and rel_plan.parts[0] == "specs":
            artifact_root_path = plan_path.parent

    artifact_root = "workspace"
    rel_artifact_root: Path | None = None
    if artifact_root_path is not None:
        try:
            rel_artifact_root = artifact_root_path.relative_to(workspace)
        except ValueError:
            rel_artifact_root = None
        if rel_artifact_root is not None:
            artifact_root = str(rel_artifact_root)

    workstream_id = metadata.get("workstream_id")
    feature = metadata.get("feature") or metadata.get("parent_feature")
    parent_feature = metadata.get("parent_feature")

    if rel_artifact_root is not None and rel_artifact_root.parts and rel_artifact_root.parts[0] == "specs":
        spec_parts = rel_artifact_root.parts[1:]
        if len(spec_parts) >= 3 and spec_parts[1] == "modifications":
            parent_feature = parent_feature or spec_parts[0]
            feature = feature or spec_parts[0]
            workstream_id = workstream_id or spec_parts[-1]
        elif spec_parts:
            workstream_id = workstream_id or spec_parts[-1]
            feature = feature or spec_parts[0]

    if workstream_id is None:
        workstream_id = plan_path.stem
    if feature is None:
        feature = parent_feature or workstream_id
    if parent_feature is None:
        parent_feature = "none"

    return {
        "feature": feature,
        "workstream_id": workstream_id,
        "artifact_root": artifact_root,
        "parent_feature": parent_feature,
    }


def _infer_feature_from_plan(workspace: Path, plan_path: Path) -> str:
    context = _infer_workstream_context_from_plan(workspace, plan_path)
    feature = context.get("feature")
    if feature:
        return feature
    try:
        rel = plan_path.relative_to(workspace)
    except ValueError:
        return "workspace"
    if len(rel.parts) >= 3 and rel.parts[0] == "specs":
        return rel.parts[1]
    return "workspace"


def _parse_compact_lines(section_body: str, *, limit: int = 8) -> List[str]:
    lines: List[str] = []
    for raw_line in section_body.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped.startswith("|") or stripped.startswith(">"):
            continue
        stripped = re.sub(r"^\d+\.\s+", "", stripped)
        stripped = re.sub(r"^-+\s+", "", stripped)
        stripped = re.sub(r"^\[[ xX]\]\s+", "", stripped)
        if stripped:
            lines.append(stripped)
        if len(lines) >= limit:
            break
    return lines


def _extract_scope(section_body: str) -> tuple[List[str], List[str]]:
    in_scope: List[str] = []
    out_scope: List[str] = []
    for line in _parse_compact_lines(section_body, limit=20):
        lower = line.lower()
        if "out of scope" in lower or lower.startswith("out:") or lower.startswith("non-scope"):
            cleaned = re.sub(r"^(out:|out of scope:|non-scope:)\s*", "", line, flags=re.IGNORECASE).strip()
            if cleaned:
                out_scope.append(cleaned)
            continue
        if lower.startswith("in:") or "in scope" in lower:
            cleaned = re.sub(r"^(in:|in scope:)\s*", "", line, flags=re.IGNORECASE).strip()
            if cleaned:
                in_scope.append(cleaned)
            continue
        in_scope.append(line)
    return in_scope[:4], out_scope[:4]


def _extract_file_refs(text: str) -> List[str]:
    refs = [*MARKDOWN_FILE_REF_RE.findall(text), *PLAIN_FILE_REF_RE.findall(text)]
    normalized: List[str] = []
    seen: set[str] = set()
    for ref in refs:
        cleaned = ref.strip().strip(".,)")
        if not cleaned:
            continue
        if cleaned.startswith("./"):
            cleaned = cleaned[2:]
        if cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)
    return normalized


def _parse_gate_feedback_summaries(gate_feedback_text: str, *, limit: int = 5) -> tuple[List[str], bool]:
    summaries: List[str] = []
    has_tier2 = False
    blocks = gate_feedback_text.split("## Finding ")
    for block in blocks[1:]:
        sev_match = FINDING_SEVERITY_RE.search(block)
        rule_match = FINDING_RULE_RE.search(block)
        msg_match = FINDING_MESSAGE_RE.search(block)
        if not (sev_match and rule_match and msg_match):
            continue
        severity = sev_match.group(1).strip().lower()
        rule = rule_match.group(1).strip()
        message = msg_match.group(1).strip()
        if severity == TIER_2:
            has_tier2 = True
        summaries.append(f"[{severity}] {rule}: {message}")
        if len(summaries) >= limit:
            break
    return summaries, has_tier2


def _task_lines_for_brief(task_files: Sequence[Path]) -> tuple[List[str], List[str], List[str]]:
    unchecked: List[str] = []
    checked: List[str] = []
    file_refs: List[str] = []
    for path in task_files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for match in TASK_UNCHECKED_RE.findall(text):
            unchecked.append(match.strip())
        for match in TASK_CHECKED_RE.findall(text):
            checked.append(match.strip())
        file_refs.extend(_extract_file_refs(text))
    return unchecked, checked, file_refs


def _format_execution_brief(
    *,
    feature: str,
    workstream_id: str,
    artifact_root: str,
    parent_feature: str,
    work_class: str,
    traceability_mode: str,
    traceability_ref: str,
    domain: str,
    knowledge_mode: str,
    generated_from: List[str],
    objective: List[str],
    in_scope: List[str],
    out_scope: List[str],
    file_refs: List[str],
    selected_patterns: List[str],
    targeted_overlays: List[str],
    active_context: List[str],
    constraints: List[str],
    risks: List[str],
    verification: List[str],
    next_actions: List[str],
    approval_holds: List[str],
) -> str:
    lines = [
        "---",
        'schema_version: "1.0"',
        f'feature: "{feature}"',
        f'workstream_id: "{workstream_id}"',
        f'artifact_root: "{artifact_root}"',
        f'parent_feature: "{parent_feature}"',
        f'work_class: "{work_class}"',
        f'traceability_mode: "{traceability_mode}"',
        f'traceability_ref: "{traceability_ref}"',
        f'domain: "{domain}"',
        f'knowledge_mode: "{knowledge_mode}"',
        "generated_from:",
    ]
    for item in generated_from:
        lines.append(f'  - "{item}"')
    lines.extend(
        [
            f'generated_at: "{_now_iso_utc()}"',
            "---",
            "",
            "# Execution Brief",
            "",
            "## Behavior Overlay",
            "- Think Before Coding: restate objective, constraints, verification target.",
            "- Simplicity First: choose the smallest change that satisfies the brief.",
            "- Surgical Changes: stay within listed scope and avoid unrelated edits.",
            "- Goal-Driven Execution: verify against named tests and gate signals.",
            "",
            "## Objective",
        ]
    )
    lines.extend([f"- {item}" for item in objective[:3]] or ["- Clarify objective from source plan before implementation."])
    lines.extend(["", "## Scope"])
    lines.extend([f"- In: {item}" for item in (in_scope[:4] or ["Scope not explicitly declared; use listed files/modules as boundary."])])
    lines.extend([f"- Out: {item}" for item in out_scope[:4]])
    if file_refs:
        lines.extend(["", "## Files/Modules In Scope"])
        lines.extend([f"- {item}" for item in file_refs[:10]])
    if selected_patterns:
        lines.extend(["", "## Selected Patterns To Load"])
        lines.extend([f"- {item}" for item in selected_patterns[:8]])
    if targeted_overlays:
        lines.extend(["", "## Targeted Micro-Overlays"])
        lines.extend([f"- {item}" for item in targeted_overlays[:8]])
    lines.extend(["", "## Active Context"])
    lines.extend(
        [f"- {item}" for item in active_context[:4]]
        or ["- Use this execution brief as the active context snapshot for the current workstream."]
    )
    if constraints:
        lines.extend(["", "## Constraints and Invariants"])
        lines.extend([f"- {item}" for item in constraints[:8]])
    if risks:
        lines.extend(["", "## Active Risks and Gate Signals"])
        lines.extend([f"- {item}" for item in risks[:5]])
    lines.extend(["", "## Traceability"])
    lines.append(f"- Mode: {traceability_mode}")
    lines.append(f"- Reference: {traceability_ref}")
    lines.extend(["", "## Verification Targets"])
    lines.extend([f"- {item}" for item in verification[:8]] or ["- Preserve existing gate checks and ensure regression coverage for changed behavior paths."])
    if next_actions:
        lines.extend(["", "## Next Actions"])
        lines.extend([f"- {item}" for item in next_actions[:5]])
    if approval_holds:
        lines.extend(["", "## Human Approval Required"])
        lines.extend([f"- {item}" for item in approval_holds[:4]])
    lines.append("")
    return "\n".join(lines)


def _execution_brief_triggers(
    *,
    work_class: str,
    plan_text: str,
    file_refs: Sequence[str],
    unchecked_tasks: Sequence[str],
) -> List[str]:
    triggers: List[str] = []
    combined_text = "\n".join([plan_text, *unchecked_tasks])

    if work_class == "refactor":
        if any(marker in combined_text.lower() for marker in {"major", "cross-module", "multi-module", "large-scale"}):
            triggers.append("major-refactor")

    if PACKAGE_ACTION_RE.search(combined_text):
        triggers.append("package-install-remove")

    high_risk_prefixes = (
        ".github/workflows/",
        "extensions/itx-gates/hooks/orchestrator.py",
        "extensions/itx-gates/hooks/orchestrator_common.py",
        "extensions/itx-gates/hooks/orchestrator_brief.py",
        "extensions/itx-gates/hooks/orchestrator_runtime.py",
        ".specify/extensions/",
        "scripts/itx_init.py",
        "scripts/patch.py",
        "scripts/release.py",
        "docker-compose",
        "Dockerfile",
        "migrations/",
    )
    if any(any(ref.startswith(prefix) for prefix in high_risk_prefixes) for ref in file_refs):
        triggers.append("high-risk-ops-change")
    return list(dict.fromkeys(triggers))


def _derive_targeted_overlays(
    *,
    work_class: str,
    plan_text: str,
    selected_patterns: Sequence[str],
    file_refs: Sequence[str],
) -> List[str]:
    overlays: List[str] = []
    lowered = plan_text.lower()
    selected_set = {item.lower() for item in selected_patterns}
    ref_text = "\n".join(file_refs).lower()

    acl_keywords = (
        "third-party",
        "third party",
        "vendor",
        "legacy",
        "external api",
        "external service",
    )
    if "adapter-anti-corruption.md" in selected_set or any(keyword in lowered for keyword in acl_keywords):
        overlays.append(
            "ACL boundary: keep vendor DTOs/errors inside adapters and map to internal contracts before domain use."
        )

    auth_keywords = (
        "oauth",
        "oidc",
        "jwt",
        "token",
        "secret",
        "credential",
        "password",
        "api key",
        "authentication",
        "authorization",
        "authz",
    )
    if any(keyword in lowered for keyword in auth_keywords):
        overlays.append(
            "Security/auth-secrets: validate auth claims and avoid hardcoded or logged secrets."
        )

    owasp_keywords = (
        "public api",
        "untrusted input",
        "sql",
        "nosql",
        "xss",
        "ssrf",
        "injection",
        "idor",
        "broken access control",
        "access control",
    )
    if any(keyword in lowered for keyword in owasp_keywords):
        overlays.append(
            "Security/OWASP: enforce input validation, least-privilege access control, and injection-safe data access."
        )

    rate_limit_keywords = ("rate limit", "throttle", "ddos", "gateway", "burst", "abuse")
    if any(keyword in lowered for keyword in rate_limit_keywords) or (
        "public api" in lowered and ("login" in lowered or "auth" in lowered)
    ):
        overlays.append(
            "Security/rate-limiting: define bounded request policies for sensitive or public endpoints."
        )

    modify_like_patch = work_class in {"patch", "tooling", "modify"} and any(
        marker in lowered for marker in ("modify", "behavior change", "change existing")
    )
    behavior_change_markers = (
        "modify existing behavior",
        "functional change",
        "user-visible change",
    )
    behavior_adjacent_refactor = work_class == "refactor" and any(marker in lowered for marker in behavior_change_markers)
    if work_class == "bugfix" or behavior_adjacent_refactor or modify_like_patch:
        overlays.append(
            "TDD loop: prefer red-green-refactor for changed business behavior before broad implementation edits."
        )

    if any(marker in lowered for marker in ("/review", "review.run", "review phase")):
        overlays.append("Review overlay: produce severity-ordered findings and avoid feature implementation in review.")
    if any(marker in lowered for marker in ("/cleanup", "cleanup.run", "cleanup phase")):
        overlays.append("Janitor overlay: keep cleanup evidence-driven and request approval before destructive removal.")

    if any(token in ref_text for token in ("vendor", "third_party", "legacy")):
        if not any(item.startswith("ACL boundary:") for item in overlays):
            overlays.append(
                "ACL boundary: keep vendor DTOs/errors inside adapters and map to internal contracts before domain use."
            )

    return list(dict.fromkeys(overlays))


def _append_pre_action_audit_log(
    *,
    workspace: Path,
    feature: str,
    plan_path: Path,
    triggers: Sequence[str],
    file_refs: Sequence[str],
    objective: Sequence[str],
    verification_targets: Sequence[str],
) -> None:
    if not triggers:
        return
    log_path = workspace / ".specify" / "context" / "audit-log.md"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    existing = log_path.read_text(encoding="utf-8", errors="ignore") if log_path.exists() else ""

    lines: List[str] = []
    for trigger in triggers:
        signature = f"{feature}:{plan_path.name}:{trigger}"
        if signature in existing:
            continue
        lines.extend(
            [
                f"## Pre-Action Audit ({_now_iso_utc()})",
                f"- Signature: `{signature}`",
                f"- Action: `{trigger}`",
                f"- Why: `{objective[0] if objective else 'Planned high-risk change requires explicit pre-action record.'}`",
                f"- Expected Outcome: `{'; '.join(verification_targets[:2]) or 'Preserve expected behavior with gate and regression evidence.'}`",
                f"- Trigger Reason: high-risk action detected from planning artifacts",
                f"- Intended Scope: `{', '.join(file_refs[:8]) or plan_path.name}`",
                "- Rollback Note: revert scoped edits and rerun gate checks before retry",
                f"- Verification Target: `{'; '.join(verification_targets[:3]) or 'gate + regression checks'}`",
                "",
            ]
        )
    if lines:
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write("\n".join(lines))


def _extract_selected_patterns(plan_text: str, known_filenames: set[str] | None = None) -> tuple[set[str] | None, bool]:
    block_re = re.compile(r"<!--\s*selected_patterns\s*:\s*(.*?)\s*-->", re.IGNORECASE | re.DOTALL)
    match = block_re.search(plan_text)
    if match:
        raw = match.group(1).strip()
        if raw.lower() == "none":
            return set(), False
        names = {name.strip().lower() for name in raw.split(",") if name.strip()}
        return names, False

    found = {name.lower() for name in PATTERN_FILENAME_RE.findall(plan_text)}
    if known_filenames is not None:
        found = {name for name in found if name in known_filenames}
    return (found if found else None), True


def _sync_lazy_knowledge(config: Dict[str, Any], workspace: Path, policy: Dict[str, Any]) -> List[Finding]:
    knowledge = config.get("knowledge") or {}
    if str(knowledge.get("mode", "eager")).strip().lower() != "lazy":
        return []

    plan_files = _find_plan_files(workspace)
    if not plan_files:
        return []

    manifest = load_knowledge_manifest(workspace)
    raw_manifest_files = manifest.get("files")
    if raw_manifest_files is not None and not isinstance(raw_manifest_files, dict):
        sys.stderr.write("[itx-gates] Warning: malformed knowledge-manifest.json: 'files' must be a mapping; ignoring.\n")
        manifest_files: Dict[str, Dict[str, Any]] = {}
    else:
        manifest_files = raw_manifest_files or {}
    known_pattern_filenames = {name.lower() for name in manifest_files}
    known_names_for_fallback = known_pattern_filenames or None

    all_requested: set[str] = set()
    has_any_selection = False
    used_regex_fallback = False
    for plan_file in plan_files:
        text = plan_file.read_text(encoding="utf-8", errors="ignore")
        policy_entry, _ = _resolve_plan_policy_entry(plan_file, policy)
        selection_mode = str((policy_entry or {}).get("pattern_selection", "optional")).lower()

        selected, fallback_used = _extract_selected_patterns(text, known_names_for_fallback)
        used_regex_fallback = used_regex_fallback or fallback_used
        if selected is not None:
            has_any_selection = True
            all_requested.update(selected)
        elif selection_mode == "required":
            return [
                {
                    "severity": TIER_1,
                    "rule": "knowledge-pattern-selection-missing",
                    "message": (
                        "Lazy knowledge mode is active but no pattern filenames were selected in the plan. "
                        "Add a structured selection block (<!-- selected_patterns: file.md, ... -->) "
                        "or reference filenames from .specify/pattern-index.md."
                    ),
                }
            ]

    if not has_any_selection:
        return []
    if not all_requested:
        if used_regex_fallback:
            sys.stderr.write(
                "[itx-gates] Warning: detected deprecated inline markdown filename fallback for pattern "
                "selection. Prefer structured selection blocks: <!-- selected_patterns: file.md, ... -->\n"
            )
        return []

    store_root = workspace / ".specify" / ".knowledge-store"
    target_roots = {
        "patterns": workspace / ".specify" / "patterns",
        "design-patterns": workspace / ".specify" / "design-patterns",
        "anti-patterns": workspace / ".specify" / "anti-patterns",
    }

    available: Dict[str, tuple[str, Path]] = {}
    for name_key, entry in manifest_files.items():
        if not isinstance(name_key, str) or not isinstance(entry, dict):
            sys.stderr.write("[itx-gates] Warning: malformed knowledge-manifest.json entry ignored.\n")
            continue
        source_raw = entry.get("source", "")
        category = str(entry.get("category", "")).strip()
        if not isinstance(source_raw, str):
            sys.stderr.write(f"[itx-gates] Warning: malformed manifest source for '{name_key}' ignored.\n")
            continue
        source = Path(source_raw)
        if source.exists() and category in target_roots:
            available[name_key.lower()] = (category, source)

    for category in target_roots:
        source_dir = store_root / category
        if not source_dir.exists():
            continue
        for file_path in source_dir.glob("*.md"):
            key = file_path.name.lower()
            if key not in available:
                available[key] = (category, file_path)

    unresolved = sorted(name for name in all_requested if name not in available)
    findings: List[Finding] = []
    if unresolved:
        findings.append(
            {
                "severity": TIER_1,
                "rule": "knowledge-pattern-unresolved",
                "message": "Some plan-selected patterns could not be resolved: " + ", ".join(unresolved),
            }
        )

    promoted: list[str] = []
    for name in sorted(all_requested):
        resolved = available.get(name)
        if resolved is None:
            continue
        category, source_path = resolved
        target_dir = target_roots[category]
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / source_path.name
        try:
            if source_path.resolve() != target_path.resolve():
                shutil.copy2(source_path, target_path)
        except OSError:
            if str(source_path) != str(target_path):
                shutil.copy2(source_path, target_path)
        promoted.append(name)

    if promoted:
        sys.stdout.write(f"[itx-gates] Lazy knowledge: promoted {len(promoted)} pattern(s): {', '.join(promoted)}\n")
    if used_regex_fallback:
        sys.stderr.write(
            "[itx-gates] Warning: detected deprecated inline markdown filename fallback for pattern "
            "selection. Prefer structured selection blocks: <!-- selected_patterns: file.md, ... -->\n"
        )
    return findings


def _generate_execution_brief(workspace: Path, config: Dict[str, Any], policy: Dict[str, Any]) -> None:
    brief_path = workspace / ".specify" / "context" / "execution-brief.md"
    plan_path = _resolve_plan_for_execution_brief(workspace)
    if plan_path is None:
        if brief_path.exists():
            brief_path.unlink()
        return

    plan_text = plan_path.read_text(encoding="utf-8", errors="ignore")
    frontmatter, _ = _split_frontmatter(plan_text)
    sections = _extract_markdown_h2_sections(plan_text)
    _, resolved_work_class = _resolve_plan_policy_entry(plan_path, policy)
    work_class = resolved_work_class or _resolve_legacy_work_class(plan_path, policy) or "unknown"
    traceability_mode = "none"
    traceability_ref = "n/a"
    mode_to_id_field = _traceability_mode_id_fields(policy)
    raw_traceability_mode = frontmatter.get("traceability_mode")
    if isinstance(raw_traceability_mode, str) and raw_traceability_mode.strip():
        traceability_mode = raw_traceability_mode.strip().lower()
        id_field = mode_to_id_field.get(traceability_mode)
        if id_field:
            raw_ref = frontmatter.get(id_field)
            if isinstance(raw_ref, str) and raw_ref.strip():
                traceability_ref = raw_ref.strip()
    workstream_context = _infer_workstream_context_from_plan(workspace, plan_path)
    feature = workstream_context["feature"]
    workstream_id = workstream_context["workstream_id"]
    artifact_root = workstream_context["artifact_root"]
    parent_feature = workstream_context["parent_feature"]
    domain = str(config.get("domain", "base")).strip() or "base"
    knowledge_mode = str((config.get("knowledge") or {}).get("mode", "eager")).strip().lower() or "eager"

    manifest = load_knowledge_manifest(workspace)
    manifest_files = manifest.get("files") if isinstance(manifest.get("files"), dict) else {}
    known_names = {str(name).lower() for name in manifest_files} if isinstance(manifest_files, dict) else None
    selected, _ = _extract_selected_patterns(plan_text, known_names or None)
    selected_patterns = sorted(selected) if selected is not None else []
    if selected == set():
        selected_patterns = ["none"]

    objective: List[str] = []
    for heading in (
        "## 1. Problem Statement",
        "## 1. Goal",
        "## 1. Symptom",
        "## 1. Migration Goal",
        "## 1. Question",
    ):
        body = sections.get(heading)
        if body:
            objective.extend(_parse_compact_lines(body, limit=3))
            break

    in_scope: List[str] = []
    out_scope: List[str] = []
    for scope_heading in (
        "## 2. Scope / Non-Scope",
        "## 2. Files / Modules Affected",
        "## 2. Reproduction",
        "## 2. Current State / Target State",
    ):
        body = sections.get(scope_heading)
        if not body:
            continue
        scoped_in, scoped_out = _extract_scope(body)
        in_scope.extend(scoped_in)
        out_scope.extend(scoped_out)
        if in_scope:
            break

    file_refs: List[str] = []
    file_scope_body = sections.get("## 2. Files / Modules Affected")
    if file_scope_body:
        file_refs.extend(_extract_file_refs(file_scope_body))
    scope_body = sections.get("## 2. Scope / Non-Scope")
    if scope_body:
        file_refs.extend(_extract_file_refs(scope_body))

    constraints: List[str] = []
    for heading in (
        "## 3. Invariants to Preserve",
        "## 4. Public Contract Impact",
        "## 5. Behavioral Equivalence Strategy",
        "## 3. Expected Behavior",
        "## 6. Fix Strategy",
        "## 4. Compatibility Window",
        "## 5. Rollback Strategy",
        "## 2. Constraints",
    ):
        body = sections.get(heading)
        if body:
            constraints.extend(_parse_compact_lines(body, limit=3))

    verification: List[str] = []
    for heading in (
        "## 13. Test Strategy",
        "## 6. Regression Strategy",
        "## 5. Regression Testing",
        "## 4. Regression Test Target",
        "## 7. Regression and Verification",
    ):
        body = sections.get(heading)
        if body:
            verification.extend(_parse_compact_lines(body, limit=4))

    risk_lines: List[str] = []
    for heading, body in sections.items():
        if "risk" in heading.lower():
            risk_lines.extend(_parse_compact_lines(body, limit=3))

    task_files = _task_files_for_execution_brief_scope(workspace, _find_task_files(workspace), plan_path)
    unchecked_tasks, _, task_file_refs = _task_lines_for_brief(task_files)
    file_refs.extend(task_file_refs)
    next_actions = unchecked_tasks[:5]
    if not next_actions and risk_lines:
        next_actions = [f"Mitigate risk: {item}" for item in risk_lines[:3]]

    gate_feedback_path = workspace / ".specify" / "context" / "gate_feedback.md"
    gate_summaries: List[str] = []
    has_tier2 = False
    if gate_feedback_path.exists():
        gate_feedback_text = gate_feedback_path.read_text(encoding="utf-8", errors="ignore")
        gate_summaries, has_tier2 = _parse_gate_feedback_summaries(gate_feedback_text, limit=5)
    risk_lines.extend(gate_summaries)

    approval_holds: List[str] = []
    if has_tier2:
        approval_holds.append("Outstanding Tier 2 gate findings require explicit human decision.")

    assumptions: List[str] = []
    for heading, body in sections.items():
        heading_lower = heading.lower()
        if "assumption" in heading_lower:
            assumptions.extend(_parse_compact_lines(body, limit=3))

    open_questions: List[str] = []
    for heading, body in sections.items():
        heading_lower = heading.lower()
        if "open question" in heading_lower:
            open_questions.extend(_parse_compact_lines(body, limit=3))

    active_context: List[str] = [
        "This execution brief is the active context snapshot for this workstream (no separate memory-bank context file)."
    ]
    active_context.extend([f"Working assumption: {item}" for item in assumptions[:2]])
    active_context.extend([f"Open question: {item}" for item in open_questions[:2]])

    targeted_overlays = _derive_targeted_overlays(
        work_class=work_class,
        plan_text=plan_text,
        selected_patterns=selected_patterns,
        file_refs=file_refs,
    )

    generated_from = ["plan"]
    if task_files:
        generated_from.append("tasks")
    if gate_feedback_path.exists():
        generated_from.append("gate_feedback")

    dedup_files = list(dict.fromkeys(file_refs))
    dedup_constraints = list(dict.fromkeys(constraints))
    dedup_risks = list(dict.fromkeys(risk_lines))
    dedup_verification = list(dict.fromkeys(verification))

    brief_text = _format_execution_brief(
        feature=feature,
        workstream_id=workstream_id,
        artifact_root=artifact_root,
        parent_feature=parent_feature,
        work_class=work_class,
        traceability_mode=traceability_mode,
        traceability_ref=traceability_ref,
        domain=domain,
        knowledge_mode=knowledge_mode,
        generated_from=generated_from,
        objective=objective,
        in_scope=in_scope,
        out_scope=out_scope,
        file_refs=dedup_files,
        selected_patterns=selected_patterns,
        targeted_overlays=targeted_overlays,
        active_context=active_context,
        constraints=dedup_constraints,
        risks=dedup_risks,
        verification=dedup_verification,
        next_actions=next_actions,
        approval_holds=approval_holds,
    )

    brief_path.parent.mkdir(parents=True, exist_ok=True)
    brief_path.write_text(brief_text, encoding="utf-8")

    triggers = _execution_brief_triggers(
        work_class=work_class,
        plan_text=plan_text,
        file_refs=dedup_files,
        unchecked_tasks=unchecked_tasks,
    )
    _append_pre_action_audit_log(
        workspace=workspace,
        feature=workstream_id,
        plan_path=plan_path,
        triggers=triggers,
        file_refs=dedup_files,
        objective=objective,
        verification_targets=dedup_verification,
    )
