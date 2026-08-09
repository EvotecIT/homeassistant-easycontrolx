from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from custom_components.easycontrolx.binary_sensor import (
    EasyControlXBinarySensor,
    EasyControlXManagedServiceBinarySensor,
)
from custom_components.easycontrolx.binary_sensor import (
    async_setup_entry as async_setup_binary_sensors,
)
from custom_components.easycontrolx.button import (
    EasyControlXManagedServiceRestartButton,
)
from custom_components.easycontrolx.button import (
    async_setup_entry as async_setup_buttons,
)
from custom_components.easycontrolx.models import EasyControlXRuntimeData
from custom_components.easycontrolx.sensor import EasyControlXSensor
from custom_components.easycontrolx.sensor import async_setup_entry as async_setup_sensors
from custom_components.easycontrolx.switch import (
    EasyControlXManagedServiceSwitch,
)
from custom_components.easycontrolx.switch import (
    async_setup_entry as async_setup_switches,
)


def _make_entry(status: dict) -> SimpleNamespace:
    client = SimpleNamespace(
        async_post_power=AsyncMock(),
        async_post_media=AsyncMock(),
        async_post_audio=AsyncMock(),
        async_post_service=AsyncMock(),
    )
    coordinator = SimpleNamespace(
        data=status,
        async_request_refresh=AsyncMock(),
        last_update_success=True,
    )
    return SimpleNamespace(
        data={"device_id": "host-one", "base_url": "https://host.local:5188"},
        title="Host One",
        runtime_data=EasyControlXRuntimeData(client=client, coordinator=coordinator),
    )


def _collect_entities() -> tuple[list[object], callable]:
    entities: list[object] = []

    def _adder(new_entities: list[object]) -> None:
        entities.extend(new_entities)

    return entities, _adder


def _service_status(*capabilities: str, include_remote_sessions: bool = False) -> dict:
    status = {
        "device": {"capabilities": list(capabilities)},
        "services": {"itemCount": 1, "summary": "1 managed service reported."},
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
        "power": {"supportedActions": ["Lock"]},
    }

    if include_remote_sessions:
        status["remoteSessions"] = {
            "hasActiveSessions": True,
            "activeSessionCount": 1,
            "summary": "1 active remote session.",
        }

    return status


@pytest.mark.asyncio
async def test_switch_setup_skips_inventory_only_service_hosts() -> None:
    entry = _make_entry(_service_status("windows.services.list"))
    entities, adder = _collect_entities()

    await async_setup_switches(SimpleNamespace(), entry, adder)

    assert entities == []


@pytest.mark.asyncio
async def test_switch_setup_creates_entities_when_service_control_is_supported() -> None:
    entry = _make_entry(_service_status("windows.services.list", "windows.services.control"))
    entities, adder = _collect_entities()

    await async_setup_switches(SimpleNamespace(), entry, adder)

    assert len(entities) == 1
    assert isinstance(entities[0], EasyControlXManagedServiceSwitch)
    assert entities[0].name == "EasyControlX Windows Agent"


@pytest.mark.asyncio
async def test_button_setup_adds_restart_buttons_only_for_control_enabled_hosts() -> None:
    inventory_only_entry = _make_entry(_service_status("windows.services.list"))
    inventory_entities, inventory_adder = _collect_entities()
    await async_setup_buttons(SimpleNamespace(), inventory_only_entry, inventory_adder)

    control_entry = _make_entry(
        _service_status("windows.services.list", "windows.services.control")
    )
    control_entities, control_adder = _collect_entities()
    await async_setup_buttons(SimpleNamespace(), control_entry, control_adder)

    assert not any(
        isinstance(entity, EasyControlXManagedServiceRestartButton)
        for entity in inventory_entities
    )
    assert any(
        isinstance(entity, EasyControlXManagedServiceRestartButton)
        for entity in control_entities
    )


@pytest.mark.asyncio
async def test_sensor_setup_keeps_managed_services_sensor_for_inventory_only_hosts() -> None:
    entry = _make_entry(_service_status("windows.services.list"))
    entities, adder = _collect_entities()

    await async_setup_sensors(SimpleNamespace(), entry, adder)

    managed_services = [
        entity
        for entity in entities
        if isinstance(entity, EasyControlXSensor)
        and entity.entity_description.key == "managed_services"
    ]
    assert len(managed_services) == 1


@pytest.mark.asyncio
async def test_binary_sensor_setup_only_adds_remote_sessions_entity_when_present() -> None:
    without_remote_entry = _make_entry(_service_status("windows.services.list"))
    without_remote_entities, without_remote_adder = _collect_entities()
    await async_setup_binary_sensors(SimpleNamespace(), without_remote_entry, without_remote_adder)

    with_remote_entry = _make_entry(
        _service_status("windows.services.list", include_remote_sessions=True)
    )
    with_remote_entities, with_remote_adder = _collect_entities()
    await async_setup_binary_sensors(SimpleNamespace(), with_remote_entry, with_remote_adder)

    assert not any(
        isinstance(entity, EasyControlXBinarySensor)
        and entity.entity_description.key == "remote_sessions_active"
        for entity in without_remote_entities
    )
    assert any(
        isinstance(entity, EasyControlXBinarySensor)
        and entity.entity_description.key == "remote_sessions_active"
        for entity in with_remote_entities
    )


@pytest.mark.asyncio
async def test_binary_sensor_setup_adds_service_state_entities_for_inventory_only_hosts() -> None:
    inventory_only_entry = _make_entry(_service_status("windows.services.list"))
    inventory_entities, inventory_adder = _collect_entities()
    await async_setup_binary_sensors(SimpleNamespace(), inventory_only_entry, inventory_adder)

    control_entry = _make_entry(
        _service_status("windows.services.list", "windows.services.control")
    )
    control_entities, control_adder = _collect_entities()
    await async_setup_binary_sensors(SimpleNamespace(), control_entry, control_adder)

    assert any(
        isinstance(entity, EasyControlXManagedServiceBinarySensor)
        for entity in inventory_entities
    )
    assert not any(
        isinstance(entity, EasyControlXManagedServiceBinarySensor)
        for entity in control_entities
    )
