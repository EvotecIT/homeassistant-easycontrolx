from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry

if TYPE_CHECKING:
    from .api import EasyControlXApiClient
    from .coordinator import EasyControlXCoordinator


@dataclass(slots=True)
class EasyControlXRuntimeData:
    """Runtime objects stored on a config entry."""

    client: EasyControlXApiClient
    coordinator: EasyControlXCoordinator


EasyControlXConfigEntry = ConfigEntry[EasyControlXRuntimeData]
EasyControlXStatus = dict[str, Any]
