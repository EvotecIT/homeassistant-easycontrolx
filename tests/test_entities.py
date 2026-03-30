from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

from custom_components.easycontrolx.binary_sensor import (
    BINARY_SENSORS,
    EasyControlXBinarySensor,
)
from custom_components.easycontrolx.models import EasyControlXRuntimeData
from custom_components.easycontrolx.sensor import SENSORS, EasyControlXSensor


def _make_entry() -> SimpleNamespace:
    client = SimpleNamespace(async_post_service=AsyncMock())
    coordinator = SimpleNamespace(
        data={
            "serverTimeUtc": "2026-03-30T10:00:00Z",
            "device": {
                "deviceId": "host-one",
                "platform": "Windows",
                "protocolVersion": "1",
            },
            "trust": {
                "hasTrustedControllers": True,
                "trustedControllerCount": 2,
                "pendingPairingCount": 1,
            },
            "system": {
                "summary": "CPU 12%, memory 45%, uptime 2h.",
                "freshness": "Live",
                "uptimeSeconds": 7200,
                "cpu": {"usagePercent": 12.5},
                "memory": {
                    "usagePercent": 45.0,
                    "availableBytes": 17179869184,
                    "totalBytes": 34359738368,
                },
            },
            "interactiveSession": {
                "helperReady": True,
                "helperState": "Ready",
                "summary": "Helper is ready.",
                "helperLastSeenUtc": "2026-03-30T09:59:30Z",
                "activeSessionAvailable": True,
            },
            "remoteSessions": {
                "hasActiveSessions": True,
                "activeSessionCount": 2,
                "summary": "2 active remote sessions.",
            },
            "services": {
                "summary": "2 managed services reported.",
                "freshness": "Live",
                "itemCount": 2,
            },
            "serviceInventory": {
                "services": [
                    {"serviceName": "EasyControlX Windows Agent"},
                    {"serviceName": "Spooler"},
                ]
            },
        },
        last_update_success=True,
    )
    return SimpleNamespace(
        data={"device_id": "host-one", "base_url": "http://host.local:5188"},
        title="Host One",
        runtime_data=EasyControlXRuntimeData(client=client, coordinator=coordinator),
    )


def test_memory_sensor_exposes_bytes_and_summary_attributes() -> None:
    entry = _make_entry()
    description = next(item for item in SENSORS if item.key == "memory_usage")
    entity = EasyControlXSensor(entry, description)

    assert entity.native_value == 45.0
    assert entity.extra_state_attributes["available_bytes"] == 17179869184
    assert entity.extra_state_attributes["total_bytes"] == 34359738368
    assert entity.extra_state_attributes["summary"] == "CPU 12%, memory 45%, uptime 2h."


def test_managed_services_sensor_exposes_configured_service_names() -> None:
    entry = _make_entry()
    description = next(item for item in SENSORS if item.key == "managed_services")
    entity = EasyControlXSensor(entry, description)

    assert entity.native_value == 2
    assert entity.extra_state_attributes["configured_services"] == [
        "EasyControlX Windows Agent",
        "Spooler",
    ]


def test_remote_sessions_binary_sensor_exposes_count_attributes() -> None:
    entry = _make_entry()
    description = next(item for item in BINARY_SENSORS if item.key == "remote_sessions_active")
    entity = EasyControlXBinarySensor(entry, description)

    assert entity.is_on is True
    assert entity.extra_state_attributes["active_session_count"] == 2
    assert entity.extra_state_attributes["summary"] == "2 active remote sessions."
