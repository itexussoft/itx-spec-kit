import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import itx_specify  # noqa: E402
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

    def test_patch_installs_brownfield_extension_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._make_bootstrapped_workspace(tmp)
            patch_mod.patch_workspace(ROOT, ws)
            ext_yml = ws / ".specify" / "extensions" / "itx-brownfield-workflows" / "extension.yml"
            cmd = ws / ".specify" / "extensions" / "itx-brownfield-workflows" / "commands" / "bugfix.md"
            self.assertTrue(ext_yml.exists())
            self.assertTrue(cmd.exists())

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
            self.assertIn('hook_mode: "hybrid"', text)

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

    def test_patch_preserves_existing_hook_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._make_bootstrapped_workspace(tmp)
            cfg = ws / ".itx-config.yml"
            cfg.write_text(
                cfg.read_text(encoding="utf-8") + 'hook_mode: "manual"\n',
                encoding="utf-8",
            )
            patch_mod.patch_workspace(ROOT, ws)
            text = cfg.read_text(encoding="utf-8")
            self.assertIn('hook_mode: "manual"', text)
            self.assertEqual(text.count("hook_mode:"), 1)

    # ---- Templates ----

    def test_patch_installs_templates(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._make_bootstrapped_workspace(tmp)
            patch_mod.patch_workspace(ROOT, ws)
            tasks_tpl = ws / ".specify" / "templates" / "tasks-template.md"
            migration_tpl = ws / ".specify" / "templates" / "migration-plan-template.md"
            spike_tpl = ws / ".specify" / "templates" / "spike-note-template.md"
            modify_tpl = ws / ".specify" / "templates" / "modify-plan-template.md"
            hotfix_tpl = ws / ".specify" / "templates" / "hotfix-report-template.md"
            deprecate_tpl = ws / ".specify" / "templates" / "deprecate-plan-template.md"
            self.assertTrue(tasks_tpl.exists())
            self.assertTrue(migration_tpl.exists())
            self.assertTrue(spike_tpl.exists())
            self.assertTrue(modify_tpl.exists())
            self.assertTrue(hotfix_tpl.exists())
            self.assertTrue(deprecate_tpl.exists())
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

    def test_retarget_ai_restores_constitution_after_mock_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "ws"
            spec = ws / ".specify"
            spec.mkdir(parents=True)
            (ws / ".itx-config.yml").write_text('spec_kit_ref: "v0.5.0"\n', encoding="utf-8")
            const = spec / "constitution.md"
            const.write_text("USER\n", encoding="utf-8")

            def fake_run(_cli, _argv, _ref, quiet=False, cwd=None):
                root = cwd if cwd is not None else ws
                c = root / ".specify" / "constitution.md"
                c.parent.mkdir(parents=True, exist_ok=True)
                c.write_text("SPECIFY\n", encoding="utf-8")

            with mock.patch("patch.detect_specify_cli", return_value="specify"):
                with mock.patch("patch.run_specify", side_effect=fake_run):
                    patch_mod.retarget_ai_workspace(
                        ws, "claude", None, refresh_templates=False, quiet=True
                    )

            self.assertEqual(const.read_text(encoding="utf-8"), "USER\n")
            cfg = yaml.safe_load((ws / ".itx-config.yml").read_text(encoding="utf-8"))
            self.assertEqual(cfg.get("agents", {}).get("primary"), "claude")
            self.assertIn("claude", cfg.get("agents", {}).get("installed", []))

    def test_add_ai_copies_agent_tree_and_appends_installed(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "ws"
            ws.mkdir()
            (ws / ".itx-config.yml").write_text("domain: base\n", encoding="utf-8")

            def fake_run(_cli, _argv, _ref, quiet=False, cwd=None):
                root = Path(cwd)
                wf = root / ".windsurf" / "workflows"
                wf.mkdir(parents=True)
                (wf / "speckit.plan.md").write_text("x", encoding="utf-8")

            with mock.patch("patch.detect_specify_cli", return_value="specify"):
                with mock.patch("patch.run_specify", side_effect=fake_run):
                    patch_mod.add_ai_workspace(ws, "windsurf", None, quiet=True)

            self.assertTrue((ws / ".windsurf" / "workflows" / "speckit.plan.md").exists())
            cfg = yaml.safe_load((ws / ".itx-config.yml").read_text(encoding="utf-8"))
            self.assertIn("windsurf", cfg.get("agents", {}).get("installed", []))

            with mock.patch("patch.detect_specify_cli", return_value="specify"):
                with mock.patch("patch.run_specify", side_effect=fake_run):
                    patch_mod.add_ai_workspace(ws, "windsurf", None, quiet=True)
            cfg = yaml.safe_load((ws / ".itx-config.yml").read_text(encoding="utf-8"))
            self.assertEqual(cfg["agents"]["installed"].count("windsurf"), 1)

    def test_post_agent_extension_sync_skips_when_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "ws"
            ws.mkdir()
            (ws / ".itx-config.yml").write_text("domain: base\n", encoding="utf-8")
            with mock.patch("patch.install_community_extensions") as ic:
                patch_mod.post_agent_extension_sync(
                    ws, ROOT, "kilocode", skip_extension_sync=True
                )
                ic.assert_not_called()

    def test_post_agent_extension_sync_runs_pipeline(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "ws"
            ws.mkdir()
            (ws / ".itx-config.yml").write_text("domain: base\n", encoding="utf-8")
            with mock.patch("patch.detect_specify_cli", return_value="specify"):
                with mock.patch("patch.install_community_extensions") as ic:
                    with mock.patch(
                        "patch.materialize_extension_workflows_for_agent", return_value=2
                    ) as mat:
                        with mock.patch(
                            "patch.materialize_extension_skills_for_agent", return_value=1
                        ) as skills:
                            with mock.patch(
                                "patch.mirror_registry_commands", return_value=True
                            ) as mir:
                                patch_mod.post_agent_extension_sync(
                                    ws, ROOT, "kilocode", skip_extension_sync=False
                                )
            ic.assert_called_once()
            mat.assert_called_once_with(ws, "kilocode")
            skills.assert_called_once_with(ws, "kilocode")
            mir.assert_called_once_with(ws, "kilocode")

    def test_main_retarget_ai_runs_extension_sync(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "ws"
            ws.mkdir()
            (ws / ".itx-config.yml").write_text("domain: base\n", encoding="utf-8")

            with mock.patch("patch.retarget_ai_workspace") as retarget:
                with mock.patch("patch.patch_workspace", return_value=(0, [])):
                    with mock.patch("patch.post_agent_extension_sync") as sync:
                        result = patch_mod.main(
                            ["--workspace", str(ws), "--retarget-ai", "codex"]
                        )

            self.assertEqual(result, 0)
            retarget.assert_called_once()
            sync.assert_called_once_with(
                ws.resolve(),
                ROOT,
                "codex",
                skip_extension_sync=False,
            )

    def test_main_patch_materializes_for_primary_agent_without_retarget(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "ws"
            ws.mkdir()
            (ws / ".itx-config.yml").write_text(
                'domain: "base"\nexecution_mode: "mcp"\nagents:\n  primary: "codex"\n',
                encoding="utf-8",
            )

            with mock.patch("patch.patch_workspace", return_value=(2, [])):
                with mock.patch("patch.materialize_extension_workflows_for_agent", return_value=3) as mat:
                    with mock.patch("patch.materialize_extension_skills_for_agent", return_value=1) as skills:
                        result = patch_mod.main(["--workspace", str(ws)])

            self.assertEqual(result, 0)
            mat.assert_called_once_with(ws.resolve(), "codex")
            skills.assert_called_once_with(ws.resolve(), "codex")

    def test_main_patch_mirrors_registry_for_primary_agent_without_retarget(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "ws"
            ws.mkdir()
            (ws / ".itx-config.yml").write_text(
                'domain: "base"\nexecution_mode: "mcp"\nagents:\n  primary: "codex"\n',
                encoding="utf-8",
            )

            with mock.patch("patch.patch_workspace", return_value=(0, [])):
                with mock.patch("patch.materialize_extension_workflows_for_agent", return_value=0):
                    with mock.patch("patch.materialize_extension_skills_for_agent", return_value=0):
                        with mock.patch("patch.mirror_registry_commands", return_value=True) as mirror:
                            result = patch_mod.main(["--workspace", str(ws)])

            self.assertEqual(result, 0)
            mirror.assert_called_once_with(ws.resolve(), "codex")

    def test_materialize_brownfield_extension_workflows(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "w"
            ws.mkdir()
            (ws / ".agents" / "workflows").mkdir(parents=True)
            src = ROOT / "extensions" / "itx-brownfield-workflows"
            dst = ws / ".specify" / "extensions" / "itx-brownfield-workflows"
            shutil.copytree(src, dst, dirs_exist_ok=True)

            n = itx_specify.materialize_extension_workflows_for_agent(ws, "codex")
            self.assertEqual(n, 5)
            for name in ("bugfix", "refactor", "modify", "hotfix", "deprecate"):
                self.assertTrue((ws / ".agents" / "workflows" / f"speckit.{name}.md").exists())

    def test_materialize_extension_workflows_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "w"
            ws.mkdir()
            (ws / ".kilocode" / "workflows").mkdir(parents=True)
            ext = ws / ".specify" / "extensions" / "demoext"
            ext.mkdir(parents=True)
            cmd_dir = ext / "commands"
            cmd_dir.mkdir()
            (cmd_dir / "x.md").write_text("body\n", encoding="utf-8")
            (ext / "extension.yml").write_text(
                "schema_version: '1.0'\n"
                "provides:\n"
                "  commands:\n"
                "    - name: speckit.demo.cmd\n"
                "      file: commands/x.md\n",
                encoding="utf-8",
            )
            n = itx_specify.materialize_extension_workflows_for_agent(ws, "kilocode")
            self.assertEqual(n, 1)
            dest = ws / ".kilocode" / "workflows" / "speckit.demo.cmd.md"
            self.assertEqual(dest.read_text(encoding="utf-8"), "body\n")
            self.assertEqual(
                itx_specify.materialize_extension_workflows_for_agent(ws, "kilocode"), 0
            )

    def test_mirror_registry_commands_adds_target_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "w"
            reg_dir = ws / ".specify" / "extensions"
            reg_dir.mkdir(parents=True)
            data = {
                "extensions": {
                    "review": {
                        "registered_commands": {"claude": ["speckit.review.run"]},
                    }
                }
            }
            (reg_dir / ".registry").write_text(
                json.dumps(data, indent=2) + "\n", encoding="utf-8"
            )
            self.assertTrue(itx_specify.mirror_registry_commands(ws, "kilocode"))
            loaded = json.loads((reg_dir / ".registry").read_text(encoding="utf-8"))
            rc = loaded["extensions"]["review"]["registered_commands"]
            self.assertEqual(rc["kilocode"], ["speckit.review.run"])

    def test_materialize_extension_skills_for_codex(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp) / "w"
            ws.mkdir()
            (ws / ".agents" / "skills").mkdir(parents=True)
            (ws / ".specify" / "scripts" / "bash").mkdir(parents=True)
            (ws / ".specify" / "scripts" / "bash" / "check-prerequisites.sh").write_text(
                "#!/bin/sh\n",
                encoding="utf-8",
            )

            ext = ws / ".specify" / "extensions" / "cleanup"
            ext.mkdir(parents=True)
            (ext / "commands").mkdir()
            (ext / "commands" / "cleanup.md").write_text(
                "---\n"
                'description: "Cleanup command"\n'
                "scripts:\n"
                "  sh: scripts/bash/check-prerequisites.sh --json --require-tasks\n"
                "---\n\n"
                "Run `{SCRIPT}` now.\n",
                encoding="utf-8",
            )
            (ext / "extension.yml").write_text(
                'schema_version: "1.0"\n'
                "extension:\n"
                '  id: "cleanup"\n'
                "provides:\n"
                "  commands:\n"
                '    - name: "speckit.cleanup.run"\n'
                '      file: "commands/cleanup.md"\n',
                encoding="utf-8",
            )

            n = itx_specify.materialize_extension_skills_for_agent(ws, "codex")
            self.assertEqual(n, 1)
            dest = ws / ".agents" / "skills" / "speckit-cleanup-run" / "SKILL.md"
            text = dest.read_text(encoding="utf-8")
            self.assertIn('name: speckit-cleanup-run', text)
            self.assertIn("Cleanup command", text)
            self.assertIn(".specify/scripts/bash/check-prerequisites.sh --json --require-tasks", text)
            self.assertEqual(itx_specify.materialize_extension_skills_for_agent(ws, "codex"), 0)


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
        from unittest.mock import MagicMock
        from unittest.mock import patch as mock_patch

        def fake_which(cmd):
            return "/usr/bin/specify" if cmd == "specify" else ("/usr/bin/uvx" if cmd == "uvx" else None)

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
        from unittest.mock import MagicMock
        from unittest.mock import patch as mock_patch

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
                    "registered_commands": {"cursor": ["speckit.cleanup.run", "speckit.cleanup"]},
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
        import io
        from unittest.mock import patch as mock_patch

        with tempfile.TemporaryDirectory() as tmp:
            ws = self._make_extension_workspace(tmp)
            captured = io.StringIO()
            with (
                mock_patch("run_speckit.shutil.which", return_value=None),
                mock_patch("sys.stdout", captured),
            ):
                rc = run_speckit.main(
                    [
                        "--command",
                        "cleanup.run",
                        "--workspace",
                        str(ws),
                    ]
                )
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
                rc = run_speckit.main(
                    [
                        "--command",
                        "cleanup.run",
                        "--workspace",
                        str(ws),
                    ]
                )
            self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
