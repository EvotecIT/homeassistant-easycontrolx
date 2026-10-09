from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.helpers import config_validation as cv

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.typing import ConfigType

    from .models import EasyControlXConfigEntry

LOGGER = logging.getLogger(__name__)
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register actions independently of host availability."""
    from .services import async_register_services

    await async_register_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: EasyControlXConfigEntry) -> bool:
    """Set up EasyControlX from a config entry."""
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    from .api import EasyControlXApiClient
    from .const import (
        CONF_BASE_URL,
        CONF_SCAN_INTERVAL,
        CONF_TLS_FINGERPRINT,
        OPTIONAL_OPTIONS,
        PLATFORMS,
    )
    from .coordinator import EasyControlXCoordinator
    from .models import EasyControlXRuntimeData

    session = async_get_clientsession(hass)
    client = EasyControlXApiClient(
        session,
        entry.data[CONF_BASE_URL],
        entry.data["access_token"],
        entry.data.get(CONF_TLS_FINGERPRINT),
    )

    interval_seconds = int(
        entry.options.get(CONF_SCAN_INTERVAL, OPTIONAL_OPTIONS[CONF_SCAN_INTERVAL])
    )
    coordinator = EasyControlXCoordinator(
        hass,
        client,
        update_interval=timedelta(seconds=interval_seconds),
    )
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = EasyControlXRuntimeData(client=client, coordinator=coordinator)
    reload_settings = (entry.data, entry.options, entry.title, entry.unique_id)

    async def async_reload_changed_settings(
        hass: HomeAssistant, updated_entry: EasyControlXConfigEntry,
    ) -> None:
        nonlocal reload_settings
        settings = (
            updated_entry.data, updated_entry.options,
            updated_entry.title, updated_entry.unique_id,
        )
        if settings == reload_settings:
            return
        reload_settings = settings
        await async_reload_entry(hass, updated_entry)

    entry.async_on_unload(entry.add_update_listener(async_reload_changed_settings))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: EasyControlXConfigEntry) -> bool:
    """Unload an EasyControlX config entry."""
    from .const import PLATFORMS

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(hass: HomeAssistant, entry: EasyControlXConfigEntry) -> None:
    """Reload the integration after options or config changes."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_migrate_entry(hass: HomeAssistant, entry: EasyControlXConfigEntry) -> bool:
    """Migrate older config entries forward."""
    if entry.version > 1:
        return False

    if entry.version == 1 and entry.minor_version < 1:
        from .api import normalize_base_url
        from .const import CONF_BASE_URL, CONF_TLS_FINGERPRINT

        data = dict(entry.data)
        base_url = str(data.get(CONF_BASE_URL, ""))
        if base_url.lower().startswith("http://"):
            base_url = f"https://{base_url[7:]}"
        try:
            data[CONF_BASE_URL] = normalize_base_url(base_url)
        except ValueError:
            LOGGER.error("Cannot migrate invalid EasyControlX URL for %s", entry.entry_id)
            return False
        data.setdefault(CONF_TLS_FINGERPRINT, "")
        hass.config_entries.async_update_entry(
            entry,
            data=data,
            minor_version=1,
        )
        LOGGER.info("Migrated EasyControlX config entry %s to secure transport", entry.entry_id)

    return True
