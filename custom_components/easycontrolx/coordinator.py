from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import EasyControlXApiClient
from .capabilities import supports_service_inventory
from .const import UPDATE_INTERVAL_FALLBACK
from .exceptions import ApiError, CannotConnect, InvalidAuth
from .models import EasyControlXStatus

LOGGER = logging.getLogger(__name__)


class EasyControlXCoordinator(DataUpdateCoordinator[EasyControlXStatus]):
    """Coordinate status refreshes from an EasyControlX host."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: EasyControlXApiClient,
        *,
        update_interval: timedelta = UPDATE_INTERVAL_FALLBACK,
    ) -> None:
        super().__init__(
            hass,
            LOGGER,
            name="EasyControlX status",
            update_interval=update_interval,
        )
        self.client = client

    async def _async_update_data(self) -> EasyControlXStatus:
        """Fetch fresh data from the host."""
        try:
            status = await self.client.async_get_status()
        except InvalidAuth as err:
            raise ConfigEntryAuthFailed("EasyControlX authentication failed.") from err
        except (CannotConnect, ApiError) as err:
            raise UpdateFailed(f"Unable to refresh EasyControlX host status: {err}") from err

        return await self._async_enrich_optional_status(status)

    async def _async_enrich_optional_status(self, status: EasyControlXStatus) -> EasyControlXStatus:
        """Enrich shared status with optional platform-specific inventories."""
        if supports_service_inventory(status):
            try:
                status["serviceInventory"] = await self.client.async_get_services()
            except InvalidAuth as err:
                raise ConfigEntryAuthFailed("EasyControlX authentication failed.") from err
            except (CannotConnect, ApiError) as err:
                LOGGER.debug(
                    "Unable to enrich EasyControlX status with service inventory: %s",
                    err,
                )

        return status
