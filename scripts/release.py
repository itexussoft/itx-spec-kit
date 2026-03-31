#!/usr/bin/env python3
"""Bump kit version across catalog and artifact descriptors."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bump release versions consistently")
    parser.add_argument("--version", required=True, help="New semantic version, e.g. 0.2.0")
    parser.add_argument("--build", action="store_true", help="Build dist artifacts after bump")
    parser.add_argument("--root", default="", help="Optional repository root override")
    return parser.parse_args()


def validate_version(version: str) -> None:
    if not re.match(r"^\d+\.\d+\.\d+$", version):
        raise ValueError(f"Invalid version '{version}'. Expected semantic format X.Y.Z")


def update_nested_yaml_version(path: Path, root_key: str, version: str) -> None:
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"(^{re.escape(root_key)}:\s*\n(?:^[ \t].*\n)*?^[ \t]+version:\s*)([^\n]+)$",
        re.MULTILINE,
    )
    if not pattern.search(text):
        raise ValueError(f"Missing nested version field for '{root_key}' in {path}")
    updated = pattern.sub(rf"\g<1>{version}", text, count=1)
    path.write_text(updated, encoding="utf-8")


def main() -> int:
    args = parse_args()
    validate_version(args.version)
    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[1]
    catalog_path = root / "catalog" / "index.json"

    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    catalog["kit"]["version"] = args.version
    catalog_path.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")

    artifact_paths = [item["path"] for item in catalog["artifacts"]["presets"]]
    artifact_paths.extend(item["path"] for item in catalog["artifacts"]["extensions"])
    for rel in artifact_paths:
        artifact_root = root / rel
        preset_yaml = artifact_root / "preset.yml"
        if preset_yaml.exists():
            update_nested_yaml_version(preset_yaml, "preset", args.version)

        extension_yaml = artifact_root / "extension.yml"
        if extension_yaml.exists():
            update_nested_yaml_version(extension_yaml, "extension", args.version)

    print(f"Bumped kit/artifact versions to {args.version}")

    validate_cmd = [sys.executable, str(root / "scripts" / "validate_catalog.py")]
    result = subprocess.run(validate_cmd, check=False)
    if result.returncode != 0:
        return result.returncode

    if args.build:
        build_cmd = [sys.executable, str(root / "scripts" / "build_catalog_artifacts.py")]
        result = subprocess.run(build_cmd, check=False)
        return result.returncode

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        sys.stderr.write(f"[release] {exc}\n")
        raise SystemExit(1)
