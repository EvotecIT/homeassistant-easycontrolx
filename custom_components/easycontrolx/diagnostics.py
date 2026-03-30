from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .capabilities import (
    supports_app_launch,
    supports_audio,
    supports_bluetooth,
    supports_media,
    supports_monitor_inventory,
    supports_network_metrics,
    supports_process_control,
    supports_process_inventory,
    supports_service_control,
    supports_service_inventory,
    supports_storage_metrics,
    supports_system_metrics,
    supports_windows_inventory,
)
from .const import DIAGNOSTICS_REDACT
from .models import EasyControlXConfigEntry


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: EasyControlXConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    status = async_redact_data(entry.runtime_data.coordinator.data, DIAGNOSTICS_REDACT)
    capabilities = status.get("device", {}).get("capabilities", [])
    service_inventory = (status.get("serviceInventory", {}) or {}).get("services", [])

    return {
        "entry": async_redact_data(dict(entry.data), DIAGNOSTICS_REDACT),
        "options": dict(entry.options),
        "status": status,
        "capabilities": capabilities,
        "service_inventory_count": len(service_inventory),
        "service_names": [
            service.get("serviceName")
            for service in service_inventory
            if isinstance(service, dict) and service.get("serviceName")
        ],
        "derived_support": {
            "app_launch": supports_app_launch(status),
            "audio": supports_audio(status),
            "bluetooth": supports_bluetooth(status),
            "media": supports_media(status),
            "monitor_inventory": supports_monitor_inventory(status),
            "network_metrics": supports_network_metrics(status),
            "process_control": supports_process_control(status),
            "process_inventory": supports_process_inventory(status),
            "service_control": supports_service_control(status),
            "service_inventory": supports_service_inventory(status),
            "storage_metrics": supports_storage_metrics(status),
            "system_metrics": supports_system_metrics(status),
            "windows_inventory": supports_windows_inventory(status),
        },
    }
