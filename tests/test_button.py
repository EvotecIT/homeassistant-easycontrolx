from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.easycontrolx.button import EasyControlXManagedServiceRestartButton
from custom_components.easycontrolx.models import EasyControlXRuntimeData


def _make_entry() -> tuple[SimpleNamespace, dict[str, object], SimpleNamespace]:
    client = SimpleNamespace(async_post_service=AsyncMock())
    service = {
        "serviceName": "EasyControlX Windows Agent",
        "displayName": "EasyControlX Windows Agent",
        "exists": True,
        "status": "Running",
        "startType": "Automatic",
        "canStop": True,
        "description": "Host agent",
    }
    coordinator = SimpleNamespace(
        data={
            "device": {"deviceId": "host-one", "platform": "Windows", "protocolVersion": "1"},
            "serviceInventory": {"services": [service]},
        },
        async_request_refresh=AsyncMock(),
        last_update_success=True,
    )
    entry = SimpleNamespace(
        data={"device_id": "host-one"},
        title="Host One",
        runtime_data=EasyControlXRuntimeData(client=client, coordinator=coordinator),
    )
    return entry, service, coordinator


def test_managed_service_restart_button_has_expected_name_and_attributes() -> None:
    entry, service, _coordinator = _make_entry()
    button = EasyControlXManagedServiceRestartButton(entry, service)

    assert button.name == "Restart EasyControlX Windows Agent"
    assert button.available is True
    assert button.extra_state_attributes["service_name"] == "EasyControlX Windows Agent"
    assert button.extra_state_attributes["status"] == "Running"


@pytest.mark.asyncio
async def test_managed_service_restart_button_calls_service_action() -> None:
    entry, service, coordinator = _make_entry()
    button = EasyControlXManagedServiceRestartButton(entry, service)

    await button.async_press()

    entry.runtime_data.client.async_post_service.assert_awaited_once_with(
        "Restart",
        "EasyControlX Windows Agent",
    )
    coordinator.async_request_refresh.assert_awaited_once_with()


def test_managed_service_restart_button_is_unavailable_when_service_is_missing() -> None:
    entry, service, _coordinator = _make_entry()
    missing_service = {
        **service,
        "exists": False,
        "status": None,
    }
    entry.runtime_data.coordinator.data["serviceInventory"]["services"][0] = missing_service
    button = EasyControlXManagedServiceRestartButton(entry, missing_service)

    assert button.available is False
