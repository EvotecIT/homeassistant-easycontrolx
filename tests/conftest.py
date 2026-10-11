"""Shared Home Assistant integration test fixtures."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Allow Home Assistant to load the repository's custom integration."""
    yield


@pytest.fixture
def mock_flow_entry_setup():
    """Keep flow-only tests separate from the host platform setup tests."""
    with patch(
        "custom_components.easycontrolx.async_setup_entry",
        new_callable=AsyncMock,
        return_value=True,
    ):
        yield
