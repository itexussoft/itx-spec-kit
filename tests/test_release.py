import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "scripts" / "release.py"


class ReleaseScriptTests(unittest.TestCase):
    def test_release_bumps_versions(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / "catalog").mkdir(parents=True, exist_ok=True)
            (ws / "presets" / "base").mkdir(parents=True, exist_ok=True)
            (ws / "extensions" / "itx-gates").mkdir(parents=True, exist_ok=True)
            (ws / "scripts").mkdir(parents=True, exist_ok=True)

            (ws / "catalog" / "index.json").write_text(
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
            (ws / "presets" / "base" / "preset.yml").write_text(
                'schema_version: "1.0"\n'
                "preset:\n"
                '  id: "base"\n'
                "  version: \"0.1.0\"\n",
                encoding="utf-8",
            )
            (ws / "extensions" / "itx-gates" / "extension.yml").write_text(
                'schema_version: "1.0"\n'
                "extension:\n"
                '  id: "itx-gates"\n'
                "  version: \"0.1.0\"\n",
                encoding="utf-8",
            )
            (ws / "scripts" / "validate_catalog.py").write_text(
                "print('[catalog-check] Catalog and descriptors are consistent.')\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                ["python3", str(RELEASE), "--version", "0.2.0", "--root", str(ws)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, msg=result.stderr)

            catalog = json.loads((ws / "catalog" / "index.json").read_text(encoding="utf-8"))
            self.assertEqual(catalog["kit"]["version"], "0.2.0")
            self.assertIn("version: 0.2.0", (ws / "presets" / "base" / "preset.yml").read_text(encoding="utf-8"))
            self.assertIn(
                "version: 0.2.0",
                (ws / "extensions" / "itx-gates" / "extension.yml").read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
