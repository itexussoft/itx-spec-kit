#!/usr/bin/env python3
"""Validate catalog references and manifest version consistency."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import yaml


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog" / "index.json"


def nested_version_of(path: Path, root_key: str) -> Optional[str]:
    if path.suffix not in {".yml", ".yaml"}:
        return None
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        return None
    root = data.get(root_key)
    if not isinstance(root, dict):
        return None
    return str(root.get("version", "")).strip() or None


def main() -> int:
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    kit_version = data["kit"]["version"]
    errors = []

    for preset in data["artifacts"]["presets"]:
        artifact_path = ROOT / preset["path"]
        if not artifact_path.exists():
            errors.append(f"Missing preset path: {artifact_path}")
            continue
        preset_yml = artifact_path / "preset.yml"
        if not preset_yml.exists():
            errors.append(f"Missing preset descriptor: {preset_yml}")
            continue
        try:
            doc = yaml.safe_load(preset_yml.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            errors.append(f"Invalid YAML in {preset_yml}: {exc}")
            continue
        if not isinstance(doc, dict):
            errors.append(f"Preset document must be a mapping: {preset_yml}")
            continue
        preset_root = doc.get("preset")
        if not isinstance(preset_root, dict):
            errors.append(f"Missing preset.preset mapping: {preset_yml}")
            continue
        nested = str(preset_root.get("version", "")).strip() or None
        if nested != kit_version:
            errors.append(
                f"Version mismatch for preset '{preset['name']}': "
                f"preset.yml preset.version={nested!r} catalog={kit_version!r}"
            )
        provides = doc.get("provides")
        templates = provides.get("templates") if isinstance(provides, dict) else None
        if not isinstance(templates, list) or len(templates) < 1:
            errors.append(
                f"Preset '{preset['name']}' must declare provides.templates with at least one entry "
                f"(specify-cli 0.5+): {preset_yml}"
            )

    for extension in data["artifacts"]["extensions"]:
        artifact_path = ROOT / extension["path"]
        if not artifact_path.exists():
            errors.append(f"Missing extension path: {artifact_path}")
            continue
        extension_yml = artifact_path / "extension.yml"
        if not extension_yml.exists():
            errors.append(f"Missing extension descriptor: {extension_yml}")
            continue
        nested = nested_version_of(extension_yml, "extension")
        if nested != kit_version:
            errors.append(
                f"Version mismatch for extension '{extension['name']}': "
                f"extension.yml extension.version={nested!r} catalog={kit_version!r}"
            )

    if errors:
        for err in errors:
            sys.stderr.write(f"[catalog-check] {err}\n")
        return 1

    print("[catalog-check] Catalog and descriptors are consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
