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

Usage:
    python scripts/patch.py --workspace /path/to/project
    python scripts/patch.py --workspace /path/to/project --force
    python scripts/patch.py --workspace /path/to/project --kit-root /path/to/itexus-spec-kit
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path
from typing import List, Tuple


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


def patch_workspace(kit_root: Path, workspace: Path, force: bool = False) -> Tuple[int, List[str]]:
    """Apply all patch operations.

    Returns (total_updated_count, list_of_merge_instructions).
    """
    total = 0
    merge_needed: List[str] = []

    # ---- Kit-owned files: safe to overwrite always ----

    ext_src = kit_root / "extensions" / "itx-gates"
    ext_dst = workspace / ".specify" / "extensions" / "itx-gates"
    if ext_dst.exists():
        n = copy_tree(ext_src, ext_dst)
        if n:
            log(f"Updated itx-gates extension ({n} file(s))")
        total += n
    else:
        warn(".specify/extensions/itx-gates/ not found — skipping extension update")

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
    from importlib.util import module_from_spec, spec_from_file_location

    default_ref = "v0.5.0"
    init_path = Path(__file__).resolve().parent / "itx_init.py"
    if init_path.exists():
        try:
            spec = spec_from_file_location("_itx_init_ref", init_path)
            if spec and spec.loader:
                mod = module_from_spec(spec)
                spec.loader.exec_module(mod)
                default_ref = getattr(mod, "DEFAULT_SPEC_KIT_REF", default_ref)
        except Exception:
            pass
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

    total, merge_needed = patch_workspace(kit_root, workspace, force=args.force)

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
