from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .capabilities import (
    service_inventory_items,
    supported_power_actions,
    supports_audio,
    supports_media,
    supports_service_control,
    supports_service_inventory,
)
from .entity import EasyControlXEntity
from .helpers import nested_get
from .managed_services import EasyControlXManagedServiceEntity
from .models import EasyControlXConfigEntry


@dataclass(frozen=True, kw_only=True)
class EasyControlXButtonDescription(ButtonEntityDescription):
    available_fn: Callable[[dict[str, Any]], bool]
    press_fn: Callable[[EasyControlXConfigEntry], Awaitable[None]]


BUTTONS: tuple[EasyControlXButtonDescription, ...] = (
    EasyControlXButtonDescription(
        key="lock",
        icon="mdi:lock",
        available_fn=lambda data: "Lock"
        in (nested_get(data, "power", "supportedActions", default=[]) or []),
        press_fn=lambda entry: entry.runtime_data.client.async_post_power(
            "Lock", confirmed=False
        ),
    ),
    EasyControlXButtonDescription(
        key="sleep",
        icon="mdi:sleep",
        available_fn=lambda data: "Sleep"
        in (nested_get(data, "power", "supportedActions", default=[]) or []),
        press_fn=lambda entry: entry.runtime_data.client.async_post_power(
            "Sleep", confirmed=False
        ),
    ),
    EasyControlXButtonDescription(
        key="play_pause",
        icon="mdi:play-pause",
        available_fn=lambda data: bool(nested_get(data, "media", "isAvailable", default=False)),
        press_fn=lambda entry: entry.runtime_data.client.async_post_media("PlayPause"),
    ),
    EasyControlXButtonDescription(
        key="toggle_mute",
        icon="mdi:volume-high",
        available_fn=lambda data: bool(nested_get(data, "audio", "isAvailable", default=False)),
        press_fn=lambda entry: entry.runtime_data.client.async_post_audio("ToggleMute"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EasyControlXConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up EasyControlX buttons."""
    status = entry.runtime_data.coordinator.data
    power_actions = supported_power_actions(status)
    entities: list[EasyControlXButton] = []

    for description in BUTTONS:
        if description.key in {"lock", "sleep"}:
            expected_action = description.key.replace("_", " ").title().replace(" ", "")
            if expected_action not in power_actions:
                continue

        if description.key == "play_pause" and not supports_media(status):
            continue

        if description.key == "toggle_mute" and not supports_audio(status):
            continue

        entities.append(EasyControlXButton(entry, description))

    if supports_service_inventory(status) and supports_service_control(status):
        entities.extend(
            EasyControlXManagedServiceRestartButton(entry, service)
            for service in service_inventory_items(status)
        )

    async_add_entities(entities)


class EasyControlXButton(EasyControlXEntity, ButtonEntity):
    """Represent an EasyControlX action button."""

    entity_description: EasyControlXButtonDescription

    def __init__(
        self,
        config_entry: EasyControlXConfigEntry,
        description: EasyControlXButtonDescription,
    ) -> None:
        super().__init__(config_entry)
        self.entity_description = description
        self._attr_translation_key = description.key
        self._attr_unique_id = f"{config_entry.data['device_id']}_{description.key}"

    @property
    def available(self) -> bool:
        """Return availability for the button."""
        return super().available and self.entity_description.available_fn(self.coordinator.data)

    async def async_press(self) -> None:
        """Trigger the button action."""
        await self.entity_description.press_fn(self._config_entry)
        await self.coordinator.async_request_refresh()


class EasyControlXManagedServiceRestartButton(EasyControlXManagedServiceEntity, ButtonEntity):
    """Represent a restart button for a curated managed service."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:restart"

    def __init__(
        self,
        config_entry: EasyControlXConfigEntry,
        service: dict[str, Any],
    ) -> None:
        super().__init__(config_entry, service)
        self._attr_name = f"Restart {self.service_display_name}"
        self._attr_unique_id = (
            f"{config_entry.data['device_id']}_service_restart_{self.service_key}"
        )

    @property
    def available(self) -> bool:
        """Return availability for the restart button."""
        return super().available and self.service_data is not None and self.service_exists

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return service-specific attributes."""
        attributes = dict(super().extra_state_attributes or {})
        attributes.update(self.service_state_attributes())
        return attributes

    async def async_press(self) -> None:
        """Restart the managed service."""
        await self._config_entry.runtime_data.client.async_post_service(
            "Restart",
            self.service_name,
        )
        await self.coordinator.async_request_refresh()
