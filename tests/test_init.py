"""Config-entry setup and migration contracts."""

from __future__ import annotations

from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.easycontrolx import async_migrate_entry
from custom_components.easycontrolx.const import (
    CONF_BASE_URL,
    CONF_DEVICE_ID,
    CONF_TLS_FINGERPRINT,
    DOMAIN,
)


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
