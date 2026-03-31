"""Shared test fixtures."""

from __future__ import annotations

import os

import pytest


# Skip integration tests unless AGENTIC_VISION_INTEGRATION_TEST=1
def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    run_integration = os.environ.get("AGENTIC_VISION_INTEGRATION_TEST", "0") == "1"
    skip_integration = pytest.mark.skip(reason="set AGENTIC_VISION_INTEGRATION_TEST=1 to run")
    for item in items:
        if "integration" in item.nodeid and not run_integration:
            item.add_marker(skip_integration)
