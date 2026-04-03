import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATE_SCRIPT = ROOT / "scripts" / "validate_catalog.py"


def load_validate_module():
    spec = importlib.util.spec_from_file_location("validate_catalog_module", VALIDATE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ValidateCatalogTests(unittest.TestCase):
    def make_workspace(self, tmp: Path) -> None:
        (tmp / "catalog").mkdir(parents=True, exist_ok=True)
        (tmp / "presets" / "base").mkdir(parents=True, exist_ok=True)
        (tmp / "presets" / "base" / "templates").mkdir(parents=True, exist_ok=True)
        (tmp / "presets" / "base" / "templates" / "stub.md").write_text("# stub\n", encoding="utf-8")
        (tmp / "extensions" / "itx-gates").mkdir(parents=True, exist_ok=True)
        (tmp / "catalog" / "index.json").write_text(
            json.dumps(
                {
                    "schemaVersion": "1.0",
                    "kit": {"name": "itx", "version": "0.1.0"},
                    "artifacts": {
                        "presets": [{"name": "base", "path": "presets/base"}],
                        "extensions": [{"name": "itx-gates", "path": "extensions/itx-gates"}],
                    },
                }
            ),
            encoding="utf-8",
        )
        (tmp / "presets" / "base" / "preset.yml").write_text(
            'schema_version: "1.0"\n'
            "preset:\n"
            '  id: "base"\n'
            '  version: "0.1.0"\n'
            "provides:\n"
            "  templates:\n"
            '    - type: "template"\n'
            '      name: "stub"\n'
            '      file: "templates/stub.md"\n'
            '      description: "catalog test stub"\n',
            encoding="utf-8",
        )
        (tmp / "extensions" / "itx-gates" / "extension.yml").write_text(
            'schema_version: "1.0"\nextension:\n  id: "itx-gates"\n  version: "0.1.0"\n',
            encoding="utf-8",
        )

    def run_main_with_workspace(self, ws: Path) -> int:
        module = load_validate_module()
        module.ROOT = ws
        module.CATALOG = ws / "catalog" / "index.json"
        return module.main()

    def test_validate_catalog_passes_when_all_versions_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            self.make_workspace(ws)
            self.assertEqual(self.run_main_with_workspace(ws), 0)

    def test_validate_catalog_fails_on_preset_nested_version_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            self.make_workspace(ws)
            (ws / "presets" / "base" / "preset.yml").write_text(
                'schema_version: "1.0"\n'
                "preset:\n"
                '  id: "base"\n'
                '  version: "0.1.9"\n'
                "provides:\n"
                "  templates:\n"
                '    - type: "template"\n'
                '      name: "stub"\n'
                '      file: "templates/stub.md"\n'
                '      description: "catalog test stub"\n',
                encoding="utf-8",
            )
            self.assertEqual(self.run_main_with_workspace(ws), 1)

    def test_validate_catalog_fails_on_missing_preset_yml(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            self.make_workspace(ws)
            (ws / "presets" / "base" / "preset.yml").unlink()
            self.assertEqual(self.run_main_with_workspace(ws), 1)

    def test_validate_catalog_fails_when_preset_has_no_templates(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            self.make_workspace(ws)
            (ws / "presets" / "base" / "preset.yml").write_text(
                'schema_version: "1.0"\npreset:\n  id: "base"\n  version: "0.1.0"\nprovides:\n  patterns: []\n',
                encoding="utf-8",
            )
            self.assertEqual(self.run_main_with_workspace(ws), 1)

    def test_validate_catalog_fails_on_extension_nested_version_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            self.make_workspace(ws)
            (ws / "extensions" / "itx-gates" / "extension.yml").write_text(
                'schema_version: "1.0"\nextension:\n  id: "itx-gates"\n  version: "0.2.0"\n',
                encoding="utf-8",
            )
            self.assertEqual(self.run_main_with_workspace(ws), 1)


if __name__ == "__main__":
    unittest.main()
