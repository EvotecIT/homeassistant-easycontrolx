from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .models import EasyControlXConfigEntry

LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: EasyControlXConfigEntry) -> bool:
    """Set up EasyControlX from a config entry."""
    from homeassistant.helpers.aiohttp_client import async_get_clientsession

    from .api import EasyControlXApiClient
    from .const import (
        CONF_BASE_URL,
        CONF_SCAN_INTERVAL,
        DATA_LOADED_ENTRY_IDS,
        DOMAIN,
        OPTIONAL_OPTIONS,
        PLATFORMS,
    )
    from .coordinator import EasyControlXCoordinator
    from .models import EasyControlXRuntimeData
    from .services import async_register_services

    session = async_get_clientsession(hass)
    client = EasyControlXApiClient(
        session,
        entry.data[CONF_BASE_URL],
        entry.data["access_token"],
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
    domain_data = hass.data.setdefault(DOMAIN, {DATA_LOADED_ENTRY_IDS: set()})
    loaded_entry_ids = cast(set[str], domain_data[DATA_LOADED_ENTRY_IDS])
    loaded_entry_ids.add(entry.entry_id)
    await async_register_services(hass)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: EasyControlXConfigEntry) -> bool:
    """Unload an EasyControlX config entry."""
    from .const import DATA_LOADED_ENTRY_IDS, DOMAIN, PLATFORMS
    from .services import async_unregister_services

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False

    domain_data = hass.data.get(DOMAIN)
    if domain_data is None:
        return True

    loaded_entry_ids = cast(set[str], domain_data[DATA_LOADED_ENTRY_IDS])
    loaded_entry_ids.discard(entry.entry_id)
    if not loaded_entry_ids:
        async_unregister_services(hass)
        hass.data.pop(DOMAIN, None)

    return True


async def async_reload_entry(hass: HomeAssistant, entry) -> None:
    """Reload the integration after options or config changes."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_migrate_entry(hass: HomeAssistant, entry) -> bool:
    """Migrate older config entries forward."""
    if entry.version > 1:
        return False

    if entry.version == 1 and entry.minor_version == 0:
        return True

    LOGGER.info("Migrated EasyControlX config entry %s", entry.entry_id)
    return True
