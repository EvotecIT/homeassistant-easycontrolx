from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed

from custom_components.easycontrolx.api import EasyControlXApiClient
from custom_components.easycontrolx.coordinator import EasyControlXCoordinator
from custom_components.easycontrolx.exceptions import (
    ApiError,
    CannotConnect,
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

    with pytest.raises(ConfigEntryAuthFailed) as error:
        await coordinator._async_update_data()
    assert error.value.translation_domain == "easycontrolx"
    assert error.value.translation_key == (
        "certificate_untrusted"
        if isinstance(client.async_get_status.side_effect, TLSCertificateUntrusted)
        else "certificate_changed"
    )


@pytest.mark.parametrize("error", [CannotConnect, ApiError])
async def test_optional_inventory_failure_keeps_status_available_and_recovers(hass, error):
    """A transient optional endpoint failure must not discard core host status."""
    status = {
        "device": {"capabilities": ["windows.services.list"]},
        "services": {"itemCount": 1},
    }
    client = AsyncMock(spec=EasyControlXApiClient)
    client.async_get_status.side_effect = lambda: dict(status)
    client.async_get_services.side_effect = [error("unavailable"), {"services": []}]
    coordinator = EasyControlXCoordinator(hass, client)

    await coordinator.async_refresh()

    assert coordinator.last_update_success
    assert coordinator.data == status
    assert "serviceInventory" not in coordinator.data

    await coordinator.async_refresh()

    assert coordinator.last_update_success
    assert coordinator.data == {**status, "serviceInventory": {"services": []}}
    assert client.async_get_status.await_count == 2
    assert client.async_get_services.await_count == 2


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

    with pytest.raises(ConfigEntryAuthFailed) as error:
        await coordinator._async_enrich_optional_status(status)
    assert error.value.translation_domain == "easycontrolx"
    assert error.value.translation_key == "certificate_changed"


@pytest.mark.asyncio
async def test_untrusted_certificate_starts_reauthentication() -> None:
    client = AsyncMock()
    client.async_get_status.side_effect = TLSCertificateUntrusted("approval required")
    coordinator = EasyControlXCoordinator.__new__(EasyControlXCoordinator)
    coordinator.client = client

    with pytest.raises(ConfigEntryAuthFailed) as error:
        await coordinator._async_update_data()
    assert error.value.translation_domain == "easycontrolx"
    assert error.value.translation_key == (
        "certificate_untrusted"
        if isinstance(client.async_get_status.side_effect, TLSCertificateUntrusted)
        else "certificate_changed"
    )
