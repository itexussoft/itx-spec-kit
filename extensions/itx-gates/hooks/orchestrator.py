#!/usr/bin/env python3
"""Compatibility entrypoint for the Itexus gates orchestrator."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from orchestrator_brief import *  # noqa: F401,F403
from orchestrator_common import *  # noqa: F401,F403
from orchestrator_runtime import *  # noqa: F401,F403
from orchestrator_common import _DEFAULT_POLICY  # noqa: F401


if __name__ == "__main__":
    sys.exit(main())
