import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import patch as patch_mod  # noqa: E402


class PatchTests(unittest.TestCase):
    def _make_bootstrapped_workspace(self, tmp: str) -> Path:
        ws = Path(tmp) / "project"
        ws.mkdir()
        (ws / ".itx-config.yml").write_text(
            'domain: "base"\nexecution_mode: "mcp"\nknowledge:\n  mode: "lazy"\n',
            encoding="utf-8",
        )
        ext = ws / ".specify" / "extensions" / "itx-gates" / "hooks"
        ext.mkdir(parents=True)
        (ext / "orchestrator.py").write_text("# old\n", encoding="utf-8")
        (ws / ".specify" / "constitution.md").write_text("# old\n", encoding="utf-8")
        (ws / ".specify" / "policy.yml").write_text("# old\n", encoding="utf-8")
        (ws / "docs" / "knowledge-base").mkdir(parents=True)
        return ws

    # ---- Kit-owned files: always overwritten ----

    def test_patch_updates_extension_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._make_bootstrapped_workspace(tmp)
            total, _ = patch_mod.patch_workspace(ROOT, ws)
            self.assertGreater(total, 0)
            runner = ws / ".specify" / "extensions" / "itx-gates" / "commands" / "run_speckit.py"
            self.assertTrue(runner.exists())

    def test_patch_creates_cursor_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._make_bootstrapped_workspace(tmp)
            patch_mod.patch_workspace(ROOT, ws)
            rule = ws / ".cursor" / "rules" / "itx-speckit-commands.mdc"
            self.assertTrue(rule.exists())
            self.assertIn("runner adapter", rule.read_text(encoding="utf-8"))

    # ---- Editable files: default mode writes .kit-update, not overwrite ----

    def test_default_mode_does_not_overwrite_constitution(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._make_bootstrapped_workspace(tmp)
            patch_mod.patch_workspace(ROOT, ws)
            text = (ws / ".specify" / "constitution.md").read_text(encoding="utf-8")
            self.assertEqual(text, "# old\n")
            kit_update = ws / ".specify" / "constitution.md.kit-update"
            self.assertTrue(kit_update.exists())
            self.assertIn("Itexus Base Constitution", kit_update.read_text(encoding="utf-8"))

    def test_default_mode_does_not_overwrite_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._make_bootstrapped_workspace(tmp)
            patch_mod.patch_workspace(ROOT, ws)
            text = (ws / ".specify" / "policy.yml").read_text(encoding="utf-8")
            self.assertEqual(text, "# old\n")
            kit_update = ws / ".specify" / "policy.yml.kit-update"
            self.assertTrue(kit_update.exists())

    def test_default_mode_returns_merge_instructions(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._make_bootstrapped_workspace(tmp)
            _, merge_needed = patch_mod.patch_workspace(ROOT, ws)
            self.assertGreater(len(merge_needed), 0)
            joined = "\n".join(merge_needed)
            self.assertIn("constitution.md", joined)

    def test_default_mode_creates_editable_if_missing(self):
        """If an editable file doesn't exist yet, it gets created directly."""
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._make_bootstrapped_workspace(tmp)
            (ws / ".specify" / "constitution.md").unlink()
            patch_mod.patch_workspace(ROOT, ws)
            self.assertTrue((ws / ".specify" / "constitution.md").exists())
            self.assertFalse((ws / ".specify" / "constitution.md.kit-update").exists())

    def test_default_mode_skips_identical_editable(self):
        """If editable file already matches kit source, no .kit-update is created."""
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._make_bootstrapped_workspace(tmp)
            kit_src = ROOT / "presets" / "base" / "constitution.md"
            (ws / ".specify" / "constitution.md").write_bytes(kit_src.read_bytes())
            _, merge_needed = patch_mod.patch_workspace(ROOT, ws)
            self.assertFalse((ws / ".specify" / "constitution.md.kit-update").exists())
            joined = "\n".join(merge_needed)
            self.assertNotIn("constitution.md", joined)

    # ---- Force mode: overwrite with backup ----

    def test_force_mode_overwrites_constitution_with_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._make_bootstrapped_workspace(tmp)
            patch_mod.patch_workspace(ROOT, ws, force=True)
            text = (ws / ".specify" / "constitution.md").read_text(encoding="utf-8")
            self.assertIn("Itexus Base Constitution", text)
            backup = ws / ".specify" / "constitution.md.patch-backup"
            self.assertTrue(backup.exists())
            self.assertEqual(backup.read_text(encoding="utf-8"), "# old\n")

    def test_force_mode_overwrites_policy_with_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._make_bootstrapped_workspace(tmp)
            patch_mod.patch_workspace(ROOT, ws, force=True)
            backup = ws / ".specify" / "policy.yml.patch-backup"
            self.assertTrue(backup.exists())
            self.assertEqual(backup.read_text(encoding="utf-8"), "# old\n")

    def test_force_mode_returns_no_merge_instructions(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._make_bootstrapped_workspace(tmp)
            _, merge_needed = patch_mod.patch_workspace(ROOT, ws, force=True)
            self.assertEqual(len(merge_needed), 0)

    # ---- Idempotency ----

    def test_patch_idempotent_default_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._make_bootstrapped_workspace(tmp)
            first, _ = patch_mod.patch_workspace(ROOT, ws)
            self.assertGreater(first, 0)
            second, _ = patch_mod.patch_workspace(ROOT, ws)
            self.assertEqual(second, 0)

    def test_patch_idempotent_force_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._make_bootstrapped_workspace(tmp)
            first, _ = patch_mod.patch_workspace(ROOT, ws, force=True)
            self.assertGreater(first, 0)
            second, _ = patch_mod.patch_workspace(ROOT, ws, force=True)
            self.assertEqual(second, 0)

    # ---- Config ----

    def test_patch_adds_spec_kit_ref_to_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._make_bootstrapped_workspace(tmp)
            patch_mod.patch_workspace(ROOT, ws)
            text = (ws / ".itx-config.yml").read_text(encoding="utf-8")
            self.assertIn("spec_kit_ref:", text)

    def test_patch_preserves_existing_spec_kit_ref(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._make_bootstrapped_workspace(tmp)
            cfg = ws / ".itx-config.yml"
            cfg.write_text(
                cfg.read_text(encoding="utf-8") + 'spec_kit_ref: "custom-ref"\n',
                encoding="utf-8",
            )
            patch_mod.patch_workspace(ROOT, ws)
            text = cfg.read_text(encoding="utf-8")
            self.assertIn("custom-ref", text)
            self.assertEqual(text.count("spec_kit_ref:"), 1)

    # ---- Templates ----

    def test_patch_installs_templates(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._make_bootstrapped_workspace(tmp)
            patch_mod.patch_workspace(ROOT, ws)
            tasks_tpl = ws / ".specify" / "templates" / "tasks-template.md"
            self.assertTrue(tasks_tpl.exists())
            self.assertIn("- [ ]", tasks_tpl.read_text(encoding="utf-8"))

    # ---- fix_tasks_checkboxes ----

    def test_fix_tasks_converts_bare_list_items(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._make_bootstrapped_workspace(tmp)
            (ws / "specs" / "feature-a").mkdir(parents=True)
            tasks = ws / "specs" / "feature-a" / "tasks.md"
            tasks.write_text(
                "# Tasks\n- T001 Implement domain layer\n- T002 Write tests\n",
                encoding="utf-8",
            )
            fixed = patch_mod.fix_tasks_checkboxes(ws)
            self.assertEqual(fixed, 1)
            text = tasks.read_text(encoding="utf-8")
            self.assertIn("- [ ] T001 Implement domain layer", text)
            self.assertIn("- [ ] T002 Write tests", text)

    def test_fix_tasks_preserves_existing_checkboxes(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._make_bootstrapped_workspace(tmp)
            (ws / "specs" / "feature-a").mkdir(parents=True)
            tasks = ws / "specs" / "feature-a" / "tasks.md"
            tasks.write_text(
                "# Tasks\n- [ ] Pending task\n- [x] Done task\n",
                encoding="utf-8",
            )
            fixed = patch_mod.fix_tasks_checkboxes(ws)
            self.assertEqual(fixed, 0)
            text = tasks.read_text(encoding="utf-8")
            self.assertIn("- [ ] Pending task", text)
            self.assertIn("- [x] Done task", text)

    def test_fix_tasks_handles_mixed_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._make_bootstrapped_workspace(tmp)
            (ws / "specs" / "feature-a").mkdir(parents=True)
            tasks = ws / "specs" / "feature-a" / "tasks.md"
            tasks.write_text(
                "# Tasks\n- [ ] T000 Already good\n- T001 Bare item\n",
                encoding="utf-8",
            )
            fixed = patch_mod.fix_tasks_checkboxes(ws)
            self.assertEqual(fixed, 1)
            text = tasks.read_text(encoding="utf-8")
            self.assertIn("- [ ] T000 Already good", text)
            self.assertIn("- [ ] T001 Bare item", text)

    def test_fix_tasks_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._make_bootstrapped_workspace(tmp)
            (ws / "specs" / "feature-a").mkdir(parents=True)
            tasks = ws / "specs" / "feature-a" / "tasks.md"
            tasks.write_text("# Tasks\n- T001 Bare item\n", encoding="utf-8")
            patch_mod.fix_tasks_checkboxes(ws)
            first_text = tasks.read_text(encoding="utf-8")
            fixed = patch_mod.fix_tasks_checkboxes(ws)
            self.assertEqual(fixed, 0)
            self.assertEqual(tasks.read_text(encoding="utf-8"), first_text)

    def test_fix_tasks_ignores_instructional_bullets(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._make_bootstrapped_workspace(tmp)
            (ws / "specs" / "feature-a").mkdir(parents=True)
            tasks = ws / "specs" / "feature-a" / "tasks.md"
            tasks.write_text(
                "# Format Rules\n- Include exact file paths\n- Keep tasks independent\n",
                encoding="utf-8",
            )
            fixed = patch_mod.fix_tasks_checkboxes(ws)
            self.assertEqual(fixed, 0)
            self.assertEqual(
                tasks.read_text(encoding="utf-8"),
                "# Format Rules\n- Include exact file paths\n- Keep tasks independent\n",
            )

    # ---- Validation ----

    def test_patch_rejects_non_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = patch_mod.main(["--workspace", tmp])
            self.assertEqual(result, 1)


class RunSpeckitTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(ROOT / "extensions" / "itx-gates" / "commands"))

    def _import(self):
        import run_speckit  # noqa: E402
        return run_speckit

    def test_run_speckit_cli_detection_returns_none_when_nothing(self):
        run_speckit = self._import()
        from unittest.mock import patch as mock_patch

        with mock_patch("run_speckit.shutil.which", return_value=None):
            self.assertIsNone(run_speckit._detect_cli())

    def test_run_speckit_cli_detection_skips_stock_specify(self):
        """specify is skipped when it cannot dispatch extension commands."""
        run_speckit = self._import()
        from unittest.mock import patch as mock_patch, MagicMock

        def fake_which(cmd):
            return "/usr/bin/specify" if cmd == "specify" else (
                "/usr/bin/uvx" if cmd == "uvx" else None
            )

        fake_probe = MagicMock(return_value=MagicMock(returncode=2))

        with (
            mock_patch("run_speckit.shutil.which", side_effect=fake_which),
            mock_patch("run_speckit.subprocess.run", fake_probe),
        ):
            result = run_speckit._detect_cli()

        self.assertEqual(result, "uvx")
        fake_probe.assert_called_once()

    def test_run_speckit_cli_detection_uses_specify_when_extensions_ok(self):
        """specify is used when extension list succeeds."""
        run_speckit = self._import()
        from unittest.mock import patch as mock_patch, MagicMock

        def fake_which(cmd):
            return "/usr/bin/specify" if cmd == "specify" else None

        fake_probe = MagicMock(return_value=MagicMock(returncode=0))

        with (
            mock_patch("run_speckit.shutil.which", side_effect=fake_which),
            mock_patch("run_speckit.subprocess.run", fake_probe),
        ):
            result = run_speckit._detect_cli()

        self.assertEqual(result, "specify")

    def test_run_speckit_cli_override(self):
        """--cli override bypasses auto-detection."""
        run_speckit = self._import()
        from unittest.mock import patch as mock_patch

        with mock_patch("run_speckit.shutil.which", return_value="/usr/bin/uvx"):
            result = run_speckit._detect_cli(cli_override="uvx")

        self.assertEqual(result, "uvx")

    def test_run_speckit_cli_override_missing_returns_none(self):
        run_speckit = self._import()
        from unittest.mock import patch as mock_patch

        with mock_patch("run_speckit.shutil.which", return_value=None):
            result = run_speckit._detect_cli(cli_override="spec-kit")

        self.assertIsNone(result)

    def test_run_speckit_build_command_uvx(self):
        run_speckit = self._import()
        cmd = run_speckit._build_command("uvx", "review.run", Path("/ws"), run_speckit.DEFAULT_SPEC_KIT_REF)
        self.assertIn("uvx", cmd)
        self.assertIn("review.run", cmd)
        self.assertIn(run_speckit.DEFAULT_SPEC_KIT_REF, cmd[2])

    def test_run_speckit_build_command_specify(self):
        run_speckit = self._import()
        cmd = run_speckit._build_command("specify", "cleanup.run", Path("/ws"), run_speckit.DEFAULT_SPEC_KIT_REF)
        self.assertEqual(cmd, ["specify", "cleanup.run"])

    def test_run_speckit_build_command_spec_kit(self):
        run_speckit = self._import()
        cmd = run_speckit._build_command("spec-kit", "review.run", Path("/ws"), run_speckit.DEFAULT_SPEC_KIT_REF)
        self.assertEqual(cmd, ["spec-kit", "review.run", "--path", "/ws"])

    def test_run_speckit_load_ref_default(self):
        run_speckit = self._import()
        with tempfile.TemporaryDirectory() as tmp:
            ref = run_speckit._load_spec_kit_ref(Path(tmp))
            self.assertEqual(ref, run_speckit.DEFAULT_SPEC_KIT_REF)

    def test_run_speckit_load_ref_from_config(self):
        run_speckit = self._import()
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / ".itx-config.yml").write_text(
                'domain: "base"\nspec_kit_ref: "custom-sha"\n',
                encoding="utf-8",
            )
            ref = run_speckit._load_spec_kit_ref(ws)
            self.assertEqual(ref, "custom-sha")

    # ---- Local resolution ----

    def _make_extension_workspace(self, tmp: str) -> Path:
        """Create a minimal workspace with a registered cleanup extension."""
        import json as _json
        ws = Path(tmp) / "project"
        ws.mkdir()
        ext = ws / ".specify" / "extensions" / "cleanup"
        ext.mkdir(parents=True)
        (ext / "commands").mkdir()
        (ext / "commands" / "cleanup.md").write_text(
            "---\ndescription: test prompt\n---\n## Goal\nDo cleanup.\n",
            encoding="utf-8",
        )
        (ext / "extension.yml").write_text(
            'schema_version: "1.0"\n'
            "provides:\n"
            "  commands:\n"
            '    - name: "speckit.cleanup.run"\n'
            '      file: "commands/cleanup.md"\n'
            '      aliases: ["speckit.cleanup"]\n',
            encoding="utf-8",
        )
        registry = {
            "schema_version": "1.0",
            "extensions": {
                "cleanup": {
                    "version": "1.0.0",
                    "enabled": True,
                    "registered_commands": {
                        "cursor": ["speckit.cleanup.run", "speckit.cleanup"]
                    },
                }
            },
        }
        reg_path = ws / ".specify" / "extensions" / ".registry"
        reg_path.write_text(_json.dumps(registry), encoding="utf-8")
        return ws

    def test_resolve_local_finds_command(self):
        run_speckit = self._import()
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._make_extension_workspace(tmp)
            result = run_speckit._resolve_local(ws, "cleanup.run")
            self.assertIsNotNone(result)
            self.assertTrue(result.exists())
            self.assertIn("Do cleanup.", result.read_text(encoding="utf-8"))

    def test_resolve_local_finds_command_with_prefix(self):
        run_speckit = self._import()
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._make_extension_workspace(tmp)
            result = run_speckit._resolve_local(ws, "speckit.cleanup.run")
            self.assertIsNotNone(result)

    def test_resolve_local_finds_alias(self):
        run_speckit = self._import()
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._make_extension_workspace(tmp)
            result = run_speckit._resolve_local(ws, "cleanup")
            self.assertIsNotNone(result)

    def test_resolve_local_returns_none_for_unknown_command(self):
        run_speckit = self._import()
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._make_extension_workspace(tmp)
            result = run_speckit._resolve_local(ws, "nonexistent.run")
            self.assertIsNone(result)

    def test_resolve_local_returns_none_without_registry(self):
        run_speckit = self._import()
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            result = run_speckit._resolve_local(ws, "cleanup.run")
            self.assertIsNone(result)

    def test_resolve_local_skips_disabled_extension(self):
        import json as _json
        run_speckit = self._import()
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._make_extension_workspace(tmp)
            reg_path = ws / ".specify" / "extensions" / ".registry"
            registry = _json.loads(reg_path.read_text(encoding="utf-8"))
            registry["extensions"]["cleanup"]["enabled"] = False
            reg_path.write_text(_json.dumps(registry), encoding="utf-8")
            result = run_speckit._resolve_local(ws, "cleanup.run")
            self.assertIsNone(result)

    def test_canonicalize(self):
        run_speckit = self._import()
        self.assertEqual(run_speckit._canonicalize("cleanup.run"), "speckit.cleanup.run")
        self.assertEqual(run_speckit._canonicalize("speckit.cleanup.run"), "speckit.cleanup.run")

    def test_main_falls_back_to_local_when_no_cli(self):
        """main() resolves locally and prints prompt envelope when no CLI exists."""
        run_speckit = self._import()
        from unittest.mock import patch as mock_patch
        import io

        with tempfile.TemporaryDirectory() as tmp:
            ws = self._make_extension_workspace(tmp)
            captured = io.StringIO()
            with (
                mock_patch("run_speckit.shutil.which", return_value=None),
                mock_patch("sys.stdout", captured),
            ):
                rc = run_speckit.main([
                    "--command", "cleanup.run",
                    "--workspace", str(ws),
                ])
            self.assertEqual(rc, 0)
            output = captured.getvalue()
            self.assertIn(run_speckit.PROMPT_BEGIN, output)
            self.assertIn(run_speckit.PROMPT_END, output)
            self.assertIn("Do cleanup.", output)

    def test_main_returns_error_when_nothing_works(self):
        run_speckit = self._import()
        from unittest.mock import patch as mock_patch

        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            with mock_patch("run_speckit.shutil.which", return_value=None):
                rc = run_speckit.main([
                    "--command", "cleanup.run",
                    "--workspace", str(ws),
                ])
            self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
