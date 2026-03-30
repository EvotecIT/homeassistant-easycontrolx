from __future__ import annotations

from homeassistant.components.camera import Camera
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .capabilities import supports_active_window_preview, supports_desktop_preview
from .const import CONF_PREFERRED_MONITOR_ID
from .entity import EasyControlXEntity
from .helpers import nested_get
from .models import EasyControlXConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EasyControlXConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up EasyControlX cameras."""
    status = entry.runtime_data.coordinator.data
    entities: list[EasyControlXCamera] = []

    if supports_desktop_preview(status):
        entities.append(EasyControlXDesktopPreviewCamera(entry))

    if supports_active_window_preview(status):
        entities.append(EasyControlXActiveWindowPreviewCamera(entry))

    async_add_entities(entities)


class EasyControlXCamera(EasyControlXEntity, Camera):
    """Base camera entity for EasyControlX."""

    _attr_should_poll = False

    def __init__(self, config_entry: EasyControlXConfigEntry, key: str) -> None:
        EasyControlXEntity.__init__(self, config_entry)
        Camera.__init__(self)
        self._attr_translation_key = key
        self._attr_unique_id = f"{config_entry.data['device_id']}_{key}"


class EasyControlXDesktopPreviewCamera(EasyControlXCamera):
    """Desktop preview camera."""

    def __init__(self, config_entry: EasyControlXConfigEntry) -> None:
        super().__init__(config_entry, "desktop_preview")

    async def async_camera_image(
        self,
        width: int | None = None,
        height: int | None = None,
    ) -> bytes | None:
        """Return the desktop preview image."""
        monitor_id = self._config_entry.options.get(CONF_PREFERRED_MONITOR_ID) or None
        return await self._config_entry.runtime_data.client.async_get_desktop_preview(
            monitor_id=monitor_id,
            max_width=width or 1280,
            max_height=height or 720,
        )

    @property
    def extra_state_attributes(self) -> dict[str, str | None] | None:
        """Return camera-specific attributes."""
        attrs = super().extra_state_attributes or {}
        attrs["preferred_monitor_id"] = self._config_entry.options.get(
            CONF_PREFERRED_MONITOR_ID
        ) or None
        return attrs


class EasyControlXActiveWindowPreviewCamera(EasyControlXCamera):
    """Active window preview camera."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_entity_registry_enabled_default = False

    def __init__(self, config_entry: EasyControlXConfigEntry) -> None:
        super().__init__(config_entry, "active_window_preview")

    @property
    def available(self) -> bool:
        """Return if an active window is available."""
        return (
            super().available
            and nested_get(self.coordinator.data, "windows", "activeWindow") is not None
        )

    async def async_camera_image(
        self,
        width: int | None = None,
        height: int | None = None,
    ) -> bytes | None:
        """Return the active window preview image."""
        window_id = nested_get(self.coordinator.data, "windows", "activeWindow", "windowId")
        if not window_id:
            return None

        return await self._config_entry.runtime_data.client.async_get_window_preview(
            window_id,
            max_width=width or 960,
            max_height=height or 540,
        )

    @property
    def extra_state_attributes(self) -> dict[str, str | None] | None:
        """Return active window metadata."""
        attrs = super().extra_state_attributes or {}
        attrs["active_window_title"] = nested_get(
            self.coordinator.data, "windows", "activeWindow", "title"
        )
        attrs["active_window_id"] = nested_get(
            self.coordinator.data, "windows", "activeWindow", "windowId"
        )
        return attrs
