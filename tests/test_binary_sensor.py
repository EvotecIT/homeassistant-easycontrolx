from __future__ import annotations

from types import SimpleNamespace

from custom_components.easycontrolx.binary_sensor import EasyControlXManagedServiceBinarySensor
from custom_components.easycontrolx.models import EasyControlXRuntimeData


def _make_entry(
    *,
    exists: bool = True,
    status: str | None = "Running",
) -> tuple[SimpleNamespace, dict]:
    service = {
        "serviceName": "EasyControlX Windows Agent",
        "displayName": "EasyControlX Windows Agent",
        "exists": exists,
        "status": status,
        "startType": "Automatic",
        "canStop": True,
        "description": "Host agent",
    }
    coordinator = SimpleNamespace(
        data={
            "device": {"deviceId": "host-one", "platform": "Windows", "protocolVersion": "1"},
            "serviceInventory": {"services": [service]},
        },
        last_update_success=True,
    )
    entry = SimpleNamespace(
        data={"device_id": "host-one"},
        title="Host One",
        runtime_data=EasyControlXRuntimeData(client=SimpleNamespace(), coordinator=coordinator),
    )
    return entry, service


def test_managed_service_binary_sensor_reports_running_state() -> None:
    entry, service = _make_entry()
    entity = EasyControlXManagedServiceBinarySensor(entry, service)

    assert entity.available is True
    assert entity.is_on is True
    assert entity.extra_state_attributes["service_name"] == "EasyControlX Windows Agent"
    assert entity.extra_state_attributes["status"] == "Running"


def test_managed_service_binary_sensor_reports_non_running_state() -> None:
    entry, service = _make_entry(status="Stopped")
    entity = EasyControlXManagedServiceBinarySensor(entry, service)

    assert entity.available is True
    assert entity.is_on is False


def test_managed_service_binary_sensor_stays_available_for_missing_services() -> None:
    entry, service = _make_entry(exists=False, status=None)
    entity = EasyControlXManagedServiceBinarySensor(entry, service)

    assert entity.available is True
    assert entity.is_on is False
    assert entity.extra_state_attributes["exists"] is False
