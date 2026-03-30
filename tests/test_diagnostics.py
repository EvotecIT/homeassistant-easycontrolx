from __future__ import annotations

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
    assert result["service_names"] == ["EasyControlX Windows Agent", "Spooler"]


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
