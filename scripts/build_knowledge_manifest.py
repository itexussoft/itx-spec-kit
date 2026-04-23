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
import re
import sys
from pathlib import Path

import yaml


_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n?", re.DOTALL)


def _split_frontmatter(markdown: str) -> tuple[dict, str]:
    match = _FRONTMATTER_RE.match(markdown)
    if not match:
        return {}, markdown
    try:
        parsed = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        parsed = {}
    if not isinstance(parsed, dict):
        parsed = {}
    return parsed, markdown[match.end() :]


def _to_slug_tokens(value: str) -> list[str]:
    cleaned = re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
    return [token for token in cleaned.split() if token]


def _derive_tags(*, name: str, description: str, category: str, frontmatter: dict) -> list[str]:
    raw_tags = frontmatter.get("tags")
    if isinstance(raw_tags, list):
        tags = [str(tag).strip().lower() for tag in raw_tags if str(tag).strip()]
        if tags:
            return sorted(dict.fromkeys(tags))

    tags: list[str] = []
    tags.extend(_to_slug_tokens(name.replace(".md", "")))
    tags.extend(_to_slug_tokens(description))
    tags.append(category)
    if "event" in tags:
        tags.extend(["events", "event-driven"])
    if "api" in tags:
        tags.extend(["controller", "endpoint"])
    if "ledger" in tags:
        tags.extend(["db", "sql", "transaction"])
    if "frontend" in tags:
        tags.extend(["ui", "component"])
    return sorted(dict.fromkeys(tag for tag in tags if tag))


def _derive_phases(frontmatter: dict) -> list[str]:
    raw_phases = frontmatter.get("phases")
    if isinstance(raw_phases, list):
        phases = [str(phase).strip() for phase in raw_phases if str(phase).strip()]
        if phases:
            return sorted(dict.fromkeys(phases))
    return ["after_plan", "after_tasks", "after_review"]


def _derive_token_estimate(frontmatter: dict, body_text: str) -> int:
    raw = frontmatter.get("token_estimate")
    if isinstance(raw, int) and raw > 0:
        return raw
    words = len(re.findall(r"\S+", body_text))
    # Approximate token budget for English prose.
    estimate = max(80, int(words * 1.35))
    return estimate


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
            markdown = source.read_text(encoding="utf-8", errors="ignore") if source.exists() else ""
            frontmatter, body = _split_frontmatter(markdown)
            tags = _derive_tags(
                name=Path(file_rel).name,
                description=str(item.get("description", "")).strip(),
                category=category_name,
                frontmatter=frontmatter,
            )
            phases = _derive_phases(frontmatter)
            token_estimate = _derive_token_estimate(frontmatter, body)
            entries.append(
                {
                    "name": Path(file_rel).name,
                    "category": category_name,
                    "source": str(source),
                    "description": str(item.get("description", "")).strip(),
                    "tags": tags,
                    "phases": phases,
                    "token_estimate": token_estimate,
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
        "schema_version": "1.1",
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
