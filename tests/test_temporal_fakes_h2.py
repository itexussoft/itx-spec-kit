import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FAKE_PATH = ROOT / "harnesses" / "temporal-fakes" / "example-fake" / "fake_deployment.py"


def load_fake_module():
    spec = importlib.util.spec_from_file_location("temporal_fake_deployment", FAKE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class TemporalFakesWaveH2Tests(unittest.TestCase):
    def test_state_machine_deploys_to_healthy(self):
        module = load_fake_module()
        now = {"value": 0.0}
        fake = module.DeploymentFake(clock=lambda: now["value"])

        self.assertEqual(fake.snapshot()["state"], "idle")
        fake.deploy()
        self.assertEqual(fake.snapshot()["state"], "deploying")
        now["value"] = 31.0
        fake.tick()
        self.assertEqual(fake.snapshot()["state"], "healthy")

    def test_injected_degrade_fault_expires(self):
        module = load_fake_module()
        now = {"value": 0.0}
        fake = module.DeploymentFake(clock=lambda: now["value"])
        fake.deploy()
        now["value"] = 31.0
        fake.tick()
        self.assertEqual(fake.snapshot()["state"], "healthy")

        fake.inject(
            scenario_id="degrade-error-rate",
            fault_type="degrade",
            params={"error_rate": 0.4},
            duration_s=10,
            start_after_s=0,
            ramp_up_s=0,
        )
        fake.tick()
        self.assertEqual(fake.snapshot()["state"], "degraded")
        self.assertGreater(fake.snapshot()["metrics"]["error_rate"], 0.0)

        now["value"] = 45.0
        fake.tick()
        self.assertEqual(fake.snapshot()["state"], "healthy")


if __name__ == "__main__":
    unittest.main()
