#!/usr/bin/env python3
"""Patch an already-bootstrapped itexus-spec-kit workspace.

Applies incremental updates from the kit source to a live project without
re-running the full bootstrap.  Safe to run multiple times (idempotent).

Files are split into two categories:

  Kit-owned:  Extension code, Cursor rules, runner adapter — always overwritten.
  Editable:   constitution.md, policy.yml, knowledge-base docs — may have been
              modified by /speckit.constitution or manual edits.  New versions
              are written as *.kit-update side-files for manual merge.  Use
              --force to overwrite editable files directly (a .patch-backup is
              created first).

Agent scaffolding (optional):

  --retarget-ai: run ``specify init`` in the workspace, then restore preserved
  Itexus/user paths (constitution, pattern-index, extensions, etc.), then patch,
  then re-sync community extensions for the retargeted agent.
  --add-ai: run ``specify init`` in a temp dir and merge only that agent's
  artifact tree into the workspace (best-effort multi-agent), then patch, then
  re-sync community extensions for the added agent (use
  --skip-add-ai-extension-sync to opt out).

Usage:
    python scripts/patch.py --workspace /path/to/project
    python scripts/patch.py --workspace /path/to/project --force
    python scripts/patch.py --workspace /path/to/project --retarget-ai claude
    python scripts/patch.py --workspace /path/to/project --add-ai kiro-cli
    python scripts/patch.py --workspace /path/to/project --kit-root /path/to/itexus-spec-kit
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Tuple

import yaml

from itx_specify import (
    LOCAL_KIT_EXTENSIONS,
    agent_artifact_folder,
    detect_specify_cli,
    install_community_extensions,
    load_spec_kit_ref,
    map_agent_for_specify,
    materialize_extension_skills_for_agent,
    materialize_extension_workflows_for_agent,
    mirror_registry_commands,
    run_specify,
    specify_init_argv,
    validate_init_agent,
)


def log(message: str) -> None:
    print(f"[itx-patch] {message}")


def warn(message: str) -> None:
    print(f"[itx-patch] WARNING: {message}")


def copy_file(src: Path, dst: Path) -> bool:
    """Copy src to dst, creating parent directories. Returns True if updated."""
    if not src.exists():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and dst.read_bytes() == src.read_bytes():
        return False
    shutil.copy2(src, dst)
    return True


def copy_tree(src: Path, dst: Path) -> int:
    """Recursively copy src tree into dst. Returns count of updated files."""
    if not src.exists():
        return 0
    count = 0
    for item in src.rglob("*"):
        if item.is_dir():
            continue
        rel = item.relative_to(src)
        if copy_file(item, dst / rel):
            count += 1
    return count


def _safe_update_file(src: Path, dst: Path, force: bool) -> str | None:
    """Handle a user-editable file safely.

    Returns a status string describing what happened, or None if no action was
    needed (file already matches the kit version or a .kit-update already exists).
    """
    if not src.exists():
        return None

    src_bytes = src.read_bytes()
    dst.parent.mkdir(parents=True, exist_ok=True)

    if not dst.exists():
        shutil.copy2(src, dst)
        return "created"

    if dst.read_bytes() == src_bytes:
        return None

    if force:
        backup = dst.with_suffix(dst.suffix + ".patch-backup")
        shutil.copy2(dst, backup)
        shutil.copy2(src, dst)
        return f"overwritten (backup: {backup.name})"

    kit_update = dst.with_suffix(dst.suffix + ".kit-update")
    if kit_update.exists() and kit_update.read_bytes() == src_bytes:
        return None
    shutil.copy2(src, kit_update)
    return f"new version staged as {kit_update.name}"


_GOVERNANCE_FILES = (
    "decision-authority.yml",
    "input-contracts.yml",
    "notification-events.yml",
    "workflow-state-schema.yml",
)
_KB_DOC_NAMES = ("workflow-and-gates.md", "index.md", "domain-selection.md", "delivery-mechanics.md")


def _retarget_relative_paths(workspace: Path, refresh_templates: bool) -> list[Path]:
    paths: list[Path] = [
        Path(".specify/constitution.md"),
        Path(".specify/memory/constitution.md"),
        Path(".specify/pattern-index.md"),
        Path(".specify/policy.yml"),
        Path(".specify/extensions"),
    ]
    for name in _GOVERNANCE_FILES:
        paths.append(Path(".specify") / name)
    kb = workspace / "docs" / "knowledge-base"
    for name in _KB_DOC_NAMES:
        paths.append(Path("docs/knowledge-base") / name)
    if not refresh_templates:
        paths.append(Path(".specify/templates"))
    return paths


def _remove_path(path: Path) -> None:
    if path.is_file() or path.is_symlink():
        path.unlink(missing_ok=True)
    elif path.is_dir():
        shutil.rmtree(path, ignore_errors=False)


def _copy_into_backup(src: Path, dst: Path) -> None:
    if src.is_file() or src.is_symlink():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    elif src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)


def _snapshot_retarget_paths(
    workspace: Path, backup: Path, refresh_templates: bool
) -> list[Path]:
    saved: list[Path] = []
    for rel in _retarget_relative_paths(workspace, refresh_templates):
        src = workspace / rel
        if src.exists():
            _copy_into_backup(src, backup / rel)
            saved.append(rel)
    return saved


def _restore_snapshot(workspace: Path, backup: Path, saved: list[Path]) -> None:
    for rel in saved:
        src = backup / rel
        dst = workspace / rel
        if dst.exists():
            _remove_path(dst)
        if not src.exists():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_file() or src.is_symlink():
            shutil.copy2(src, dst)
        elif src.is_dir():
            shutil.copytree(src, dst, dirs_exist_ok=True)


def _load_config_dict(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, yaml.YAMLError):
        return {}


def _write_config_dict(path: Path, data: dict) -> None:
    path.write_text(
        yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def update_agents_primary(workspace: Path, canonical: str) -> None:
    cfg_path = workspace / ".itx-config.yml"
    data = _load_config_dict(cfg_path)
    agents = data.get("agents")
    if not isinstance(agents, dict):
        agents = {}
        data["agents"] = agents
    agents["primary"] = canonical
    _write_config_dict(cfg_path, data)


def append_agents_installed(workspace: Path, canonical: str) -> None:
    cfg_path = workspace / ".itx-config.yml"
    data = _load_config_dict(cfg_path)
    agents = data.get("agents")
    if not isinstance(agents, dict):
        agents = {}
        data["agents"] = agents
    inst = agents.get("installed")
    if not isinstance(inst, list):
        inst = []
    if canonical not in inst:
        inst.append(canonical)
    agents["installed"] = inst
    _write_config_dict(cfg_path, data)


def primary_agent_from_config(workspace: Path) -> str | None:
    cfg_path = workspace / ".itx-config.yml"
    data = _load_config_dict(cfg_path)
    agents = data.get("agents")
    if not isinstance(agents, dict):
        return None
    raw = agents.get("primary")
    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        return map_agent_for_specify(raw.strip())
    except ValueError:
        return None


def copy_agent_tree_from_staging(
    staging: Path, workspace: Path, canonical: str, generic_commands_dir: str | None
) -> bool:
    """Copy agent-owned scaffold from a fresh specify init tree into workspace."""
    if canonical == "generic":
        gdir = (generic_commands_dir or "").strip().strip("/")
        if not gdir:
            warn("--generic-commands-dir is required for generic")
            return False
        src = staging / gdir
        if not src.exists():
            warn(f"Staging missing generic commands dir: {gdir}")
            return False
        dst = workspace / gdir
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst, dirs_exist_ok=True)
        return True

    folder = agent_artifact_folder(canonical)
    if not folder:
        warn(f"No artifact folder known for integration {canonical!r}")
        return False
    rel = folder.rstrip("/")
    src = staging / rel
    if not src.exists():
        warn(f"Staging missing agent tree: {rel}")
        return False
    dst = workspace / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, dst, dirs_exist_ok=True)
    return True


def retarget_ai_workspace(
    workspace: Path,
    canonical_agent: str,
    generic_commands_dir: str | None,
    *,
    refresh_templates: bool,
    quiet: bool,
) -> None:
    spec_cli = detect_specify_cli()
    if not spec_cli:
        raise RuntimeError(
            "retarget-ai requires specify or uvx on PATH (spec-kit binary is not supported for this operation)."
        )
    if canonical_agent == "generic":
        raise RuntimeError("Use specify init manually for generic, or pass a concrete --retarget-ai integration key.")

    if not (workspace / ".specify").is_dir():
        raise RuntimeError(f"Not a specify workspace (missing .specify/): {workspace}")

    spec_kit_ref = load_spec_kit_ref(workspace)
    script_type = "ps" if os.name == "nt" else "sh"

    with tempfile.TemporaryDirectory() as tmp:
        backup = Path(tmp) / "preserve"
        saved = _snapshot_retarget_paths(workspace, backup, refresh_templates)
        log(f"Preserved {len(saved)} path(s) for retarget restore")
        try:
            run_specify(
                spec_cli,
                specify_init_argv(
                    canonical_agent,
                    generic_commands_dir,
                    script_type,
                    use_force=True,
                ),
                spec_kit_ref,
                quiet=quiet,
                cwd=workspace,
            )
        except subprocess.CalledProcessError:
            run_specify(
                spec_cli,
                specify_init_argv(
                    canonical_agent,
                    generic_commands_dir,
                    script_type,
                    use_force=False,
                ),
                spec_kit_ref,
                quiet=quiet,
                cwd=workspace,
            )
        _restore_snapshot(workspace, backup, saved)

    append_agents_installed(workspace, canonical_agent)
    update_agents_primary(workspace, canonical_agent)
    log(
        f"Retarget complete; agents.primary set to {canonical_agent!r} "
        "and agents.installed updated in .itx-config.yml"
    )
    warn(
        "specify's .specify/integration.json reflects the retargeted agent only; "
        "review git diff for unexpected changes outside preserved paths."
    )


def add_ai_workspace(
    workspace: Path,
    canonical_agent: str,
    generic_commands_dir: str | None,
    *,
    quiet: bool,
) -> None:
    spec_cli = detect_specify_cli()
    if not spec_cli:
        raise RuntimeError(
            "add-ai requires specify or uvx on PATH (spec-kit binary is not supported for this operation)."
        )

    spec_kit_ref = load_spec_kit_ref(workspace)
    script_type = "ps" if os.name == "nt" else "sh"
    gdir = (generic_commands_dir or "").strip() or None

    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / "proj"
        stage.mkdir(parents=True, exist_ok=True)
        try:
            run_specify(
                spec_cli,
                specify_init_argv(canonical_agent, gdir, script_type, use_force=True),
                spec_kit_ref,
                quiet=quiet,
                cwd=stage,
            )
        except subprocess.CalledProcessError:
            run_specify(
                spec_cli,
                specify_init_argv(canonical_agent, gdir, script_type, use_force=False),
                spec_kit_ref,
                quiet=quiet,
                cwd=stage,
            )
        if not copy_agent_tree_from_staging(stage, workspace, canonical_agent, gdir):
            raise RuntimeError("add-ai failed: could not copy agent scaffold from staging")

    append_agents_installed(workspace, canonical_agent)
    log(f"Merged scaffold for {canonical_agent!r}; appended to agents.installed in .itx-config.yml")
    warn(
        "Upstream .specify/integration.json still describes a single primary agent; "
        "use the correct tool UI per integration. Review overlapping dirs (e.g. .agents/, .github/) manually."
    )


def post_agent_extension_sync(
    workspace: Path,
    kit_root: Path,
    canonical_agent: str,
    *,
    skip_extension_sync: bool,
) -> None:
    """Re-run community `specify extension add` and align extension state for an agent."""
    if skip_extension_sync:
        return
    spec_cli = detect_specify_cli()
    if not spec_cli:
        warn("extension sync skipped: specify/uvx not on PATH")
        return
    spec_kit_ref = load_spec_kit_ref(workspace)
    try:
        install_community_extensions(
            spec_cli,
            kit_root,
            workspace,
            spec_kit_ref,
            quiet=False,
            with_jira=False,
            log_fn=log,
        )
    except Exception as exc:
        warn(f"extension sync failed: {exc}")

    n = materialize_extension_workflows_for_agent(workspace, canonical_agent)
    if n:
        log(f"Materialized {n} extension workflow file(s) for {canonical_agent!r}")

    n = materialize_extension_skills_for_agent(workspace, canonical_agent)
    if n:
        log(f"Materialized {n} extension skill file(s) for {canonical_agent!r}")

    if mirror_registry_commands(workspace, canonical_agent):
        log(f"Mirrored extension registry command entries for {canonical_agent!r}")


def patch_workspace(kit_root: Path, workspace: Path, force: bool = False) -> Tuple[int, List[str]]:
    """Apply all patch operations.

    Returns (total_updated_count, list_of_merge_instructions).
    """
    total = 0
    merge_needed: List[str] = []

    # ---- Kit-owned files: safe to overwrite always ----

    for ext_name in LOCAL_KIT_EXTENSIONS:
        ext_src = kit_root / "extensions" / ext_name
        ext_dst = workspace / ".specify" / "extensions" / ext_name
        n = copy_tree(ext_src, ext_dst)
        if n:
            log(f"Updated {ext_name} extension ({n} file(s))")
        total += n

    rules_src = kit_root / "presets" / "base" / "cursor-rules"
    rules_dst = workspace / ".cursor" / "rules"
    if rules_src.exists():
        n = copy_tree(rules_src, rules_dst)
        if n:
            log(f"Updated Cursor rules ({n} file(s))")
        total += n

    # ---- User-editable files: safe-update with backup / side-file ----

    editable_files = [
        (
            kit_root / "presets" / "base" / "constitution.md",
            workspace / ".specify" / "constitution.md",
        ),
        (
            kit_root / "presets" / "base" / "policy.yml",
            workspace / ".specify" / "policy.yml",
        ),
    ]

    docs_src = kit_root / "presets" / "base" / "docs"
    docs_dst = workspace / "docs" / "knowledge-base"
    if docs_src.exists() and docs_dst.exists():
        for name in ("workflow-and-gates.md", "index.md", "domain-selection.md", "delivery-mechanics.md"):
            editable_files.append((docs_src / name, docs_dst / name))

    base_preset = kit_root / "presets" / "base"
    specify_dir = workspace / ".specify"
    for name in (
        "decision-authority.yml",
        "input-contracts.yml",
        "notification-events.yml",
        "workflow-state-schema.yml",
    ):
        editable_files.append((base_preset / name, specify_dir / name))

    # ---- Kit-owned templates: always overwrite into .specify/templates/ ----

    tpl_src = kit_root / "presets" / "base" / "templates"
    tpl_dst = workspace / ".specify" / "templates"
    if tpl_src.exists():
        n = copy_tree(tpl_src, tpl_dst)
        if n:
            log(f"Updated templates ({n} file(s))")
        total += n

    for src, dst in editable_files:
        status = _safe_update_file(src, dst, force)
        if status is None:
            continue
        total += 1
        rel = dst.relative_to(workspace)
        if "staged as" in status:
            kit_update_rel = dst.with_suffix(dst.suffix + ".kit-update").relative_to(workspace)
            log(f"{rel}: {status}")
            merge_needed.append(f"  diff {rel} {kit_update_rel}")
        else:
            log(f"{rel}: {status}")

    # ---- Append-only config: spec_kit_ref ----
    _ensure_spec_kit_ref(workspace)

    return total, merge_needed


def _ensure_spec_kit_ref(workspace: Path) -> None:
    """Add spec_kit_ref to .itx-config.yml if not already present."""
    config_path = workspace / ".itx-config.yml"
    if not config_path.exists():
        return
    text = config_path.read_text(encoding="utf-8")
    if "spec_kit_ref:" in text:
        return
    try:
        from itx_specify import DEFAULT_SPEC_KIT_REF as default_ref
    except Exception:
        default_ref = "v0.5.0"
    text = text.rstrip("\n") + f'\nspec_kit_ref: "{default_ref}"\n'
    config_path.write_text(text, encoding="utf-8")
    log(f"Added spec_kit_ref: {default_ref} to .itx-config.yml")


_TASK_ID_RE = re.compile(r"^T\d{3}\b", re.IGNORECASE)


def _is_bare_task_line(line: str) -> bool:
    stripped = line.lstrip()
    if not stripped.startswith("- "):
        return False
    item_text = stripped[2:].strip()
    if not item_text or item_text.startswith("["):
        return False
    return _TASK_ID_RE.match(item_text) is not None


def fix_tasks_checkboxes(workspace: Path) -> int:
    """Convert bare task-id list items in tasks.md files to checkbox format.

    Only list items that look like real task rows (``- T001 ...``) are
    converted to checkbox syntax. Instructional bullets are left untouched.
    Returns the number of files modified.
    """
    task_files: List[Path] = []
    for pattern in ("specs/**/tasks.md", "tasks.md", ".specify/tasks.md", ".specify/tasks/tasks.md"):
        task_files.extend(workspace.glob(pattern))

    seen: set[Path] = set()
    modified = 0
    for path in task_files:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)

        text = path.read_text(encoding="utf-8")
        new_lines: List[str] = []
        changed = False
        for line in text.splitlines(keepends=True):
            if _is_bare_task_line(line):
                prefix_len = len(line) - len(line.lstrip())
                prefix = line[:prefix_len]
                stripped = line.lstrip()
                item_text = stripped[2:].strip()
                newline = "\n" if line.endswith("\n") else ""
                new_lines.append(f"{prefix}- [ ] {item_text}{newline}")
                changed = True
                continue
            new_lines.append(line)
        new_text = "".join(new_lines)
        if changed and new_text != text:
            path.write_text(new_text, encoding="utf-8")
            log(f"Fixed checkbox format: {path.relative_to(workspace)}")
            modified += 1
    return modified


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Patch an already-bootstrapped itexus-spec-kit workspace.",
    )
    parser.add_argument("--workspace", required=True, help="Target workspace root")
    parser.add_argument(
        "--kit-root",
        default=None,
        help="Path to itexus-spec-kit source (default: auto-detect from script location)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite user-editable files directly (creates .patch-backup first)",
    )
    parser.add_argument(
        "--fix-tasks",
        action="store_true",
        help="Convert bare list items in tasks.md files to checkbox format (- [ ])",
    )
    agent_grp = parser.add_mutually_exclusive_group()
    agent_grp.add_argument(
        "--retarget-ai",
        metavar="AGENT",
        default=None,
        help="Run specify init in workspace, restore preserved paths, then patch (requires specify/uvx).",
    )
    agent_grp.add_argument(
        "--add-ai",
        metavar="AGENT",
        default=None,
        help="Run specify init in a temp dir and merge agent scaffold into workspace, then patch.",
    )
    parser.add_argument(
        "--generic-commands-dir",
        default="",
        help="With --add-ai generic (or init): commands output directory. Required when AGENT is generic.",
    )
    parser.add_argument(
        "--retarget-ai-refresh-templates",
        action="store_true",
        help="When using --retarget-ai, do not preserve .specify/templates (allow specify to refresh them).",
    )
    parser.add_argument(
        "--skip-add-ai-extension-sync",
        action="store_true",
        help="With --add-ai or --retarget-ai: skip specify extension add, workflow materialization, and registry mirror (offline/scaffold-only).",
    )
    args = parser.parse_args(argv)

    workspace = Path(args.workspace).expanduser().resolve()
    if args.kit_root:
        kit_root = Path(args.kit_root).expanduser().resolve()
    else:
        kit_root = Path(__file__).resolve().parent.parent

    if not workspace.exists():
        sys.stderr.write(f"[itx-patch] Workspace not found: {workspace}\n")
        return 1
    if not (workspace / ".itx-config.yml").exists():
        sys.stderr.write(f"[itx-patch] Not an itexus-spec-kit workspace (missing .itx-config.yml): {workspace}\n")
        return 1

    log(f"Patching workspace: {workspace}")
    log(f"Kit source: {kit_root}")

    gcmd = (args.generic_commands_dir or "").strip() or None
    add_ai_canonical: str | None = None
    if args.retarget_ai:
        validate_init_agent(args.retarget_ai, gcmd)
        canonical = map_agent_for_specify(args.retarget_ai)
        try:
            retarget_ai_workspace(
                workspace,
                canonical,
                gcmd,
                refresh_templates=args.retarget_ai_refresh_templates,
                quiet=False,
            )
        except Exception as exc:
            sys.stderr.write(f"[itx-patch] retarget-ai failed: {exc}\n")
            return 1
    elif args.add_ai:
        validate_init_agent(args.add_ai, gcmd)
        canonical = map_agent_for_specify(args.add_ai)
        try:
            add_ai_workspace(workspace, canonical, gcmd, quiet=False)
        except Exception as exc:
            sys.stderr.write(f"[itx-patch] add-ai failed: {exc}\n")
            return 1
        add_ai_canonical = canonical

    total, merge_needed = patch_workspace(kit_root, workspace, force=args.force)

    sync_agent = add_ai_canonical
    if args.retarget_ai:
        sync_agent = canonical

    if sync_agent is not None:
        post_agent_extension_sync(
            workspace,
            kit_root,
            sync_agent,
            skip_extension_sync=args.skip_add_ai_extension_sync,
        )
    else:
        primary_agent = primary_agent_from_config(workspace)
        if primary_agent:
            n = materialize_extension_workflows_for_agent(workspace, primary_agent)
            if n:
                log(f"Materialized {n} extension workflow file(s) for {primary_agent!r}")
                total += n
            n = materialize_extension_skills_for_agent(workspace, primary_agent)
            if n:
                log(f"Materialized {n} extension skill file(s) for {primary_agent!r}")
                total += n
            if mirror_registry_commands(workspace, primary_agent):
                log(f"Mirrored extension registry command entries for {primary_agent!r}")

    if args.fix_tasks:
        fixed = fix_tasks_checkboxes(workspace)
        total += fixed
        if fixed:
            log(f"Migrated {fixed} tasks file(s) to checkbox format.")

    if total == 0:
        log("Already up to date.")
    else:
        log(f"Patch complete — {total} file(s) updated.")

    if merge_needed:
        log("")
        log("The following editable files differ from the kit version.")
        log("Review and merge the .kit-update files, then remove them:")
        for instruction in merge_needed:
            log(instruction)
        log("")
        log("Or re-run with --force to overwrite (creates .patch-backup first).")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
