#!/usr/bin/env python3
"""Generate pattern-index.md files from preset.yml metadata."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import yaml

ROOT = Path(__file__).resolve().parents[1]
PRESETS_DIR = ROOT / "presets"


def _rows(items: Iterable[dict]) -> list[str]:
    rows: list[str] = []
    for item in items:
        file_name = Path(str(item.get("file", "")).strip()).name
        description = str(item.get("description", "")).strip()
        if not file_name:
            continue
        if description:
            rows.append(f"- `{file_name}`: {description}")
        else:
            rows.append(f"- `{file_name}`")
    return rows


def render_index(preset_name: str, preset_data: dict) -> str:
    provides = preset_data.get("provides") or {}
    patterns = _rows(provides.get("patterns") or [])
    design_patterns = _rows(provides.get("design_patterns") or [])
    anti_patterns = _rows(provides.get("anti_patterns") or [])

    lines: list[str] = []
    lines.append(f"# Pattern Index ({preset_name})")
    lines.append("")

    lines.append("## Architectural Patterns")
    lines.extend(patterns or ["- None"])
    lines.append("")

    lines.append("## Code-Level Design Patterns")
    lines.extend(design_patterns or ["- None"])
    lines.append("")

    lines.append("## Anti-Patterns (Forbidden / Demoted)")
    lines.extend(anti_patterns or ["- None"])
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    for preset_dir in sorted(PRESETS_DIR.iterdir()):
        if not preset_dir.is_dir():
            continue
        preset_yml = preset_dir / "preset.yml"
        if not preset_yml.exists():
            continue

        preset_data = yaml.safe_load(preset_yml.read_text(encoding="utf-8")) or {}
        preset_name = str((preset_data.get("preset") or {}).get("id") or preset_dir.name)
        index_text = render_index(preset_name, preset_data)
        (preset_dir / "pattern-index.md").write_text(index_text, encoding="utf-8")
        print(f"Generated {preset_dir / 'pattern-index.md'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
