#!/usr/bin/env python3
"""Validate catalog references and manifest version consistency."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

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


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_smell_catalog(path: Path, errors: List[str]) -> None:
    if not path.exists():
        errors.append(f"Missing smell catalog: {path}")
        return
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        errors.append(f"Invalid YAML in {path}: {exc}")
        return
    if not isinstance(payload, dict):
        errors.append(f"Smell catalog must be a mapping: {path}")
        return

    version = payload.get("version")
    if not isinstance(version, int) or version < 1:
        errors.append(f"Smell catalog version must be a positive integer: {path}")

    smells = payload.get("smells")
    if not isinstance(smells, list) or not smells:
        errors.append(f"Smell catalog must declare a non-empty smells list: {path}")
        return

    seen_ids: set[str] = set()
    for index, smell in enumerate(smells, start=1):
        pointer = f"{path} (smells[{index-1}])"
        if not isinstance(smell, dict):
            errors.append(f"Smell entry must be a mapping: {pointer}")
            continue

        smell_id = smell.get("id")
        if not _is_non_empty_string(smell_id):
            errors.append(f"Smell id is required: {pointer}")
            continue
        normalized_id = str(smell_id).strip()
        if normalized_id in seen_ids:
            errors.append(f"Duplicate smell id '{normalized_id}': {path}")
        seen_ids.add(normalized_id)

        if not _is_non_empty_string(smell.get("fowler_name")):
            errors.append(f"fowler_name is required: {pointer}")

        refactorings = smell.get("refactorings")
        if not isinstance(refactorings, list) or not refactorings:
            errors.append(f"refactorings must be a non-empty list: {pointer}")
        else:
            for ridx, refactoring in enumerate(refactorings, start=1):
                rptr = f"{pointer} refactorings[{ridx-1}]"
                if not isinstance(refactoring, dict):
                    errors.append(f"Refactoring entry must be a mapping: {rptr}")
                    continue
                if not _is_non_empty_string(refactoring.get("id")):
                    errors.append(f"Refactoring id is required: {rptr}")
                if not _is_non_empty_string(refactoring.get("intent")):
                    errors.append(f"Refactoring intent is required: {rptr}")
                url = refactoring.get("url")
                if not _is_non_empty_string(url) or not str(url).strip().startswith("http"):
                    errors.append(f"Refactoring url must be an absolute URL: {rptr}")
                priority = refactoring.get("priority")
                if not isinstance(priority, int) or priority < 1:
                    errors.append(f"Refactoring priority must be a positive integer: {rptr}")

        detectors = smell.get("detectors")
        if not isinstance(detectors, dict):
            errors.append(f"detectors must be a mapping: {pointer}")
        else:
            for tool_name, rules in detectors.items():
                if not _is_non_empty_string(tool_name):
                    errors.append(f"Detector tool names must be non-empty strings: {pointer}")
                if not isinstance(rules, list):
                    errors.append(f"Detector entry for '{tool_name}' must be a list: {pointer}")
                    continue
                for rule in rules:
                    if not _is_non_empty_string(rule):
                        errors.append(f"Detector rules must be non-empty strings: {pointer}")

        test_first = smell.get("test_first")
        if not isinstance(test_first, dict):
            errors.append(f"test_first must be a mapping: {pointer}")
        else:
            if not _is_non_empty_string(test_first.get("strategy")):
                errors.append(f"test_first.strategy is required: {pointer}")
            if not _is_non_empty_string(test_first.get("hint")):
                errors.append(f"test_first.hint is required: {pointer}")

        if not _is_non_empty_string(smell.get("advisory")):
            errors.append(f"advisory is required: {pointer}")


def main() -> int:
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    kit_version = data["kit"]["version"]
    errors = []

    _validate_smell_catalog(ROOT / "presets" / "base" / "smell-catalog.yml", errors)

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
