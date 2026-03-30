from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .capabilities import (
    service_inventory_items,
    supports_service_control,
    supports_service_inventory,
)
from .entity import EasyControlXEntity
from .helpers import nested_get
from .managed_services import EasyControlXManagedServiceEntity
from .models import EasyControlXConfigEntry


@dataclass(frozen=True, kw_only=True)
class EasyControlXBinarySensorDescription(BinarySensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], bool]
    attributes_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


BINARY_SENSORS: tuple[EasyControlXBinarySensorDescription, ...] = (
    EasyControlXBinarySensorDescription(
        key="trusted_controllers",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda data: bool(
            nested_get(data, "trust", "hasTrustedControllers", default=False)
        ),
        attributes_fn=lambda data: {
            "trusted_controller_count": nested_get(
                data,
                "trust",
                "trustedControllerCount",
                default=0,
            ),
            "pending_pairing_count": nested_get(
                data,
                "trust",
                "pendingPairingCount",
                default=0,
            ),
        },
    ),
    EasyControlXBinarySensorDescription(
        key="helper_ready",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda data: bool(
            nested_get(data, "interactiveSession", "helperReady", default=False)
        ),
        attributes_fn=lambda data: {
            "helper_state": nested_get(data, "interactiveSession", "helperState"),
            "summary": nested_get(data, "interactiveSession", "summary"),
        },
    ),
    EasyControlXBinarySensorDescription(
        key="remote_sessions_active",
        device_class=BinarySensorDeviceClass.RUNNING,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda data: bool(
            nested_get(data, "remoteSessions", "hasActiveSessions", default=False)
        ),
        attributes_fn=lambda data: {
            "active_session_count": nested_get(
                data,
                "remoteSessions",
                "activeSessionCount",
                default=0,
            ),
            "summary": nested_get(data, "remoteSessions", "summary"),
        },
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EasyControlXConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up EasyControlX binary sensors."""
    status = entry.runtime_data.coordinator.data
    entities: list[EasyControlXBinarySensor] = []

    for description in BINARY_SENSORS:
        if (
            description.key == "helper_ready"
            and not nested_get(status, "helper", default=None)
            and not nested_get(status, "interactiveSession", default=None)
        ):
            continue
        if description.key == "remote_sessions_active" and not nested_get(
            status,
            "remoteSessions",
            default=None,
        ):
            continue

        entities.append(EasyControlXBinarySensor(entry, description))

    if supports_service_inventory(status) and not supports_service_control(status):
        entities.extend(
            EasyControlXManagedServiceBinarySensor(entry, service)
            for service in service_inventory_items(status)
        )

    async_add_entities(entities)


class EasyControlXBinarySensor(EasyControlXEntity, BinarySensorEntity):
    """Represent an EasyControlX binary sensor."""

    entity_description: EasyControlXBinarySensorDescription

    def __init__(
        self,
        config_entry: EasyControlXConfigEntry,
        description: EasyControlXBinarySensorDescription,
    ) -> None:
        super().__init__(config_entry)
        self.entity_description = description
        self._attr_translation_key = description.key
        self._attr_unique_id = f"{config_entry.data['device_id']}_{description.key}"

    @property
    def is_on(self) -> bool:
        """Return the entity state."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return binary-sensor-specific attributes."""
        attributes = dict(super().extra_state_attributes or {})
        if self.entity_description.attributes_fn is not None:
            attributes.update(self.entity_description.attributes_fn(self.coordinator.data))
        return attributes


class EasyControlXManagedServiceBinarySensor(
    EasyControlXManagedServiceEntity,
    BinarySensorEntity,
):
    """Represent a managed service running-state sensor for inventory-only hosts."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self,
        config_entry: EasyControlXConfigEntry,
        service: dict[str, Any],
    ) -> None:
        super().__init__(config_entry, service)
        self._attr_name = self.service_display_name
        self._attr_unique_id = (
            f"{config_entry.data['device_id']}_service_state_{self.service_key}"
        )

    @property
    def available(self) -> bool:
        """Return availability for the service binary sensor."""
        return super().available and self.service_data is not None

    @property
    def is_on(self) -> bool:
        """Return whether the service is currently running."""
        service = self.service_data
        return bool(service and str(service.get("status", "")).lower() == "running")

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return service-specific attributes."""
        attributes = dict(super().extra_state_attributes or {})
        attributes.update(self.service_state_attributes())
        return attributes
