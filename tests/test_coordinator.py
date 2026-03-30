from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from custom_components.easycontrolx.coordinator import EasyControlXCoordinator


@pytest.mark.asyncio
async def test_coordinator_enriches_status_with_service_inventory() -> None:
    client = AsyncMock()
    status = {
        "device": {"capabilities": ["windows.services.list"]},
        "services": {"itemCount": 2},
    }
    client.async_get_services.return_value = {
        "services": [
            {"serviceName": "EasyControlX Windows Agent"},
            {"serviceName": "Spooler"},
        ]
    }

    coordinator = EasyControlXCoordinator.__new__(EasyControlXCoordinator)
    coordinator.client = client

    result = await coordinator._async_enrich_optional_status(status)

    assert result["serviceInventory"]["services"][0]["serviceName"] == "EasyControlX Windows Agent"
    client.async_get_services.assert_awaited_once_with()
