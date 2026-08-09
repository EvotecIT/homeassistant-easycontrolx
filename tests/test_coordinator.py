from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed

from custom_components.easycontrolx.coordinator import EasyControlXCoordinator
from custom_components.easycontrolx.exceptions import (
    TLSCertificateUntrusted,
    TLSFingerprintMismatch,
)


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


@pytest.mark.asyncio
async def test_certificate_rotation_starts_reauthentication() -> None:
    client = AsyncMock()
    client.async_get_status.side_effect = TLSFingerprintMismatch("certificate changed")
    coordinator = EasyControlXCoordinator.__new__(EasyControlXCoordinator)
    coordinator.client = client

    with pytest.raises(ConfigEntryAuthFailed, match="certificate changed"):
        await coordinator._async_update_data()


@pytest.mark.asyncio
async def test_optional_inventory_fails_closed_on_certificate_rotation() -> None:
    client = AsyncMock()
    client.async_get_services.side_effect = TLSFingerprintMismatch("certificate changed")
    coordinator = EasyControlXCoordinator.__new__(EasyControlXCoordinator)
    coordinator.client = client
    status = {
        "device": {"capabilities": ["windows.services.list"]},
        "services": {"itemCount": 1},
    }

    with pytest.raises(ConfigEntryAuthFailed, match="certificate changed"):
        await coordinator._async_enrich_optional_status(status)


@pytest.mark.asyncio
async def test_untrusted_certificate_starts_reauthentication() -> None:
    client = AsyncMock()
    client.async_get_status.side_effect = TLSCertificateUntrusted("approval required")
    coordinator = EasyControlXCoordinator.__new__(EasyControlXCoordinator)
    coordinator.client = client

    with pytest.raises(ConfigEntryAuthFailed, match="fingerprint approval"):
        await coordinator._async_update_data()
