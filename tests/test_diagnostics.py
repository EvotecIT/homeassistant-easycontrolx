from __future__ import annotations

import json
from copy import deepcopy
from types import SimpleNamespace

import pytest

from custom_components.easycontrolx.diagnostics import async_get_config_entry_diagnostics
from custom_components.easycontrolx.models import EasyControlXRuntimeData


def _make_entry() -> SimpleNamespace:
    status = {
        "device": {
            "deviceId": "host-one",
            "platform": "Windows",
            "protocolVersion": "1",
            "capabilities": [
                "audio.output",
                "media",
                "windows.processes.list",
                "windows.processes.control",
                "windows.services.list",
                "windows.services.control",
            ],
        },
        "serviceInventory": {
            "services": [
                {"serviceName": "EasyControlX Windows Agent"},
                {"serviceName": "Spooler"},
            ]
        },
        "access_token": "secret-runtime-token",
    }
    runtime_data = EasyControlXRuntimeData(
        client=SimpleNamespace(),
        coordinator=SimpleNamespace(data=status),
    )
    return SimpleNamespace(
        data={"access_token": "secret-entry-token", "device_id": "host-one"},
        options={"scan_interval": 30},
        runtime_data=runtime_data,
    )


@pytest.mark.asyncio
async def test_diagnostics_redacts_tokens_and_reports_service_summary() -> None:
    entry = _make_entry()

    result = await async_get_config_entry_diagnostics(SimpleNamespace(), entry)

    assert result["entry"]["access_token"] == "**REDACTED**"
    assert result["status"]["access_token"] == "**REDACTED**"
    assert result["service_inventory_count"] == 2
    assert result["service_names"] == ["**REDACTED**", "**REDACTED**"]


@pytest.mark.asyncio
async def test_diagnostics_removes_host_identity_without_mutating_runtime() -> None:
    """A support download retains health data without identifying the host or sessions."""
    entry = _make_entry()
    entry.data.update(
        base_url="https://private-host.example:8844",
        tls_fingerprint="private-certificate-fingerprint",
        device_id="private-host-id",
    )
    entry.options["preferred_monitor_id"] = "private-monitor-id"
    status = entry.runtime_data.coordinator.data
    status["device"].update(deviceId="private-host-id", name="private-host-name")
    status["discovery"] = {"enabled": True, "instanceName": "private-discovery-name"}
    status["remoteSessions"] = {
        "activeSessionCount": 1,
        "summary": "private-session-summary",
        "sessions": [
            {
                "sessionId": "private-session-id",
                "displayName": "private-window-name",
                "accessMode": "ViewOnly",
            }
        ],
    }
    status["serviceInventory"]["services"] = [
        {
            "serviceName": "private-service-name",
            "displayName": "private-service-display-name",
            "description": "private-service-description",
            "status": "Running",
            "canStop": True,
        }
    ]
    original = deepcopy((entry.data, entry.options, status))

    result = await async_get_config_entry_diagnostics(SimpleNamespace(), entry)

    assert "private-" not in json.dumps(result)
    assert result["status"]["device"]["platform"] == "Windows"
    assert result["status"]["device"]["protocolVersion"] == "1"
    assert result["status"]["discovery"]["enabled"] is True
    assert result["status"]["remoteSessions"]["activeSessionCount"] == 1
    assert result["status"]["remoteSessions"]["sessions"][0]["accessMode"] == "ViewOnly"
    assert result["status"]["serviceInventory"]["services"][0]["status"] == "Running"
    assert result["service_inventory_count"] == 1
    assert result["options"]["scan_interval"] == 30
    assert (entry.data, entry.options, status) == original


@pytest.mark.asyncio
async def test_diagnostics_reports_derived_support_flags() -> None:
    entry = _make_entry()

    result = await async_get_config_entry_diagnostics(SimpleNamespace(), entry)

    assert result["derived_support"]["audio"] is True
    assert result["derived_support"]["media"] is True
    assert result["derived_support"]["process_inventory"] is True
    assert result["derived_support"]["process_control"] is True
    assert result["derived_support"]["service_inventory"] is True
    assert result["derived_support"]["service_control"] is True
