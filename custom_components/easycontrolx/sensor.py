from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .capabilities import (
    service_inventory_items,
    supports_audio,
    supports_bluetooth,
    supports_media,
    supports_monitor_inventory,
    supports_network_metrics,
    supports_process_inventory,
    supports_service_inventory,
    supports_storage_metrics,
    supports_system_metrics,
    supports_windows_inventory,
)
from .entity import EasyControlXEntity
from .helpers import nested_get, section_attributes
from .models import EasyControlXConfigEntry


@dataclass(frozen=True, kw_only=True)
class EasyControlXSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], Any]
    attributes_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


SENSORS: tuple[EasyControlXSensorDescription, ...] = (
    EasyControlXSensorDescription(
        key="trusted_controllers_count",
        icon="mdi:account-check-outline",
        native_unit_of_measurement="controllers",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: nested_get(data, "trust", "trustedControllerCount", default=0),
        attributes_fn=lambda data: {
            "has_trusted_controllers": nested_get(
                data,
                "trust",
                "hasTrustedControllers",
                default=False,
            ),
        },
    ),
    EasyControlXSensorDescription(
        key="pending_pairings",
        icon="mdi:cellphone-key",
        native_unit_of_measurement="pairings",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda data: nested_get(data, "trust", "pendingPairingCount", default=0),
    ),
    EasyControlXSensorDescription(
        key="open_windows",
        icon="mdi:application-outline",
        native_unit_of_measurement="windows",
        value_fn=lambda data: nested_get(data, "windows", "itemCount", default=0),
        attributes_fn=lambda data: section_attributes(data, "windows"),
    ),
    EasyControlXSensorDescription(
        key="monitors",
        icon="mdi:monitor-multiple",
        native_unit_of_measurement="monitors",
        value_fn=lambda data: nested_get(data, "monitors", "itemCount", default=0),
        attributes_fn=lambda data: section_attributes(data, "monitors"),
    ),
    EasyControlXSensorDescription(
        key="bluetooth_devices",
        icon="mdi:bluetooth",
        native_unit_of_measurement="devices",
        value_fn=lambda data: nested_get(data, "bluetooth", "itemCount", default=0),
        attributes_fn=lambda data: section_attributes(data, "bluetooth"),
    ),
    EasyControlXSensorDescription(
        key="processes",
        icon="mdi:application-cog-outline",
        native_unit_of_measurement="processes",
        value_fn=lambda data: nested_get(data, "processes", "itemCount", default=0),
        attributes_fn=lambda data: section_attributes(data, "processes"),
    ),
    EasyControlXSensorDescription(
        key="remote_sessions",
        icon="mdi:monitor-eye",
        native_unit_of_measurement="sessions",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: nested_get(data, "remoteSessions", "activeSessionCount", default=0),
        attributes_fn=lambda data: {
            "has_active_sessions": nested_get(
                data,
                "remoteSessions",
                "hasActiveSessions",
                default=False,
            ),
            "summary": nested_get(data, "remoteSessions", "summary"),
        },
    ),
    EasyControlXSensorDescription(
        key="audio_summary",
        icon="mdi:volume-high",
        value_fn=lambda data: nested_get(data, "audio", "summary", default="Unavailable"),
        attributes_fn=lambda data: section_attributes(data, "audio", include_item_count=False),
    ),
    EasyControlXSensorDescription(
        key="media_summary",
        icon="mdi:play-circle-outline",
        value_fn=lambda data: nested_get(data, "media", "summary", default="Unavailable"),
        attributes_fn=lambda data: section_attributes(data, "media", include_item_count=False),
    ),
    EasyControlXSensorDescription(
        key="cpu_usage",
        icon="mdi:cpu-64-bit",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: nested_get(data, "system", "cpu", "usagePercent"),
        attributes_fn=lambda data: {
            "summary": nested_get(data, "system", "summary"),
            "freshness": nested_get(data, "system", "freshness"),
            "uptime_seconds": nested_get(data, "system", "uptimeSeconds"),
        },
    ),
    EasyControlXSensorDescription(
        key="memory_usage",
        icon="mdi:memory",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: nested_get(data, "system", "memory", "usagePercent"),
        attributes_fn=lambda data: {
            "summary": nested_get(data, "system", "summary"),
            "freshness": nested_get(data, "system", "freshness"),
            "available_bytes": nested_get(data, "system", "memory", "availableBytes"),
            "total_bytes": nested_get(data, "system", "memory", "totalBytes"),
        },
    ),
    EasyControlXSensorDescription(
        key="uptime_seconds",
        icon="mdi:timer-outline",
        native_unit_of_measurement="s",
        value_fn=lambda data: nested_get(data, "system", "uptimeSeconds"),
        attributes_fn=lambda data: {
            "summary": nested_get(data, "system", "summary"),
            "freshness": nested_get(data, "system", "freshness"),
        },
    ),
    EasyControlXSensorDescription(
        key="storage_volumes",
        icon="mdi:harddisk",
        native_unit_of_measurement="volumes",
        value_fn=lambda data: nested_get(data, "storage", "itemCount", default=0),
        attributes_fn=lambda data: section_attributes(data, "storage"),
    ),
    EasyControlXSensorDescription(
        key="network_interfaces",
        icon="mdi:ethernet",
        native_unit_of_measurement="interfaces",
        value_fn=lambda data: nested_get(data, "network", "itemCount", default=0),
        attributes_fn=lambda data: section_attributes(data, "network"),
    ),
    EasyControlXSensorDescription(
        key="managed_services",
        icon="mdi:cog-box",
        native_unit_of_measurement="services",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda data: nested_get(data, "services", "itemCount", default=0),
        attributes_fn=lambda data: {
            **section_attributes(data, "services"),
            "configured_services": [
                service.get("serviceName")
                for service in service_inventory_items(data)
                if service.get("serviceName")
            ],
        },
    ),
    EasyControlXSensorDescription(
        key="helper_state",
        icon="mdi:desktop-classic",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda data: nested_get(
            data,
            "interactiveSession",
            "helperState",
            default="Unavailable",
        ),
        attributes_fn=lambda data: {
            "helper_ready": nested_get(data, "interactiveSession", "helperReady"),
            "active_session_available": nested_get(
                data,
                "interactiveSession",
                "activeSessionAvailable",
            ),
            "summary": nested_get(data, "interactiveSession", "summary"),
            "helper_last_seen_utc": nested_get(
                data,
                "interactiveSession",
                "helperLastSeenUtc",
            ),
        },
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EasyControlXConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up EasyControlX sensors."""
    status = entry.runtime_data.coordinator.data
    entities: list[EasyControlXSensor] = []

    for description in SENSORS:
        if description.key == "open_windows" and not supports_windows_inventory(status):
            continue
        if description.key == "monitors" and not supports_monitor_inventory(status):
            continue
        if description.key == "bluetooth_devices" and not supports_bluetooth(status):
            continue
        if description.key == "processes" and not supports_process_inventory(status):
            continue
        if description.key == "remote_sessions" and not nested_get(
            status,
            "remoteSessions",
            default=None,
        ):
            continue
        if description.key == "audio_summary" and not supports_audio(status):
            continue
        if description.key == "media_summary" and not supports_media(status):
            continue
        if (
            description.key in {"cpu_usage", "memory_usage", "uptime_seconds"}
            and not supports_system_metrics(status)
        ):
            continue
        if description.key == "storage_volumes" and not supports_storage_metrics(status):
            continue
        if description.key == "network_interfaces" and not supports_network_metrics(status):
            continue
        if description.key == "managed_services" and not supports_service_inventory(status):
            continue
        if (
            description.key == "helper_state"
            and not nested_get(status, "helper", default=None)
            and not nested_get(status, "interactiveSession", default=None)
        ):
            continue

        entities.append(EasyControlXSensor(entry, description))

    async_add_entities(entities)


class EasyControlXSensor(EasyControlXEntity, SensorEntity):
    """Represent an EasyControlX sensor."""

    entity_description: EasyControlXSensorDescription

    def __init__(
        self,
        config_entry: EasyControlXConfigEntry,
        description: EasyControlXSensorDescription,
    ) -> None:
        super().__init__(config_entry)
        self.entity_description = description
        self._attr_translation_key = description.key
        self._attr_unique_id = f"{config_entry.data['device_id']}_{description.key}"

    @property
    def native_value(self) -> Any:
        """Return the current sensor value."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return sensor-specific attributes."""
        attributes = dict(super().extra_state_attributes or {})
        if self.entity_description.attributes_fn is not None:
            attributes.update(self.entity_description.attributes_fn(self.coordinator.data))
        return attributes
