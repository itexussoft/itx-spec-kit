"""Core orchestrator interface for upstream command/runtime adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional, Protocol


class CoreOrchestrator(ABC):
    """Stable orchestration surface for upstream workflow engines."""

    @abstractmethod
    def specify(self, workspace: Path) -> int:
        """Execute the upstream specify transition."""

    @abstractmethod
    def plan(self, workspace: Path) -> int:
        """Execute the upstream plan transition."""

    @abstractmethod
    def implement(self, workspace: Path) -> int:
        """Execute the upstream implement transition."""

    @abstractmethod
    def run_extension_command(self, *, command: str, workspace: Path, cli_override: Optional[str] = None) -> Dict[str, Any]:
        """Execute an extension command with CLI + local fallback contract."""

    @abstractmethod
    def detect_capabilities(self, workspace: Path) -> Dict[str, Any]:
        """Return capability metadata for host/runtime decisions."""


class ResolverProtocol(Protocol):
    def __call__(self, workspace: Path, command: str) -> Path | None:  # pragma: no cover - protocol
        ...

