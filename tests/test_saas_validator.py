import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / "extensions" / "itx-gates" / "hooks"
sys.path.insert(0, str(HOOKS))

from validators import saas_platform_heuristic  # noqa: E402


class SaasPlatformValidatorTests(unittest.TestCase):
    def test_empty_workspace_no_findings(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / "README.md").write_text("# no code\n", encoding="utf-8")
            findings = saas_platform_heuristic.run(ws)
            self.assertEqual(findings, [])

    def test_no_findings_without_tenant_domain_signal(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            pkg = ws / "app"
            pkg.mkdir()
            (pkg / "main.py").write_text(
                'redis.get("config")\n',
                encoding="utf-8",
            )
            findings = saas_platform_heuristic.run(ws)
            self.assertEqual(findings, [])

    def test_tenant_filter_missing_raw_sql(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            pkg = ws / "svc"
            pkg.mkdir()
            (pkg / "repo.py").write_text(
                'tenant_id = "required"\n'
                'SQL = """\n'
                "SELECT id, email FROM users WHERE active = 1\n"
                '"""\n',
                encoding="utf-8",
            )
            findings = saas_platform_heuristic.run(ws)
            rules = {f.get("rule") for f in findings}
            self.assertIn("saas-tenant-filter-missing", rules)

    def test_global_cache_key_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            pkg = ws / "svc"
            pkg.mkdir()
            (pkg / "cache_layer.py").write_text(
                "tenant_id = 1\n"
                'cache.get("global_config")\n',
                encoding="utf-8",
            )
            findings = saas_platform_heuristic.run(ws)
            rules = {f.get("rule") for f in findings}
            self.assertIn("saas-global-cache-key", rules)

    def test_cache_key_with_tenant_token_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            pkg = ws / "svc"
            pkg.mkdir()
            (pkg / "cache_layer.py").write_text(
                "tenant_id = 1\n"
                'redis.set("tenant:9:config", "x")\n',
                encoding="utf-8",
            )
            findings = saas_platform_heuristic.run(ws)
            cache_rules = [f for f in findings if f.get("rule") == "saas-global-cache-key"]
            self.assertEqual(cache_rules, [])

    def test_session_query_all_triggers_tenant_filter_heuristic(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            pkg = ws / "svc"
            pkg.mkdir()
            (pkg / "orm.py").write_text(
                "from models import User\n"
                "tenant_id = 1\n"
                "def all_users(session):\n"
                "    return session.query(User).all()\n",
                encoding="utf-8",
            )
            findings = saas_platform_heuristic.run(ws)
            rules = {f.get("rule") for f in findings}
            self.assertIn("saas-tenant-filter-missing", rules)


if __name__ == "__main__":
    unittest.main()
