from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_BASE_URL, CONF_DEVICE_ID, DOMAIN
from .helpers import nested_get
from .models import EasyControlXConfigEntry


class EasyControlXEntity(CoordinatorEntity):
    """Base EasyControlX entity."""

    _attr_has_entity_name = True

    def __init__(self, config_entry: EasyControlXConfigEntry) -> None:
        super().__init__(config_entry.runtime_data.coordinator)
        self._config_entry = config_entry

    @property
    def device_info(self) -> DeviceInfo:
        """Describe the EasyControlX host as a Home Assistant device."""
        status = self.coordinator.data
        device = nested_get(status, "device", default={}) or {}

        return DeviceInfo(
            identifiers={(DOMAIN, self._config_entry.data[CONF_DEVICE_ID])},
            manufacturer="EvotecIT",
            name=device.get("name", self._config_entry.title),
            model=f"EasyControlX {device.get('platform', 'Host')}",
            sw_version=device.get("protocolVersion"),
            configuration_url=self._config_entry.data.get(CONF_BASE_URL),
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return common diagnostic attributes."""
        status = self.coordinator.data
        device = nested_get(status, "device", default={}) or {}
        return {
            "base_url": self._config_entry.data.get(CONF_BASE_URL),
            "device_id": device.get("deviceId"),
            "platform": device.get("platform"),
            "protocol_version": device.get("protocolVersion"),
            "server_time_utc": status.get("serverTimeUtc"),
        }
