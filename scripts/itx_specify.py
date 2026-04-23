"""Shared helpers for specify-cli / spec-kit alignment (pinned to github/spec-kit tag)."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

import yaml

# Keep in sync with DEFAULT_SPEC_KIT_REF / integration keys for that tag.
# github/spec-kit v0.5.0 — see src/specify_cli/integrations/__init__.py
DEFAULT_SPEC_KIT_REF = "v0.5.0"

# Integration keys registered in specify-cli v0.5.0, excluding "generic".
SPECIFY_INTEGRATION_KEYS_V0_5_0: frozenset[str] = frozenset(
    {
        "agy",
        "amp",
        "auggie",
        "bob",
        "claude",
        "codex",
        "codebuddy",
        "copilot",
        "cursor-agent",
        "gemini",
        "iflow",
        "junie",
        "kilocode",
        "kimi",
        "kiro-cli",
        "opencode",
        "pi",
        "qodercli",
        "qwen",
        "roo",
        "shai",
        "tabnine",
        "trae",
        "vibe",
        "windsurf",
    }
)

# Match specify_cli.AI_ASSISTANT_ALIASES + itexus convenience for --agent.
AGENT_ALIASES: dict[str, str] = {
    "cursor": "cursor-agent",
    "kiro": "kiro-cli",
}

# AGENT_CONFIG[*]["folder"] from specify-cli v0.5.0 (used for --add-ai copy roots).
# "generic" uses user-provided commands dir, not a single root.
AGENT_ARTIFACT_FOLDERS: dict[str, str | None] = {
    "agy": ".agent/",
    "amp": ".agents/",
    "auggie": ".augment/",
    "bob": ".bob/",
    "claude": ".claude/",
    "codex": ".agents/",
    "codebuddy": ".codebuddy/",
    "copilot": ".github/",
    "cursor-agent": ".cursor/",
    "gemini": ".gemini/",
    "generic": None,
    "iflow": ".iflow/",
    "junie": ".junie/",
    "kilocode": ".kilocode/",
    "kimi": ".kimi/",
    "kiro-cli": ".kiro/",
    "opencode": ".opencode/",
    "pi": ".pi/",
    "qodercli": ".qoder/",
    "qwen": ".qwen/",
    "roo": ".roo/",
    "shai": ".shai/",
    "tabnine": ".tabnine/agent/",
    "trae": ".trae/",
    "vibe": ".vibe/",
    "windsurf": ".windsurf/",
}


def normalize_agent_for_specify(agent: str) -> str:
    """Apply aliases and return the canonical specify --ai integration key."""
    raw = agent.strip()
    if not raw:
        raise ValueError("Agent name must not be empty")
    resolved = AGENT_ALIASES.get(raw, raw)
    if resolved == "generic":
        return "generic"
    if resolved not in SPECIFY_INTEGRATION_KEYS_V0_5_0:
        allowed = ", ".join(sorted(SPECIFY_INTEGRATION_KEYS_V0_5_0 | frozenset({"generic"})))
        raise ValueError(f"Invalid agent/integration: {agent!r}. Choose from: {allowed}, generic")
    return resolved


def map_agent_for_specify(agent: str) -> str:
    """Backward-compatible name: normalize for `specify init --ai`."""
    return normalize_agent_for_specify(agent)


def validate_init_agent(agent: str, generic_commands_dir: str | None) -> str:
    """Validate --agent for itx-init; require --generic-commands-dir when agent is generic."""
    canonical = normalize_agent_for_specify(agent)
    if canonical == "generic":
        if not (generic_commands_dir or "").strip():
            raise ValueError("--generic-commands-dir is required when --agent generic")
    return canonical


def detect_spec_cli() -> str:
    """First available: spec-kit, specify, or uvx (same priority as historical itx-init)."""
    for cmd in ("spec-kit", "specify", "uvx"):
        if shutil.which(cmd):
            return cmd
    return ""


def detect_specify_cli() -> str:
    """specify or uvx only (argv shape for `specify init`); excludes spec-kit."""
    for cmd in ("specify", "uvx"):
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


def load_spec_kit_ref(workspace: Path) -> str:
    """Read spec_kit_ref from .itx-config.yml, falling back to DEFAULT_SPEC_KIT_REF."""
    config_path = workspace / ".itx-config.yml"
    if config_path.exists():
        try:
            data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                ref = str(data.get("spec_kit_ref", "")).strip()
                if ref:
                    return ref
        except (OSError, yaml.YAMLError, TypeError):
            pass
    return DEFAULT_SPEC_KIT_REF


def specify_init_argv(
    canonical_agent: str,
    generic_commands_dir: str | None,
    script_type: str,
    *,
    use_force: bool,
    extra_tail: list[str] | None = None,
) -> list[str]:
    """Argv for `specify init` (subcommand + flags), excluding the leading ``specify``."""
    tail = list(extra_tail or [])
    if use_force:
        tail.append("--force")
    tail.extend(["--ignore-agent-tools", "--no-git"])
    if canonical_agent == "generic":
        gdir = (generic_commands_dir or "").strip()
        if not gdir:
            raise ValueError("generic_commands_dir required for generic integration")
        return [
            "init",
            "--here",
            "--integration",
            "generic",
            "--integration-options",
            f"--commands-dir {gdir}",
            "--script",
            script_type,
            *tail,
        ]
    return [
        "init",
        "--here",
        "--ai",
        canonical_agent,
        "--script",
        script_type,
        *tail,
    ]


def try_load_agent_config_from_specify_cli() -> dict[str, Any] | None:
    """If specify_cli is installed, return its AGENT_CONFIG dict; else None."""
    try:
        from specify_cli import AGENT_CONFIG  # type: ignore[import-not-found]

        if isinstance(AGENT_CONFIG, dict):
            return AGENT_CONFIG
    except Exception:
        pass
    return None


def agent_artifact_folder(canonical_key: str) -> str | None:
    """Project-relative folder root for an integration's scaffold (for --add-ai)."""
    cfg = try_load_agent_config_from_specify_cli()
    if cfg and canonical_key in cfg:
        folder = cfg[canonical_key].get("folder")
        if folder is None:
            return None
        return str(folder).rstrip("/") + "/" if str(folder) else None
    return AGENT_ARTIFACT_FOLDERS.get(canonical_key)


# --- Community extensions (pinned refs; keep in sync with itx-init / release docs) ---

EXTENSION_REFS: dict[str, str] = {
    "dsrednicki/spec-kit-cleanup": "v1.0.0",
    "ismaelJimenez/spec-kit-review": "v1.0.0",
    "mbachorik/spec-kit-jira": "v0.2.0",
}

# Local itexus extensions installed from the checked-out kit source.
LOCAL_KIT_EXTENSIONS: tuple[str, ...] = (
    "itx-gates",
    "itx-brownfield-workflows",
)


def extension_repo_url(extension_id: str) -> str:
    return f"https://github.com/{extension_id}.git"


def extension_archive_url(extension_id: str, ref: str) -> str:
    return f"https://github.com/{extension_id}/archive/{ref}.zip"


def strip_legacy_extension_command_aliases(ext_dir: Path) -> None:
    """Remove command `aliases` entries before `specify extension add`.

    specify-cli 0.5+ rejects short forms like `speckit.cleanup`; canonical names
    such as `speckit.cleanup.run` remain valid. Community extensions may still
    ship legacy aliases until upstream tags are updated.
    """
    ext_yml = ext_dir / "extension.yml"
    if not ext_yml.is_file():
        return
    try:
        data = yaml.safe_load(ext_yml.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return
    if not isinstance(data, dict):
        return
    provides = data.get("provides")
    if not isinstance(provides, dict):
        return
    commands = provides.get("commands")
    if not isinstance(commands, list):
        return
    changed = False
    for entry in commands:
        if isinstance(entry, dict) and "aliases" in entry:
            entry.pop("aliases", None)
            changed = True
    if changed:
        ext_yml.write_text(
            yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )


def _extension_install_message(quiet: bool, log_fn: Callable[[str], None] | None, message: str) -> None:
    if quiet:
        return
    if log_fn:
        log_fn(message)
    else:
        print(f"[itx-specify] {message}")


def _extension_install_warn(quiet: bool, log_fn: Callable[[str], None] | None, message: str) -> None:
    if quiet:
        return
    if log_fn:
        log_fn(f"WARNING: {message}")
    else:
        print(f"[itx-specify] WARNING: {message}", file=sys.stderr)


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
    *,
    log_fn: Callable[[str], None] | None = None,
) -> None:
    if shutil.which("git"):
        _extension_install_message(quiet, log_fn, f"Cloning extension: {repo_url}@{git_ref}")
        run_checked(["git", "clone", repo_url, str(local_dir)], quiet=quiet)
        run_checked(["git", "checkout", git_ref], quiet=quiet, cwd=local_dir)
        strip_legacy_extension_command_aliases(local_dir)
        _extension_install_message(quiet, log_fn, f"Installing extension from dev path: {local_dir}")
        run_specify(spec_cli, ["extension", "add", str(local_dir), "--dev"], spec_kit_ref, quiet=quiet, cwd=workspace)
        return

    print(
        f"Warning: 'git' not found. Falling back to ZIP install for {spec_extension_id}@{git_ref}.",
        file=sys.stderr,
    )
    run_specify(
        spec_cli,
        ["extension", "add", spec_extension_id, "--from", spec_zip_url],
        spec_kit_ref,
        quiet=quiet,
        cwd=workspace,
    )


def install_community_extensions(
    spec_cli: str,
    kit_root: Path,
    workspace: Path,
    spec_kit_ref: str,
    *,
    quiet: bool = False,
    with_jira: bool = False,
    log_fn: Callable[[str], None] | None = None,
) -> None:
    """Run `specify extension add` for local kit extensions and pinned community extensions."""
    if spec_cli not in ("specify", "uvx"):
        raise RuntimeError("install_community_extensions requires specify or uvx")

    for ext_name in LOCAL_KIT_EXTENSIONS:
        ext_path = kit_root / "extensions" / ext_name
        try:
            run_specify(
                spec_cli,
                ["extension", "add", str(ext_path), "--dev"],
                spec_kit_ref,
                quiet=quiet,
                cwd=workspace,
            )
        except subprocess.CalledProcessError:
            _extension_install_warn(
                quiet,
                log_fn,
                f"extension add {ext_name} failed or redundant; continuing",
            )

    with tempfile.TemporaryDirectory() as temp_ext_dir:
        temp_root = Path(temp_ext_dir)
        for ext_id, git_ref, subdir in (
            ("dsrednicki/spec-kit-cleanup", EXTENSION_REFS["dsrednicki/spec-kit-cleanup"], "spec-kit-cleanup"),
            ("ismaelJimenez/spec-kit-review", EXTENSION_REFS["ismaelJimenez/spec-kit-review"], "spec-kit-review"),
        ):
            try:
                install_extension_from_git(
                    spec_cli,
                    extension_repo_url(ext_id),
                    git_ref,
                    temp_root / subdir,
                    ext_id,
                    extension_archive_url(ext_id, git_ref),
                    spec_kit_ref,
                    quiet,
                    workspace,
                    log_fn=log_fn,
                )
            except subprocess.CalledProcessError:
                _extension_install_warn(
                    quiet,
                    log_fn,
                    f"extension add {ext_id} failed or redundant; continuing",
                )
        if with_jira:
            jid = "mbachorik/spec-kit-jira"
            try:
                install_extension_from_git(
                    spec_cli,
                    extension_repo_url(jid),
                    EXTENSION_REFS[jid],
                    temp_root / "spec-kit-jira",
                    jid,
                    extension_archive_url(jid, EXTENSION_REFS[jid]),
                    spec_kit_ref,
                    quiet,
                    workspace,
                    log_fn=log_fn,
                )
            except subprocess.CalledProcessError:
                _extension_install_warn(
                    quiet,
                    log_fn,
                    f"extension add {jid} failed or redundant; continuing",
                )


def agent_workflows_dir(workspace: Path, canonical_agent: str) -> Path | None:
    """Return ``workspace / <artifact> / workflows`` if that directory exists, else None."""
    if canonical_agent == "generic":
        return None
    folder = agent_artifact_folder(canonical_agent)
    if not folder:
        return None
    rel = folder.rstrip("/")
    wd = workspace / rel / "workflows"
    return wd if wd.is_dir() else None


def materialize_extension_workflows_for_agent(workspace: Path, canonical_agent: str) -> int:
    """Copy extension command markdown into the agent's ``workflows/`` dir when missing (idempotent)."""
    workflows_dir = agent_workflows_dir(workspace, canonical_agent)
    if workflows_dir is None:
        return 0

    ext_root = workspace / ".specify" / "extensions"
    if not ext_root.is_dir():
        return 0

    created = 0
    for ext_dir in sorted(ext_root.iterdir()):
        if not ext_dir.is_dir() or ext_dir.name.startswith("."):
            continue
        ext_yml = ext_dir / "extension.yml"
        if not ext_yml.is_file():
            continue
        try:
            data = yaml.safe_load(ext_yml.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            continue
        if not isinstance(data, dict):
            continue
        provides = data.get("provides")
        if not isinstance(provides, dict):
            continue
        commands = provides.get("commands")
        if not isinstance(commands, list):
            continue
        for entry in commands:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name")
            rel_file = entry.get("file")
            if not name or not rel_file:
                continue
            src = ext_dir / str(rel_file)
            if not src.is_file():
                continue
            dest = workflows_dir / f"{name}.md"
            if dest.exists():
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            created += 1
    return created


_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n?", re.DOTALL)


def agent_skills_dir(workspace: Path, canonical_agent: str) -> Path | None:
    """Return a skill directory for agents that expose skill folders."""
    if canonical_agent == "generic":
        return None
    folder = agent_artifact_folder(canonical_agent)
    if not folder:
        return None
    rel = folder.rstrip("/")
    candidate = workspace / rel / "skills"
    if candidate.is_dir():
        return candidate
    if canonical_agent in {"claude", "codex"}:
        return candidate
    return None


def _split_script_command(command: str) -> tuple[str, str]:
    text = str(command).strip()
    if not text:
        return "", ""
    parts = text.split(maxsplit=1)
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " " + parts[1]


def _resolve_skill_script_reference(workspace: Path, ext_dir: Path, ext_id: str, raw: str) -> str:
    script_rel, suffix = _split_script_command(raw)
    if not script_rel:
        return raw
    ext_script = ext_dir / script_rel
    if ext_script.exists():
        return f".specify/extensions/{ext_id}/{script_rel}{suffix}"
    shared_script = workspace / ".specify" / script_rel
    if shared_script.exists():
        return f".specify/{script_rel}{suffix}"
    return raw


def _load_command_frontmatter(markdown: str) -> tuple[dict[str, Any], str]:
    match = _FRONTMATTER_RE.match(markdown)
    if not match:
        return {}, markdown
    try:
        data = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        data = {}
    body = markdown[match.end() :]
    return data if isinstance(data, dict) else {}, body


def materialize_extension_skills_for_agent(workspace: Path, canonical_agent: str) -> int:
    """Create agent skill files from installed extension commands when missing."""
    skills_dir = agent_skills_dir(workspace, canonical_agent)
    if skills_dir is None:
        return 0

    ext_root = workspace / ".specify" / "extensions"
    if not ext_root.is_dir():
        return 0

    created = 0
    for ext_dir in sorted(ext_root.iterdir()):
        if not ext_dir.is_dir() or ext_dir.name.startswith("."):
            continue
        ext_yml = ext_dir / "extension.yml"
        if not ext_yml.is_file():
            continue
        try:
            data = yaml.safe_load(ext_yml.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            continue
        if not isinstance(data, dict):
            continue
        provides = data.get("provides")
        if not isinstance(provides, dict):
            continue
        commands = provides.get("commands")
        if not isinstance(commands, list):
            continue
        ext_id = str(data.get("extension", {}).get("id", ext_dir.name))
        for entry in commands:
            if not isinstance(entry, dict):
                continue
            name = str(entry.get("name", "")).strip()
            rel_file = str(entry.get("file", "")).strip()
            if not name or not rel_file:
                continue
            src = ext_dir / rel_file
            if not src.is_file():
                continue

            skill_name = name.replace(".", "-")
            dest = skills_dir / skill_name / "SKILL.md"
            if dest.exists():
                continue

            raw_markdown = src.read_text(encoding="utf-8")
            frontmatter, body = _load_command_frontmatter(raw_markdown)
            body = body.lstrip("\n")

            scripts = frontmatter.get("scripts")
            if isinstance(scripts, dict):
                sh_script = scripts.get("sh")
                if isinstance(sh_script, str) and "{SCRIPT}" in body:
                    resolved = _resolve_skill_script_reference(workspace, ext_dir, ext_id, sh_script)
                    body = body.replace("{SCRIPT}", resolved)

            description = str(
                frontmatter.get("description")
                or entry.get("description")
                or name
            ).strip()
            meta = {
                "name": skill_name,
                "description": description,
                "compatibility": "Requires spec-kit project structure with .specify/ directory",
                "metadata": {
                    "author": "github-spec-kit",
                    "source": f"{ext_id}:{rel_file}",
                },
            }
            skills_dir.mkdir(parents=True, exist_ok=True)
            dest.parent.mkdir(parents=True, exist_ok=True)
            rendered = "---\n"
            rendered += yaml.dump(meta, default_flow_style=False, sort_keys=False, allow_unicode=True)
            rendered += "---\n\n"
            rendered += body
            if not rendered.endswith("\n"):
                rendered += "\n"
            dest.write_text(rendered, encoding="utf-8")
            created += 1
    return created


def mirror_registry_commands(workspace: Path, target_agent: str) -> bool:
    """If ``registered_commands`` lacks *target_agent*, copy command lists from another integration key."""
    reg_path = workspace / ".specify" / "extensions" / ".registry"
    if not reg_path.is_file():
        return False
    try:
        data = json.loads(reg_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return False
    extensions = data.get("extensions")
    if not isinstance(extensions, dict):
        return False

    changed = False
    for _ext_id, meta in extensions.items():
        if not isinstance(meta, dict):
            continue
        rc = meta.get("registered_commands")
        if not isinstance(rc, dict):
            continue
        if target_agent in rc:
            continue
        source_list: list[str] | None = None
        for key in ("claude", "codex", "cursor-agent", "kilocode"):
            if key == target_agent:
                continue
            val = rc.get(key)
            if isinstance(val, list) and val:
                source_list = list(val)
                break
        if source_list is None:
            for _k, v in rc.items():
                if isinstance(v, list) and v:
                    source_list = list(v)
                    break
        if source_list:
            rc[target_agent] = list(source_list)
            changed = True

    if changed:
        reg_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return changed
