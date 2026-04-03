"""Validator package helpers for itx-gates."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Literal, Set, TypedDict

from typing_extensions import NotRequired


class Finding(TypedDict):
    severity: Literal["tier1", "tier2"]
    rule: str
    message: str
    confidence: NotRequired[str]
    remediation: NotRequired[str]
    remediation_owner: NotRequired[str]


EXCLUDED_DIRS: Set[str] = {
    "node_modules",
    "venv",
    ".venv",
    "dist",
    "build",
    "__pycache__",
    ".git",
    ".specify",
}


def should_skip_path(path: Path) -> bool:
    return any(part in EXCLUDED_DIRS or part.startswith(".") for part in path.parts)


def is_test_or_fixture_path(path: Path) -> bool:
    name = path.name.lower()
    if (
        name.startswith("test_")
        or name.endswith("_test.py")
        or name.endswith(".spec.ts")
        or name.endswith(".spec.js")
        or name.endswith(".test.ts")
        or name.endswith(".test.js")
    ):
        return True
    parts = {part.lower() for part in path.parts}
    return "tests" in parts or "fixtures" in parts or "__tests__" in parts


def collect_code_files(workspace: Path, suffixes: Iterable[str], skip_test_like: bool = False) -> List[Path]:
    files: List[Path] = []
    for suffix in suffixes:
        for file_path in workspace.rglob(f"*{suffix}"):
            if should_skip_path(file_path):
                continue
            if skip_test_like and is_test_or_fixture_path(file_path):
                continue
            files.append(file_path)
    return files
