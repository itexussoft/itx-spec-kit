"""No-op security provider."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from validators import Finding


def run(workspace: Path, settings: Dict[str, Any]) -> List[Finding]:
    _ = workspace, settings
    return []

