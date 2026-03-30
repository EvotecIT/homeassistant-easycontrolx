from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .capabilities import (
    service_inventory_items,
    supports_service_control,
    supports_service_inventory,
)
from .managed_services import EasyControlXManagedServiceEntity
from .models import EasyControlXConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EasyControlXConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up EasyControlX managed service switches."""
    status = entry.runtime_data.coordinator.data
    if not supports_service_inventory(status) or not supports_service_control(status):
        return

    entities = [
        EasyControlXManagedServiceSwitch(entry, service)
        for service in service_inventory_items(status)
    ]
    async_add_entities(entities)


class EasyControlXManagedServiceSwitch(EasyControlXManagedServiceEntity, SwitchEntity):
    """Represent a curated Windows service as a switch."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        config_entry: EasyControlXConfigEntry,
        service: dict[str, Any],
    ) -> None:
        super().__init__(config_entry, service)
        self._attr_name = self.service_display_name
        self._attr_unique_id = f"{config_entry.data['device_id']}_service_{self.service_key}"

    @property
    def available(self) -> bool:
        """Return availability for the switch."""
        return super().available and self.service_data is not None and self.service_exists

    @property
    def is_on(self) -> bool | None:
        """Return whether the service is currently running."""
        service = self.service_data
        if service is None or not service.get("exists", False):
            return None
        return str(service.get("status", "")).lower() == "running"

    @property
    def assumed_state(self) -> bool:
        """Return whether the service state should be treated as assumed."""
        return False

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return service-specific attributes."""
        attributes = dict(super().extra_state_attributes or {})
        attributes.update(self.service_state_attributes())
        return attributes

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Start the managed service."""
        await self._async_run_action("Start")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Stop the managed service."""
        await self._async_run_action("Stop")

    async def _async_run_action(self, action: str) -> None:
        """Execute a curated service action and refresh host data."""
        await self._config_entry.runtime_data.client.async_post_service(action, self.service_name)
        await self.coordinator.async_request_refresh()
