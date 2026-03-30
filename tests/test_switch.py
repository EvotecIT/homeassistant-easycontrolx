from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.easycontrolx.models import EasyControlXRuntimeData
from custom_components.easycontrolx.switch import EasyControlXManagedServiceSwitch


def _make_entry() -> tuple[SimpleNamespace, SimpleNamespace]:
    client = SimpleNamespace(async_post_service=AsyncMock())
    coordinator = SimpleNamespace(
        data={
            "device": {"deviceId": "host-one", "platform": "Windows", "protocolVersion": "1"},
            "serviceInventory": {
                "services": [
                    {
                        "serviceName": "EasyControlX Windows Agent",
                        "displayName": "EasyControlX Windows Agent",
                        "exists": True,
                        "status": "Running",
                        "startType": "Automatic",
                        "canStop": True,
                        "description": "Host agent",
                    }
                ]
            },
        },
        async_request_refresh=AsyncMock(),
        last_update_success=True,
    )
    entry = SimpleNamespace(
        data={"device_id": "host-one"},
        title="Host One",
        runtime_data=EasyControlXRuntimeData(client=client, coordinator=coordinator),
    )
    return entry, coordinator


def test_service_switch_reads_running_state() -> None:
    entry, _coordinator = _make_entry()
    switch = EasyControlXManagedServiceSwitch(
        entry,
        entry.runtime_data.coordinator.data["serviceInventory"]["services"][0],
    )

    assert switch.is_on is True
    assert switch.available is True
    assert switch.extra_state_attributes["service_name"] == "EasyControlX Windows Agent"


@pytest.mark.asyncio
async def test_service_switch_turn_off_calls_service_action() -> None:
    entry, coordinator = _make_entry()
    switch = EasyControlXManagedServiceSwitch(
        entry,
        entry.runtime_data.coordinator.data["serviceInventory"]["services"][0],
    )

    await switch.async_turn_off()

    entry.runtime_data.client.async_post_service.assert_awaited_once_with(
        "Stop",
        "EasyControlX Windows Agent",
    )
    coordinator.async_request_refresh.assert_awaited_once_with()


def test_service_switch_is_unavailable_when_service_is_missing() -> None:
    entry, _coordinator = _make_entry()
    missing_service = {
        **entry.runtime_data.coordinator.data["serviceInventory"]["services"][0],
        "exists": False,
        "status": None,
    }
    entry.runtime_data.coordinator.data["serviceInventory"]["services"][0] = missing_service
    switch = EasyControlXManagedServiceSwitch(entry, missing_service)

    assert switch.available is False
    assert switch.is_on is None
