"""Capability, privacy-default, and preview request contracts."""

from unittest.mock import AsyncMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.easycontrolx.camera import (
    EasyControlXActiveWindowPreviewCamera,
    EasyControlXDesktopPreviewCamera,
    async_setup_entry,
)
from custom_components.easycontrolx.const import CONF_PREFERRED_MONITOR_ID, DOMAIN
from custom_components.easycontrolx.coordinator import EasyControlXCoordinator
from custom_components.easycontrolx.models import EasyControlXRuntimeData


@pytest.fixture
def camera_entry(hass):
    client = AsyncMock()
    client.async_get_desktop_preview.return_value = b"desktop-image"
    client.async_get_window_preview.return_value = b"window-image"
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"device_id": "host-one", "base_url": "https://host.local:5188"},
        options={CONF_PREFERRED_MONITOR_ID: "monitor-two"},
    )
    entry.add_to_hass(hass)
    coordinator = EasyControlXCoordinator(hass, client)
    coordinator.async_set_updated_data({})
    entry.runtime_data = EasyControlXRuntimeData(client=client, coordinator=coordinator)
    return entry


@pytest.mark.parametrize("capabilities,expected", [
    ([], []),
    (["desktop.preview"], ["desktop_preview"]),
    (["windows.windows.preview", "windows.windows.list"], ["active_window_preview"]),
])
async def test_camera_setup_respects_host_capabilities(hass, camera_entry, capabilities, expected):
    camera_entry.runtime_data.coordinator.async_set_updated_data(
        {"device": {"capabilities": capabilities}},
    )
    entities = []
    await async_setup_entry(hass, camera_entry, entities.extend)
    assert [entity.translation_key for entity in entities] == expected
    for entity in entities:
        if isinstance(entity, EasyControlXActiveWindowPreviewCamera):
            assert entity.entity_registry_enabled_default is False
    camera_entry.runtime_data.client.async_get_desktop_preview.assert_not_awaited()
    camera_entry.runtime_data.client.async_get_window_preview.assert_not_awaited()


async def test_desktop_preview_uses_selected_monitor_and_requested_size(camera_entry):
    camera = EasyControlXDesktopPreviewCamera(camera_entry)
    client = camera_entry.runtime_data.client
    assert await camera.async_camera_image() == b"desktop-image"
    client.async_get_desktop_preview.assert_awaited_once_with(
        monitor_id="monitor-two", max_width=1280, max_height=720,
    )
    assert camera.extra_state_attributes["preferred_monitor_id"] == "monitor-two"
    client.async_get_desktop_preview.reset_mock()
    assert await camera.async_camera_image(640, 360) == b"desktop-image"
    client.async_get_desktop_preview.assert_awaited_once_with(
        monitor_id="monitor-two", max_width=640, max_height=360,
    )


async def test_active_window_preview_tracks_current_window_and_disappearance(camera_entry):
    camera = EasyControlXActiveWindowPreviewCamera(camera_entry)
    runtime = camera_entry.runtime_data
    assert camera.available is False
    assert await camera.async_camera_image() is None
    runtime.client.async_get_window_preview.assert_not_awaited()

    runtime.coordinator.async_set_updated_data({
        "windows": {"activeWindow": {"windowId": "window-1", "title": "First"}},
    })
    assert camera.available is True
    assert await camera.async_camera_image() == b"window-image"
    runtime.client.async_get_window_preview.assert_awaited_once_with(
        "window-1", max_width=960, max_height=540,
    )
    runtime.client.async_get_window_preview.reset_mock()
    runtime.coordinator.async_set_updated_data({
        "windows": {"activeWindow": {"windowId": "window-2", "title": "Second"}},
    })
    assert await camera.async_camera_image(480, 270) == b"window-image"
    runtime.client.async_get_window_preview.assert_awaited_once_with(
        "window-2", max_width=480, max_height=270,
    )
    assert camera.extra_state_attributes["active_window_title"] == "Second"
    assert camera.extra_state_attributes["active_window_id"] == "window-2"

    runtime.client.async_get_window_preview.reset_mock()
    runtime.coordinator.async_set_updated_data({"windows": {"activeWindow": None}})
    assert camera.available is False
    assert await camera.async_camera_image() is None
    runtime.client.async_get_window_preview.assert_not_awaited()


async def test_desktop_preview_translates_host_failure(camera_entry):
    from homeassistant.exceptions import HomeAssistantError

    from custom_components.easycontrolx.exceptions import CannotConnect

    failure = CannotConnect("private-host-detail")
    camera_entry.runtime_data.client.async_get_desktop_preview.side_effect = failure
    camera = EasyControlXDesktopPreviewCamera(camera_entry)
    with pytest.raises(HomeAssistantError) as error:
        await camera.async_camera_image()
    assert error.value.translation_key == "host_unavailable"
    assert error.value.__cause__ is failure
