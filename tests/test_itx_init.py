import argparse
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import itx_init  # noqa: E402
import itx_specify  # noqa: E402


def _valid_args(**overrides):
    base = {
        "agent": "claude",
        "domain": "base",
        "knowledge_mode": "lazy",
        "execution_mode": "mcp",
        "hook_mode": "hybrid",
        "spec_kit_ref": itx_init.DEFAULT_SPEC_KIT_REF,
        "generic_commands_dir": "",
    }
    base.update(overrides)
    return argparse.Namespace(**base)


class ItxInitTests(unittest.TestCase):
    def test_extension_refs_are_pinned(self):
        for ref in itx_specify.EXTENSION_REFS.values():
            self.assertTrue(ref)
            self.assertNotEqual(ref, "main")

    def test_archive_url_uses_ref(self):
        url = itx_specify.extension_archive_url("owner/repo", "v1.2.3")
        self.assertEqual(url, "https://github.com/owner/repo/archive/v1.2.3.zip")

    def test_local_kit_extensions_include_brownfield_package(self):
        self.assertIn("itx-gates", itx_specify.LOCAL_KIT_EXTENSIONS)
        self.assertIn("itx-brownfield-workflows", itx_specify.LOCAL_KIT_EXTENSIONS)

    def test_strip_legacy_extension_command_aliases_removes_aliases(self):
        with tempfile.TemporaryDirectory() as tmp:
            ext_dir = Path(tmp) / "ext"
            ext_dir.mkdir()
            (ext_dir / "extension.yml").write_text(
                "schema_version: '1.0'\n"
                "provides:\n"
                "  commands:\n"
                "    - name: speckit.cleanup.run\n"
                "      file: commands/cleanup.md\n"
                "      aliases: [speckit.cleanup]\n",
                encoding="utf-8",
            )
            itx_specify.strip_legacy_extension_command_aliases(ext_dir)
            text = (ext_dir / "extension.yml").read_text(encoding="utf-8")
            self.assertNotIn("aliases", text)

    def test_install_extension_from_git_uses_checkout_ref(self):
        with tempfile.TemporaryDirectory() as tmp:
            local_dir = Path(tmp) / "ext"
            workspace = Path(tmp) / "ws"
            workspace.mkdir()
            with (
                mock.patch("itx_specify.shutil.which", return_value="/usr/bin/git"),
                mock.patch("itx_specify.run_checked") as run_checked,
                mock.patch("itx_specify.run_specify") as run_specify,
            ):
                itx_specify.install_extension_from_git(
                    spec_cli="specify",
                    repo_url="https://github.com/owner/repo.git",
                    git_ref="v1.2.3",
                    local_dir=local_dir,
                    spec_extension_id="owner/repo",
                    spec_zip_url="https://github.com/owner/repo/archive/v1.2.3.zip",
                    spec_kit_ref=itx_specify.DEFAULT_SPEC_KIT_REF,
                    quiet=True,
                    workspace=workspace,
                )

            self.assertEqual(
                run_checked.call_args_list[0].args[0],
                ["git", "clone", "https://github.com/owner/repo.git", str(local_dir)],
            )
            self.assertEqual(run_checked.call_args_list[1].args[0], ["git", "checkout", "v1.2.3"])
            run_specify.assert_called_once()

    def test_install_community_extensions_installs_local_kit_extensions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            workspace = root / "ws"
            kit_root = root / "kit"
            workspace.mkdir()
            for ext_name in itx_specify.LOCAL_KIT_EXTENSIONS:
                (kit_root / "extensions" / ext_name).mkdir(parents=True, exist_ok=True)

            with (
                mock.patch("itx_specify.run_specify") as run_specify,
                mock.patch("itx_specify.install_extension_from_git"),
            ):
                itx_specify.install_community_extensions(
                    spec_cli="specify",
                    kit_root=kit_root,
                    workspace=workspace,
                    spec_kit_ref=itx_specify.DEFAULT_SPEC_KIT_REF,
                    quiet=True,
                    with_jira=False,
                )

            local_calls = [
                call
                for call in run_specify.call_args_list
                if call.args[1][:2] == ["extension", "add"] and "--dev" in call.args[1]
            ]
            self.assertGreaterEqual(len(local_calls), len(itx_specify.LOCAL_KIT_EXTENSIONS))
            dev_paths = {call.args[1][2] for call in local_calls}
            self.assertIn(str(kit_root / "extensions" / "itx-gates"), dev_paths)
            self.assertIn(str(kit_root / "extensions" / "itx-brownfield-workflows"), dev_paths)

    def test_main_spec_kit_branch_installs_local_kit_extensions(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "ws"
            args = argparse.Namespace(
                project_name="demo",
                agent="codex",
                domain="base",
                knowledge_mode="lazy",
                workspace=str(workspace),
                execution_mode="mcp",
                hook_mode="hybrid",
                container_name="",
                spec_kit_ref=itx_init.DEFAULT_SPEC_KIT_REF,
                with_jira=False,
                generic_commands_dir="",
                debug=False,
                quiet=True,
            )

            with (
                mock.patch("itx_init.parse_args", return_value=args),
                mock.patch("itx_init.ensure_valid_args"),
                mock.patch("itx_init.detect_spec_cli", return_value="spec-kit"),
                mock.patch("itx_init.require_command"),
                mock.patch("itx_init.run_checked") as run_checked,
                mock.patch("itx_init.write_itx_config"),
                mock.patch("itx_init.stage_docs_and_policy"),
                mock.patch("itx_init.stage_templates"),
                mock.patch("itx_init.stage_cursor_rules"),
                mock.patch("itx_init.stage_knowledge"),
                mock.patch("itx_init.merge_pattern_index"),
                mock.patch("itx_init.build_knowledge_manifest_file"),
            ):
                result = itx_init.main([])

            self.assertEqual(result, 0)
            ext_installs = [
                call.args[0]
                for call in run_checked.call_args_list
                if call.args
                and len(call.args[0]) >= 4
                and call.args[0][:3] == ["spec-kit", "extension", "install"]
            ]
            installed_ext_names = {cmd[3] for cmd in ext_installs}
            self.assertIn("itx-gates", installed_ext_names)
            self.assertIn("itx-brownfield-workflows", installed_ext_names)

    def test_write_itx_config_mcp(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            itx_init.write_itx_config(
                workspace=ws,
                domain="base",
                execution_mode="mcp",
                knowledge_mode="lazy",
                hook_mode="hybrid",
                container_name="unused",
            )
            text = (ws / ".itx-config.yml").read_text(encoding="utf-8")
            self.assertIn('domain: "base"', text)
            self.assertIn('execution_mode: "mcp"', text)
            self.assertIn('hook_mode: "hybrid"', text)
            self.assertNotIn("docker:", text)

    def test_write_itx_config_docker(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            itx_init.write_itx_config(
                workspace=ws,
                domain="healthcare",
                execution_mode="docker-fallback",
                knowledge_mode="eager",
                hook_mode="manual",
                container_name="sandbox",
            )
            text = (ws / ".itx-config.yml").read_text(encoding="utf-8")
            self.assertIn('domain: "healthcare"', text)
            self.assertIn('execution_mode: "docker-fallback"', text)
            self.assertIn('hook_mode: "manual"', text)
            self.assertIn('container_name: "sandbox"', text)

    def test_stage_knowledge_eager(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            kit = root / "kit"
            ws = root / "ws"
            (kit / "presets" / "base" / "patterns").mkdir(parents=True)
            (kit / "presets" / "base" / "patterns" / "domain-driven-design.md").write_text("# ddd\n", encoding="utf-8")
            (kit / "presets" / "base" / "design-patterns").mkdir(parents=True)
            (kit / "presets" / "base" / "anti-patterns").mkdir(parents=True)
            ws.mkdir()
            (ws / ".specify").mkdir()

            itx_init.stage_knowledge(kit, ws, domain="base", knowledge_mode="eager")
            self.assertTrue((ws / ".specify" / "patterns" / "domain-driven-design.md").exists())
            self.assertFalse((ws / ".specify" / ".knowledge-store").exists())

    def test_stage_knowledge_lazy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            kit = root / "kit"
            ws = root / "ws"
            (kit / "presets" / "base" / "patterns").mkdir(parents=True)
            (kit / "presets" / "base" / "patterns" / "domain-driven-design.md").write_text("# ddd\n", encoding="utf-8")
            (kit / "presets" / "base" / "design-patterns").mkdir(parents=True)
            (kit / "presets" / "base" / "anti-patterns").mkdir(parents=True)
            ws.mkdir()
            (ws / ".specify").mkdir()

            itx_init.stage_knowledge(kit, ws, domain="base", knowledge_mode="lazy")
            self.assertTrue((ws / ".specify" / ".knowledge-store" / "patterns" / "domain-driven-design.md").exists())
            self.assertTrue((ws / ".specify" / "patterns").exists())
            self.assertTrue((ws / ".gitignore").exists())

    def test_assemble_pattern_index_base_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            kit = root / "kit"
            ws = root / "ws"
            (kit / "presets" / "base").mkdir(parents=True)
            (kit / "presets" / "base" / "pattern-index.md").write_text("# Base\n", encoding="utf-8")
            (ws / ".specify").mkdir(parents=True)

            itx_init.merge_pattern_index(kit, ws, domain="base")
            text = (ws / ".specify" / "pattern-index.md").read_text(encoding="utf-8")
            self.assertIn("# Base", text)

    def test_assemble_pattern_index_with_domain(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            kit = root / "kit"
            ws = root / "ws"
            (kit / "presets" / "base").mkdir(parents=True)
            (kit / "presets" / "base" / "pattern-index.md").write_text("# Base\n", encoding="utf-8")
            (kit / "presets" / "healthcare").mkdir(parents=True)
            (kit / "presets" / "healthcare" / "pattern-index.md").write_text("# Healthcare\n", encoding="utf-8")
            (ws / ".specify").mkdir(parents=True)

            itx_init.merge_pattern_index(kit, ws, domain="healthcare")
            text = (ws / ".specify" / "pattern-index.md").read_text(encoding="utf-8")
            self.assertIn("# Base", text)
            self.assertIn("# Healthcare", text)

    def test_detect_spec_cli_priority(self):
        with mock.patch("itx_init.shutil.which") as which:
            which.side_effect = lambda name: "/usr/bin/specify" if name == "specify" else None
            self.assertEqual(itx_init.detect_spec_cli(), "specify")

        with mock.patch("itx_init.shutil.which") as which:
            which.side_effect = lambda name: "/usr/bin/spec-kit" if name == "spec-kit" else None
            self.assertEqual(itx_init.detect_spec_cli(), "spec-kit")

    def test_validate_args_missing_required(self):
        with self.assertRaises(SystemExit):
            itx_init.parse_args([])

    def test_parse_args_spec_kit_ref_default(self):
        args = itx_init.parse_args(
            [
                "--project-name",
                "demo",
                "--agent",
                "cursor",
            ]
        )
        self.assertEqual(args.spec_kit_ref, itx_init.DEFAULT_SPEC_KIT_REF)

    def test_parse_args_spec_kit_ref_override(self):
        args = itx_init.parse_args(
            [
                "--project-name",
                "demo",
                "--agent",
                "cursor",
                "--spec-kit-ref",
                "main",
            ]
        )
        self.assertEqual(args.spec_kit_ref, "main")

    def test_map_agent_aliases(self):
        self.assertEqual(itx_specify.map_agent_for_specify("cursor"), "cursor-agent")
        self.assertEqual(itx_specify.map_agent_for_specify("kiro"), "kiro-cli")
        self.assertEqual(itx_specify.map_agent_for_specify("windsurf"), "windsurf")

    def test_ensure_valid_args_rejects_unknown_agent(self):
        with self.assertRaises(ValueError):
            itx_init.ensure_valid_args(_valid_args(agent="not-a-real-integration"))

    def test_ensure_valid_args_generic_requires_commands_dir(self):
        with self.assertRaises(ValueError):
            itx_init.ensure_valid_args(_valid_args(agent="generic", generic_commands_dir=""))
        itx_init.ensure_valid_args(
            _valid_args(agent="generic", generic_commands_dir=".myagent/commands/")
        )

    def test_ensure_valid_args_rejects_unknown_hook_mode(self):
        with self.assertRaises(ValueError):
            itx_init.ensure_valid_args(_valid_args(hook_mode="unsupported"))

    def test_write_itx_config_includes_primary_agent(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            itx_init.write_itx_config(
                workspace=ws,
                domain="base",
                execution_mode="mcp",
                knowledge_mode="lazy",
                hook_mode="auto",
                container_name="x",
                primary_agent="cursor-agent",
            )
            text = (ws / ".itx-config.yml").read_text(encoding="utf-8")
            self.assertIn("agents:", text)
            self.assertIn('primary: "cursor-agent"', text)
            self.assertIn('hook_mode: "auto"', text)


if __name__ == "__main__":
    unittest.main()
