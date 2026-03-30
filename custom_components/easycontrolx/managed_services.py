from __future__ import annotations

from typing import Any

from homeassistant.util import slugify

from .capabilities import service_inventory_items
from .entity import EasyControlXEntity
from .models import EasyControlXConfigEntry


class EasyControlXManagedServiceEntity(EasyControlXEntity):
    """Shared behavior for entities bound to a managed host service."""

    def __init__(
        self,
        config_entry: EasyControlXConfigEntry,
        service: dict[str, Any],
    ) -> None:
        super().__init__(config_entry)
        self._service_name = str(service.get("serviceName", "service"))
        self._service_key = slugify(self._service_name)
        self._service_display_name = str(service.get("displayName") or self._service_name)

    @property
    def service_name(self) -> str:
        """Return the managed service name."""
        return self._service_name

    @property
    def service_display_name(self) -> str:
        """Return the managed service display name."""
        return self._service_display_name

    @property
    def service_key(self) -> str:
        """Return a slug-safe key for the managed service."""
        return self._service_key

    @property
    def service_data(self) -> dict[str, Any] | None:
        """Return the current coordinator payload for this managed service."""
        for service in service_inventory_items(self.coordinator.data):
            if str(service.get("serviceName", "")).lower() == self._service_name.lower():
                return service
        return None

    @property
    def service_exists(self) -> bool:
        """Return whether the managed service currently exists on the host."""
        service = self.service_data
        return bool(service and service.get("exists", False))

    def service_state_attributes(self) -> dict[str, Any]:
        """Return common state attributes for managed service entities."""
        service = self.service_data or {}
        return {
            "service_name": self._service_name,
            "display_name": self._service_display_name,
            "exists": service.get("exists"),
            "status": service.get("status"),
            "start_type": service.get("startType"),
            "can_stop": service.get("canStop"),
            "description": service.get("description"),
        }
