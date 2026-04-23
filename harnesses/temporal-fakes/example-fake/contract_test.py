#!/usr/bin/env python3
"""Minimal contract-test skeleton for temporal fake and real service parity."""

from __future__ import annotations

import argparse
import json
import unittest
import urllib.request
from typing import Any, Dict


def get_json(url: str) -> Dict[str, Any]:
    with urllib.request.urlopen(url, timeout=5) as res:
        return json.loads(res.read().decode("utf-8"))


class DeploymentContractTests(unittest.TestCase):
    def test_health_endpoint_shape(self) -> None:
        payload = get_json("http://127.0.0.1:8080/healthz")
        self.assertIn("ok", payload)

    @unittest.skip("Replace with real-provider assertions for your workspace.")
    def test_fake_and_real_contract_alignment(self) -> None:
        self.fail("Implement provider-backed contract assertions.")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ping", action="store_true", help="Simple health ping for compose hooks")
    args = parser.parse_args()
    if args.ping:
        payload = get_json("http://127.0.0.1:8080/healthz")
        print(json.dumps(payload))
        return 0
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(DeploymentContractTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
