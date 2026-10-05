"""Config-entry setup and migration contracts."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.easycontrolx import async_migrate_entry
from custom_components.easycontrolx.const import (
    CONF_BASE_URL,
    CONF_DEVICE_ID,
    CONF_TLS_FINGERPRINT,
    DOMAIN,
    SERVICE_REFRESH,
)


async def test_actions_exist_without_loaded_host(hass: HomeAssistant) -> None:
    assert await async_setup_component(hass, DOMAIN, {})
    assert hass.services.has_service(DOMAIN, SERVICE_REFRESH)
    with pytest.raises(ServiceValidationError, match="No EasyControlX hosts"):
        await hass.services.async_call(DOMAIN, SERVICE_REFRESH, {}, blocking=True)


async def test_actions_follow_entry_state_and_survive_unload(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN, version=1, minor_version=1,
        data={CONF_BASE_URL: "https://host.local:5188", CONF_ACCESS_TOKEN: "token"},
    )
    entry.add_to_hass(hass)
    with (
        patch(
            "custom_components.easycontrolx.api.EasyControlXApiClient.async_get_status",
            new_callable=AsyncMock, return_value={},
        ),
        patch.object(hass.config_entries, "async_forward_entry_setups", new_callable=AsyncMock),
        patch.object(
            hass.config_entries, "async_unload_platforms", new_callable=AsyncMock,
        ) as unload,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        runtime = entry.runtime_data
        with patch.object(
            runtime.coordinator, "async_request_refresh", new_callable=AsyncMock,
        ) as refresh:
            await hass.services.async_call(DOMAIN, SERVICE_REFRESH, {}, blocking=True)
            refresh.assert_awaited_once()

            unload.return_value = True
            assert await hass.config_entries.async_unload(entry.entry_id)
            assert hass.services.has_service(DOMAIN, SERVICE_REFRESH)
            # Even retained runtime data must not permit commands after unload.
            entry.runtime_data = runtime
            refresh.reset_mock()
            with pytest.raises(ServiceValidationError, match="not currently loaded"):
                await hass.services.async_call(DOMAIN, SERVICE_REFRESH, {}, blocking=True)
            refresh.assert_not_awaited()


async def test_legacy_http_entry_migrates_to_https_repair_path(
    hass: HomeAssistant,
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        minor_version=0,
        data={
            CONF_BASE_URL: "http://host.local:5188/",
            CONF_ACCESS_TOKEN: "controller-token",
            CONF_DEVICE_ID: "device-123",
        },
    )
    entry.add_to_hass(hass)

    assert await async_migrate_entry(hass, entry) is True
    assert entry.minor_version == 1
    assert entry.data[CONF_BASE_URL] == "https://host.local:5188"
    assert entry.data[CONF_TLS_FINGERPRINT] == ""
    assert entry.data[CONF_ACCESS_TOKEN] == "controller-token"


async def test_invalid_legacy_url_fails_migration_without_mutating_entry(
    hass: HomeAssistant,
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        minor_version=0,
        data={CONF_BASE_URL: "not a valid host/path", CONF_ACCESS_TOKEN: "token"},
    )
    entry.add_to_hass(hass)

    assert await async_migrate_entry(hass, entry) is False
    assert entry.minor_version == 0
    assert entry.data[CONF_BASE_URL] == "not a valid host/path"
