#!/usr/bin/env python3
"""Generate knowledge-manifest.json from preset.yml metadata.

Called by init scripts to produce a workspace-local manifest that maps
every available knowledge file to its category and source path. The
orchestrator reads this manifest for structured hydration instead of
scanning directories.

Usage:
    python build_knowledge_manifest.py \
        --output /path/to/.specify/knowledge-manifest.json \
        --kit-root /path/to/itexus-spec-kit \
        --domain fintech-trading
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml


def _collect_entries(preset_dir: Path, preset_data: dict) -> list[dict]:
    provides = preset_data.get("provides") or {}
    entries: list[dict] = []
    for category_key, category_name in [
        ("patterns", "patterns"),
        ("design_patterns", "design-patterns"),
        ("anti_patterns", "anti-patterns"),
    ]:
        for item in provides.get(category_key) or []:
            file_rel = str(item.get("file", "")).strip()
            if not file_rel:
                continue
            source = preset_dir / file_rel
            entries.append(
                {
                    "name": Path(file_rel).name,
                    "category": category_name,
                    "source": str(source),
                    "description": str(item.get("description", "")).strip(),
                }
            )
    return entries


def build_manifest(kit_root: Path, domain: str) -> dict:
    entries: list[dict] = []
    base_yml = kit_root / "presets" / "base" / "preset.yml"
    if base_yml.exists():
        data = yaml.safe_load(base_yml.read_text(encoding="utf-8")) or {}
        entries.extend(_collect_entries(kit_root / "presets" / "base", data))

    if domain != "base":
        domain_yml = kit_root / "presets" / domain / "preset.yml"
        if domain_yml.exists():
            data = yaml.safe_load(domain_yml.read_text(encoding="utf-8")) or {}
            entries.extend(_collect_entries(kit_root / "presets" / domain, data))

    by_name: dict[str, dict] = {}
    for entry in entries:
        by_name[entry["name"]] = entry

    return {
        "schema_version": "1.0",
        "domain": domain,
        "kit_root": str(kit_root),
        "files": by_name,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build knowledge manifest")
    parser.add_argument("--output", required=True, help="Output JSON path")
    parser.add_argument("--kit-root", required=True, help="Root of itexus-spec-kit")
    parser.add_argument("--domain", default="base", help="Domain preset")
    args = parser.parse_args()

    kit_root = Path(args.kit_root).resolve()
    manifest = build_manifest(kit_root, args.domain)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"[build-knowledge-manifest] Wrote {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
