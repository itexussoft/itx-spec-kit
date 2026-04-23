"""github/spec-kit adapter implementation for core orchestration."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from core_orchestrator.base import CoreOrchestrator


@dataclass
class GithubSpecKitOrchestrator(CoreOrchestrator):
    """Adapter around current CLI probing and local command-resolution behavior."""

    load_spec_kit_ref: Callable[[Path], str]
    canonicalize: Callable[[str], str]
    resolve_local: Callable[[Path, str], Path | None]
    detect_cli: Callable[[Optional[str]], str | None]
    can_dispatch: Callable[[], bool]
    build_command: Callable[[str, str, Path, str], list[str]]
    prompt_begin: str
    prompt_end: str

    def specify(self, workspace: Path) -> int:
        return self._run_transition("speckit.specify", workspace)

    def plan(self, workspace: Path) -> int:
        return self._run_transition("speckit.plan", workspace)

    def implement(self, workspace: Path) -> int:
        return self._run_transition("speckit.implement", workspace)

    def _run_transition(self, command: str, workspace: Path) -> int:
        result = self.run_extension_command(command=command, workspace=workspace)
        return int(result.get("returncode", 1))

    def detect_capabilities(self, workspace: Path) -> Dict[str, Any]:
        _ = workspace
        cli = self.detect_cli(None)
        return {
            "cli": cli,
            "can_dispatch_extension_commands": bool(cli in {"spec-kit"} or (cli in {"specify", "uvx"} and self.can_dispatch())),
        }

    def run_extension_command(
        self,
        *,
        command: str,
        workspace: Path,
        cli_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        cli = self.detect_cli(cli_override)
        cli_exit: int | None = None
        spec_kit_ref = self.load_spec_kit_ref(workspace)
        canonical = self.canonicalize(command)
        used_cli = False

        if cli is not None and canonical.startswith("speckit.") and cli in {"specify", "uvx"} and not self.can_dispatch():
            sys.stderr.write(f"[run-speckit] {cli} cannot dispatch extension commands — using local resolution\n")
            cli = None

        if cli is not None:
            used_cli = True
            cmd = self.build_command(cli, command, workspace, spec_kit_ref)
            sys.stderr.write(f"[run-speckit] Using CLI: {cli}\n")
            sys.stderr.write(f"[run-speckit] Running: {' '.join(cmd)}\n")
            cwd = str(workspace) if cli in {"specify", "uvx"} else None
            cli_exit = subprocess.run(cmd, cwd=cwd).returncode
            if cli_exit == 0:
                return {
                    "mode": "cli",
                    "cli": cli,
                    "returncode": 0,
                    "command": command,
                    "workspace": str(workspace),
                }
            sys.stderr.write(f"[run-speckit] CLI exited {cli_exit} — trying local resolution\n")

        prompt_path = self.resolve_local(workspace, command)
        if prompt_path is not None:
            rel = prompt_path.relative_to(workspace)
            sys.stderr.write(f"[run-speckit] Resolved locally: {rel}\n")
            content = prompt_path.read_text(encoding="utf-8")
            sys.stdout.write(f"{self.prompt_begin}\n{content}\n{self.prompt_end}\n")
            return {
                "mode": "local",
                "returncode": 0,
                "command": command,
                "workspace": str(workspace),
                "prompt_path": str(prompt_path),
            }

        if not used_cli:
            sys.stderr.write(
                "[run-speckit] No Spec-Kit CLI found and local resolution failed.\n"
                "  Install one of: spec-kit, specify (specify-cli), or uvx.\n"
                "  With uvx:  pip install uv   (or see https://docs.astral.sh/uv/)\n"
            )
        else:
            sys.stderr.write(
                f"[run-speckit] CLI failed (exit {cli_exit}) and command "
                f"'{command}' not found in local extension registry.\n"
            )
        return {
            "mode": "failed",
            "returncode": 1,
            "command": command,
            "workspace": str(workspace),
            "cli": cli,
            "cli_exit": cli_exit,
        }

