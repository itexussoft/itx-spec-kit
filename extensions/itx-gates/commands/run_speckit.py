#!/usr/bin/env python3
"""Universal runner adapter for extension Spec-Kit slash commands.

Resolves the Spec-Kit CLI (spec-kit → specify → uvx) and delegates to it.
When no CLI can dispatch an extension command, the adapter falls back to
**local resolution**: it reads the extension registry in the workspace,
locates the matching command's markdown prompt, and prints it to stdout
between ``---SPECKIT-PROMPT---`` / ``---END-SPECKIT-PROMPT---`` markers so
the calling agent can execute the instructions directly.

When ``specify`` is found on PATH the adapter probes it with
``specify extension list``; if the command fails (stock specify-cli without
extension support) ``specify`` is skipped.

Pass ``--cli <name>`` to bypass auto-detection entirely.

Usage:
    python .specify/extensions/itx-gates/commands/run_speckit.py \
        --command review.run --workspace .

    python .specify/extensions/itx-gates/commands/run_speckit.py \
        --command cleanup.run --workspace /path/to/project

    python .specify/extensions/itx-gates/commands/run_speckit.py \
        --command cleanup.run --cli uvx --workspace .

Note:
    This adapter is for extension commands (for example ``review.run`` and
    ``cleanup.run``). Do not route core workflow slash commands such as
    ``/speckit.plan`` through this adapter.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

DEFAULT_SPEC_KIT_REF = "v0.5.0"

PROMPT_BEGIN = "---SPECKIT-PROMPT---"
PROMPT_END = "---END-SPECKIT-PROMPT---"


def _load_spec_kit_ref(workspace: Path) -> str:
    """Read spec_kit_ref from .itx-config.yml, falling back to the default."""
    config_path = workspace / ".itx-config.yml"
    if config_path.exists():
        try:
            data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                ref = data.get("spec_kit_ref", "").strip()
                if ref:
                    return ref
        except Exception:
            pass
    return DEFAULT_SPEC_KIT_REF


# ---------------------------------------------------------------------------
# Local extension resolution
# ---------------------------------------------------------------------------


def _canonicalize(command: str) -> str:
    """Normalise a command name so lookup works with or without ``speckit.`` prefix."""
    if command.startswith("speckit."):
        return command
    return f"speckit.{command}"


def _resolve_local(workspace: Path, command: str) -> Path | None:
    """Resolve *command* to a local markdown prompt file, or return ``None``.

    Reads ``.specify/extensions/.registry`` (JSON) to find which extension
    owns the command, then reads that extension's ``extension.yml`` to
    locate the markdown file.
    """
    registry_path = workspace / ".specify" / "extensions" / ".registry"
    if not registry_path.exists():
        return None

    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except Exception:
        return None

    extensions = registry.get("extensions", {})
    canonical = _canonicalize(command)

    ext_id: str | None = None
    for eid, meta in extensions.items():
        if not meta.get("enabled", False):
            continue
        cmds = meta.get("registered_commands", {})
        all_names: list[str] = []
        for names in cmds.values():
            all_names.extend(names)
        if canonical in all_names:
            ext_id = eid
            break

    if ext_id is None:
        return None

    ext_dir = workspace / ".specify" / "extensions" / ext_id
    ext_yml = ext_dir / "extension.yml"
    if not ext_yml.exists():
        return None

    try:
        ext_data = yaml.safe_load(ext_yml.read_text(encoding="utf-8"))
    except Exception:
        return None

    provides = ext_data.get("provides", {})
    for cmd_entry in provides.get("commands", []):
        names = [cmd_entry.get("name", "")]
        names.extend(cmd_entry.get("aliases", []))
        if canonical in names:
            md_file = cmd_entry.get("file")
            if md_file:
                md_path = ext_dir / md_file
                if md_path.exists():
                    return md_path
    return None


# ---------------------------------------------------------------------------
# CLI detection
# ---------------------------------------------------------------------------


def _specify_supports_extensions() -> bool:
    """Return True if the ``specify`` on PATH can manage extensions."""
    try:
        result = subprocess.run(
            ["specify", "extension", "list"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


def _specify_can_dispatch_extension_commands() -> bool:
    """Return True if ``specify`` appears able to run extension commands.

    Some specify-cli builds support ``extension list`` but do not expose a
    command-dispatch surface for extension commands like ``review.run``.
    In that case, we should skip CLI invocation and go straight to local
    prompt resolution.
    """
    try:
        result = subprocess.run(
            ["specify", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return False
        help_text = (result.stdout or "") + (result.stderr or "")
        # Modern dispatch-capable builds expose a generic runner command.
        return " run " in f" {help_text} "
    except Exception:
        return False


def _detect_cli(cli_override: str | None = None) -> str | None:
    """Return the first available Spec-Kit CLI or None.

    If *cli_override* is given and found on PATH it is returned immediately,
    skipping the usual probe logic.
    """
    if cli_override:
        if shutil.which(cli_override) or cli_override == "uvx" and shutil.which("uvx"):
            return cli_override
        return None

    for cmd in ("spec-kit", "specify", "uvx"):
        if not shutil.which(cmd):
            continue
        if cmd == "specify" and not _specify_supports_extensions():
            sys.stderr.write("[run-speckit] specify found but does not support extensions — skipping\n")
            continue
        return cmd
    return None


def _build_command(cli: str, speckit_command: str, workspace: Path, spec_kit_ref: str) -> list[str]:
    """Build the shell command list for the given CLI variant."""
    if cli == "spec-kit":
        return ["spec-kit", speckit_command, "--path", str(workspace)]
    if cli == "specify":
        return ["specify", speckit_command]
    # uvx
    return [
        "uvx",
        "--from",
        f"git+https://github.com/github/spec-kit.git@{spec_kit_ref}",
        "specify",
        speckit_command,
    ]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Universal adapter for running Spec-Kit slash commands.",
    )
    parser.add_argument(
        "--command",
        required=True,
        help=(
            "Extension command to run (e.g. review.run, cleanup.run). "
            "Core workflow commands (e.g. /speckit.plan) should run directly "
            "as slash commands."
        ),
    )
    parser.add_argument(
        "--workspace",
        default=".",
        help="Target workspace root (default: current directory).",
    )
    parser.add_argument(
        "--cli",
        default=None,
        choices=("spec-kit", "specify", "uvx"),
        help="Force a specific CLI backend, bypassing auto-detection.",
    )
    args = parser.parse_args(argv)
    workspace = Path(args.workspace).expanduser().resolve()

    # --- Attempt CLI dispatch first ---
    cli = _detect_cli(args.cli)
    cli_exit: int | None = None

    if cli is not None:
        spec_kit_ref = _load_spec_kit_ref(workspace)
        canonical = _canonicalize(args.command)
        if canonical.startswith("speckit.") and cli in {"specify", "uvx"}:
            if not _specify_can_dispatch_extension_commands():
                sys.stderr.write(f"[run-speckit] {cli} cannot dispatch extension commands — using local resolution\n")
                cli = None

    if cli is not None:
        cmd = _build_command(cli, args.command, workspace, spec_kit_ref)

        sys.stderr.write(f"[run-speckit] Using CLI: {cli}\n")
        sys.stderr.write(f"[run-speckit] Running: {' '.join(cmd)}\n")

        cwd = str(workspace) if cli in ("specify", "uvx") else None
        result = subprocess.run(cmd, cwd=cwd)
        cli_exit = result.returncode
        if cli_exit == 0:
            return 0

        sys.stderr.write(f"[run-speckit] CLI exited {cli_exit} — trying local resolution\n")

    # --- Fallback: resolve the extension prompt locally ---
    prompt_path = _resolve_local(workspace, args.command)
    if prompt_path is not None:
        rel = prompt_path.relative_to(workspace)
        sys.stderr.write(f"[run-speckit] Resolved locally: {rel}\n")
        content = prompt_path.read_text(encoding="utf-8")
        sys.stdout.write(f"{PROMPT_BEGIN}\n{content}\n{PROMPT_END}\n")
        return 0

    # --- Nothing worked ---
    if cli is None:
        sys.stderr.write(
            "[run-speckit] No Spec-Kit CLI found and local resolution failed.\n"
            "  Install one of: spec-kit, specify (specify-cli), or uvx.\n"
            "  With uvx:  pip install uv   (or see https://docs.astral.sh/uv/)\n"
        )
    else:
        sys.stderr.write(
            f"[run-speckit] CLI failed (exit {cli_exit}) and command "
            f"'{args.command}' not found in local extension registry.\n"
        )
    return 1


if __name__ == "__main__":
    sys.exit(main())
