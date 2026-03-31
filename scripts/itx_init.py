#!/usr/bin/env python3
"""Unified bootstrap for itexus-spec-kit.

This script replaces duplicated shell and PowerShell bootstrap logic.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from build_knowledge_manifest import build_manifest


ALLOWED_AGENTS = {"cursor", "claude", "copilot", "gemini", "codex"}
ALLOWED_DOMAINS = {"base", "fintech-trading", "fintech-banking", "healthcare"}
ALLOWED_KNOWLEDGE_MODES = {"lazy", "eager"}
ALLOWED_EXECUTION_MODES = {"mcp", "docker-fallback"}
DEFAULT_SPEC_KIT_REF = "v0.4.3"
EXTENSION_REFS = {
    "dsrednicki/spec-kit-cleanup": "v1.0.0",
    "ismaelJimenez/spec-kit-review": "v1.0.0",
    "mbachorik/spec-kit-jira": "v0.2.0",
}


def _repo_url(extension_id: str) -> str:
    return f"https://github.com/{extension_id}.git"


def _archive_url(extension_id: str, ref: str) -> str:
    return f"https://github.com/{extension_id}/archive/{ref}.zip"


def log(message: str) -> None:
    print(f"[itx-init] {message}")


def debug(enabled: bool, message: str) -> None:
    if enabled:
        print(f"[itx-init:debug] {message}")


def map_agent_for_specify(agent: str) -> str:
    return "cursor-agent" if agent == "cursor" else agent


def detect_spec_cli() -> str:
    for cmd in ("spec-kit", "specify", "uvx"):
        if shutil.which(cmd):
            return cmd
    return ""


def run_checked(command: list[str], quiet: bool = False, cwd: Path | None = None) -> None:
    stdout = subprocess.DEVNULL if quiet else None
    stderr = subprocess.DEVNULL if quiet else None
    subprocess.run(command, check=True, cwd=str(cwd) if cwd else None, stdout=stdout, stderr=stderr)


def run_specify(
    spec_cli: str,
    args: list[str],
    spec_kit_ref: str,
    quiet: bool = False,
    cwd: Path | None = None,
) -> None:
    if spec_cli == "specify":
        cmd = ["specify", *args]
    elif spec_cli == "uvx":
        cmd = ["uvx", "--from", f"git+https://github.com/github/spec-kit.git@{spec_kit_ref}", "specify", *args]
    else:
        raise RuntimeError(f"run_specify called with unsupported cli: {spec_cli}")
    run_checked(cmd, quiet=quiet, cwd=cwd)


def ensure_valid_args(args: argparse.Namespace) -> None:
    if args.agent not in ALLOWED_AGENTS:
        raise ValueError(f"Invalid --agent: {args.agent}")
    if args.domain not in ALLOWED_DOMAINS:
        raise ValueError(f"Invalid --domain: {args.domain}")
    if args.knowledge_mode not in ALLOWED_KNOWLEDGE_MODES:
        raise ValueError(f"Invalid --knowledge-mode: {args.knowledge_mode}")
    if args.execution_mode not in ALLOWED_EXECUTION_MODES:
        raise ValueError(f"Invalid --execution-mode: {args.execution_mode}")
    if not str(args.spec_kit_ref).strip():
        raise ValueError("--spec-kit-ref must not be empty")


def require_command(name: str) -> None:
    if shutil.which(name) is None:
        raise RuntimeError(f"Missing required command: {name}")


def install_extension_from_git(
    spec_cli: str,
    repo_url: str,
    git_ref: str,
    local_dir: Path,
    spec_extension_id: str,
    spec_zip_url: str,
    spec_kit_ref: str,
    quiet: bool,
    workspace: Path,
) -> None:
    if shutil.which("git"):
        if not quiet:
            log(f"Cloning extension: {repo_url}@{git_ref}")
        run_checked(["git", "clone", repo_url, str(local_dir)], quiet=quiet)
        run_checked(["git", "checkout", git_ref], quiet=quiet, cwd=local_dir)
        if not quiet:
            log(f"Installing extension from dev path: {local_dir}")
        run_specify(spec_cli, ["extension", "add", str(local_dir), "--dev"], spec_kit_ref, quiet=quiet, cwd=workspace)
        return

    print(f"Warning: 'git' not found. Falling back to ZIP install for {spec_extension_id}@{git_ref}.", file=sys.stderr)
    run_specify(
        spec_cli,
        ["extension", "add", spec_extension_id, "--from", spec_zip_url],
        spec_kit_ref,
        quiet=quiet,
        cwd=workspace,
    )


def copy_tree_contents(source: Path, target: Path) -> None:
    if not source.exists():
        return
    target.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        dest = target / item.name
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)


def write_itx_config(
    workspace: Path,
    domain: str,
    execution_mode: str,
    knowledge_mode: str,
    container_name: str,
    spec_kit_ref: str = DEFAULT_SPEC_KIT_REF,
) -> None:
    lines = [
        f'domain: "{domain}"',
        f'execution_mode: "{execution_mode}"',
        f'spec_kit_ref: "{spec_kit_ref}"',
        "knowledge:",
        f'  mode: "{knowledge_mode}"',
    ]
    if execution_mode == "docker-fallback":
        lines.extend(
            [
                "docker:",
                f'  container_name: "{container_name}"',
            ]
        )
    workspace.joinpath(".itx-config.yml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def merge_pattern_index(kit_root: Path, workspace: Path, domain: str) -> None:
    target = workspace / ".specify" / "pattern-index.md"
    chunks: list[str] = []
    base = kit_root / "presets" / "base" / "pattern-index.md"
    if base.exists():
        chunks.append(base.read_text(encoding="utf-8").rstrip())
    if domain != "base":
        domain_index = kit_root / "presets" / domain / "pattern-index.md"
        if domain_index.exists():
            chunks.append(domain_index.read_text(encoding="utf-8").rstrip())
    target.write_text("\n\n".join([c for c in chunks if c]) + "\n", encoding="utf-8")


def ensure_lazy_gitignore(workspace: Path) -> None:
    gitignore = workspace / ".gitignore"
    marker = ".specify/.knowledge-store/"
    if gitignore.exists() and marker in gitignore.read_text(encoding="utf-8", errors="ignore"):
        return
    with gitignore.open("a", encoding="utf-8") as f:
        f.write("\n# itexus-spec-kit lazy knowledge staging area\n.specify/.knowledge-store/\n")


def stage_knowledge(kit_root: Path, workspace: Path, domain: str, knowledge_mode: str) -> None:
    pattern_target = workspace / ".specify" / "patterns"
    design_target = workspace / ".specify" / "design-patterns"
    anti_target = workspace / ".specify" / "anti-patterns"
    store_root = workspace / ".specify" / ".knowledge-store"

    if knowledge_mode == "eager":
        base_target = workspace / ".specify"
    else:
        base_target = store_root
        (store_root / "patterns").mkdir(parents=True, exist_ok=True)
        (store_root / "design-patterns").mkdir(parents=True, exist_ok=True)
        (store_root / "anti-patterns").mkdir(parents=True, exist_ok=True)
        ensure_lazy_gitignore(workspace)

    copy_tree_contents(kit_root / "presets" / "base" / "patterns", base_target / "patterns")
    copy_tree_contents(kit_root / "presets" / "base" / "design-patterns", base_target / "design-patterns")
    copy_tree_contents(kit_root / "presets" / "base" / "anti-patterns", base_target / "anti-patterns")

    if domain != "base":
        copy_tree_contents(kit_root / "presets" / domain / "patterns", base_target / "patterns")
        copy_tree_contents(kit_root / "presets" / domain / "design-patterns", base_target / "design-patterns")
        copy_tree_contents(kit_root / "presets" / domain / "anti-patterns", base_target / "anti-patterns")

    pattern_target.mkdir(parents=True, exist_ok=True)
    design_target.mkdir(parents=True, exist_ok=True)
    anti_target.mkdir(parents=True, exist_ok=True)


def stage_docs_and_policy(kit_root: Path, workspace: Path, domain: str) -> None:
    (workspace / ".specify" / "context").mkdir(parents=True, exist_ok=True)
    (workspace / "docs" / "knowledge-base").mkdir(parents=True, exist_ok=True)

    base_docs = kit_root / "presets" / "base" / "docs"
    for filename in ("index.md", "workflow-and-gates.md", "domain-selection.md"):
        src = base_docs / filename
        if src.exists():
            shutil.copy2(src, workspace / "docs" / "knowledge-base" / filename)

    policy_src = kit_root / "presets" / "base" / "policy.yml"
    if policy_src.exists():
        shutil.copy2(policy_src, workspace / ".specify" / "policy.yml")

    if domain != "base":
        copy_tree_contents(kit_root / "presets" / domain / "docs", workspace / "docs" / "knowledge-base")
        glossary = kit_root / "presets" / domain / "glossary.md"
        if glossary.exists():
            shutil.copy2(glossary, workspace / "docs" / "knowledge-base" / "glossary.md")


def stage_templates(kit_root: Path, workspace: Path) -> None:
    tpl_src = kit_root / "presets" / "base" / "templates"
    tpl_dst = workspace / ".specify" / "templates"
    if tpl_src.exists():
        copy_tree_contents(tpl_src, tpl_dst)


def stage_cursor_rules(kit_root: Path, workspace: Path) -> None:
    """Copy Cursor rules from the base preset into the workspace."""
    rules_src = kit_root / "presets" / "base" / "cursor-rules"
    rules_dst = workspace / ".cursor" / "rules"
    if rules_src.exists():
        copy_tree_contents(rules_src, rules_dst)


def build_knowledge_manifest_file(kit_root: Path, workspace: Path, domain: str) -> None:
    manifest = build_manifest(kit_root.resolve(), domain)
    output = workspace / ".specify" / "knowledge-manifest.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    import json

    output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"[build-knowledge-manifest] Wrote {output}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Initialize an itexus-spec-kit workspace.",
    )
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--agent", required=True)
    parser.add_argument("--domain", default="base")
    parser.add_argument("--knowledge-mode", default="lazy")
    parser.add_argument("--workspace", default=str(Path.cwd()))
    parser.add_argument("--execution-mode", default="mcp")
    parser.add_argument("--container-name", default="")
    parser.add_argument(
        "--spec-kit-ref",
        default=DEFAULT_SPEC_KIT_REF,
        help="Pinned git ref for uvx-based specify-cli execution (tag or commit SHA).",
    )
    parser.add_argument("--with-jira", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    ensure_valid_args(args)

    script_dir = Path(__file__).resolve().parent
    kit_root = script_dir.parent
    workspace = Path(args.workspace).expanduser().resolve()
    spec_cli = detect_spec_cli()

    log("Checking host prerequisites...")
    require_command("python3")
    if not spec_cli:
        raise RuntimeError("Missing required command: either 'spec-kit', 'specify' (specify-cli), or 'uvx'.")
    if args.execution_mode == "docker-fallback":
        require_command("docker")
    container_name = args.container_name or f"{args.project_name}-sandbox"
    workspace.mkdir(parents=True, exist_ok=True)

    log("Initializing spec-kit project...")
    if spec_cli == "spec-kit":
        run_checked(
            [
                "spec-kit",
                "init",
                "--agent",
                args.agent,
                "--path",
                str(workspace),
                "--project-name",
                args.project_name,
            ],
            quiet=args.quiet,
        )
    else:
        specify_agent = map_agent_for_specify(args.agent)
        debug(args.debug, f"Using specify-cli (specify). Agent: {specify_agent}")
        debug(args.debug, f"Using spec-kit ref for uvx fallback: {args.spec_kit_ref}")
        script_type = "ps" if os.name == "nt" else "sh"
        try:
            run_specify(
                spec_cli,
                ["init", "--here", "--ai", specify_agent, "--script", script_type, "--force"],
                args.spec_kit_ref,
                quiet=args.quiet,
                cwd=workspace,
            )
        except subprocess.CalledProcessError:
            run_specify(
                spec_cli,
                ["init", "--here", "--ai", specify_agent, "--script", script_type],
                args.spec_kit_ref,
                quiet=args.quiet,
                cwd=workspace,
            )

    log("Installing core presets/extensions...")
    if spec_cli == "spec-kit":
        try:
            run_checked(["spec-kit", "preset", "remove", "base", "--path", str(workspace)], quiet=True)
        except subprocess.CalledProcessError:
            pass
        run_checked(
            ["spec-kit", "preset", "install", "base", "--source", str(kit_root / "presets" / "base"), "--path", str(workspace)],
            quiet=args.quiet,
        )
        if args.domain != "base":
            try:
                run_checked(
                    [
                        "spec-kit",
                        "preset",
                        "install",
                        args.domain,
                        "--source",
                        str(kit_root / "presets" / args.domain),
                        "--path",
                        str(workspace),
                    ],
                    quiet=args.quiet,
                )
            except subprocess.CalledProcessError:
                log(
                    f"Domain preset '{args.domain}' could not be registered via CLI "
                    f"(overlay presets may lack templates). "
                    f"Content will be staged by the file-copy step."
                )
        run_checked(
            [
                "spec-kit",
                "extension",
                "install",
                "itx-gates",
                "--source",
                str(kit_root / "extensions" / "itx-gates"),
                "--path",
                str(workspace),
            ],
            quiet=args.quiet,
        )
        run_checked(
            [
                "spec-kit",
                "extension",
                "install",
                f"dsrednicki/spec-kit-cleanup@{EXTENSION_REFS['dsrednicki/spec-kit-cleanup']}",
                "--path",
                str(workspace),
            ],
            quiet=args.quiet,
        )
        run_checked(
            [
                "spec-kit",
                "extension",
                "install",
                f"ismaelJimenez/spec-kit-review@{EXTENSION_REFS['ismaelJimenez/spec-kit-review']}",
                "--path",
                str(workspace),
            ],
            quiet=args.quiet,
        )
        if args.with_jira:
            run_checked(
                [
                    "spec-kit",
                    "extension",
                    "install",
                    f"mbachorik/spec-kit-jira@{EXTENSION_REFS['mbachorik/spec-kit-jira']}",
                    "--path",
                    str(workspace),
                ],
                quiet=args.quiet,
            )
    else:
        try:
            run_specify(spec_cli, ["preset", "remove", "base"], args.spec_kit_ref, quiet=True, cwd=workspace)
        except subprocess.CalledProcessError:
            pass
        run_specify(
            spec_cli,
            ["preset", "add", "base", "--dev", str(kit_root / "presets" / "base")],
            args.spec_kit_ref,
            quiet=args.quiet,
            cwd=workspace,
        )
        if args.domain != "base":
            try:
                run_specify(
                    spec_cli,
                    ["preset", "add", args.domain, "--dev", str(kit_root / "presets" / args.domain)],
                    args.spec_kit_ref,
                    quiet=args.quiet,
                    cwd=workspace,
                )
            except subprocess.CalledProcessError:
                log(
                    f"Domain preset '{args.domain}' could not be registered via CLI "
                    f"(overlay presets may lack templates). "
                    f"Content will be staged by the file-copy step."
                )
        run_specify(
            spec_cli,
            ["extension", "add", str(kit_root / "extensions" / "itx-gates"), "--dev"],
            args.spec_kit_ref,
            quiet=args.quiet,
            cwd=workspace,
        )

        with tempfile.TemporaryDirectory() as temp_ext_dir:
            temp_root = Path(temp_ext_dir)
            install_extension_from_git(
                spec_cli,
                _repo_url("dsrednicki/spec-kit-cleanup"),
                EXTENSION_REFS["dsrednicki/spec-kit-cleanup"],
                temp_root / "spec-kit-cleanup",
                "dsrednicki/spec-kit-cleanup",
                _archive_url("dsrednicki/spec-kit-cleanup", EXTENSION_REFS["dsrednicki/spec-kit-cleanup"]),
                args.spec_kit_ref,
                args.quiet,
                workspace,
            )
            install_extension_from_git(
                spec_cli,
                _repo_url("ismaelJimenez/spec-kit-review"),
                EXTENSION_REFS["ismaelJimenez/spec-kit-review"],
                temp_root / "spec-kit-review",
                "ismaelJimenez/spec-kit-review",
                _archive_url("ismaelJimenez/spec-kit-review", EXTENSION_REFS["ismaelJimenez/spec-kit-review"]),
                args.spec_kit_ref,
                args.quiet,
                workspace,
            )
            if args.with_jira:
                install_extension_from_git(
                    spec_cli,
                    _repo_url("mbachorik/spec-kit-jira"),
                    EXTENSION_REFS["mbachorik/spec-kit-jira"],
                    temp_root / "spec-kit-jira",
                    "mbachorik/spec-kit-jira",
                    _archive_url("mbachorik/spec-kit-jira", EXTENSION_REFS["mbachorik/spec-kit-jira"]),
                    args.spec_kit_ref,
                    args.quiet,
                    workspace,
                )

    log("Writing .itx-config.yml...")
    write_itx_config(workspace, args.domain, args.execution_mode, args.knowledge_mode, container_name, args.spec_kit_ref)
    stage_docs_and_policy(kit_root, workspace, args.domain)
    stage_templates(kit_root, workspace)
    stage_cursor_rules(kit_root, workspace)
    stage_knowledge(kit_root, workspace, args.domain, args.knowledge_mode)
    merge_pattern_index(kit_root, workspace, args.domain)

    log("Generating knowledge manifest...")
    build_knowledge_manifest_file(kit_root, workspace, args.domain)

    if args.execution_mode == "docker-fallback":
        copy_tree_contents(kit_root / "harnesses" / "docker-fallbacks", workspace / "harnesses" / "docker-fallbacks")
        (workspace / "harnesses" / "docker-fallbacks").mkdir(parents=True, exist_ok=True)
        (workspace / "harnesses" / "docker-fallbacks" / ".env").write_text(
            f"ITX_CONTAINER_NAME={container_name}\n", encoding="utf-8"
        )

    log("Initialization complete.")
    if args.execution_mode == "docker-fallback":
        log("Python hooks require Python 3.x and Docker to remain installed.")
    else:
        log("Python hooks require Python 3.x to remain installed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover - CLI boundary
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
