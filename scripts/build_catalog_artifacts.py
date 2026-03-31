#!/usr/bin/env python3
"""Build release zip artifacts from catalog entries."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path


def add_directory_to_zip(ziph: zipfile.ZipFile, root: Path, rel_dir: Path) -> None:
    base = root / rel_dir
    for path in base.rglob("*"):
        if path.is_file():
            ziph.write(path, arcname=str(path.relative_to(root)))


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    catalog = json.loads((root / "catalog" / "index.json").read_text(encoding="utf-8"))
    version = catalog["kit"]["version"]

    dist = root / "dist"
    dist.mkdir(parents=True, exist_ok=True)
    for existing in dist.glob("*.zip"):
        existing.unlink()

    artifact_paths = [Path(item["path"]) for item in catalog["artifacts"]["presets"]]
    artifact_paths.extend(Path(item["path"]) for item in catalog["artifacts"]["extensions"])

    for rel in artifact_paths:
        out = dist / f"{rel.name}-{version}.zip"
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
            add_directory_to_zip(zf, root, rel)
        print(f"Created {out}")

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
