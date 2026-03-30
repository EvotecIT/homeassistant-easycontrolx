from __future__ import annotations

from typing import Any, cast

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .capabilities import (
    service_inventory_items,
    supported_power_actions,
    supports_app_launch,
    supports_audio,
    supports_file_browse,
    supports_file_copy,
    supports_media,
    supports_process_control,
    supports_process_inventory,
    supports_service_control,
    supports_service_inventory,
)
from .const import (
    ATTR_ACTION,
    ATTR_ALLOW_MULTIPLE_MATCHES,
    ATTR_ARGUMENTS,
    ATTR_DESTINATION_PATH,
    ATTR_OVERWRITE,
    ATTR_PATH,
    ATTR_PROCESS_ID,
    ATTR_PROCESS_NAME,
    ATTR_SERVICE_NAME,
    ATTR_SOURCE_PATH,
    ATTR_TARGET,
    ATTR_VALUE,
    ATTR_WORKING_DIRECTORY,
    AUDIO_ACTIONS,
    CONF_CONFIG_ENTRY_ID,
    DESTRUCTIVE_POWER_ACTIONS,
    DOMAIN,
    MANAGED_SERVICE_ACTIONS,
    MEDIA_ACTIONS,
    POWER_ACTIONS,
    PROCESS_ACTIONS,
    SERVICE_APP_LAUNCH,
    SERVICE_AUDIO_ACTION,
    SERVICE_BROWSE_FILES,
    SERVICE_COPY_FILE,
    SERVICE_LIST_PROCESSES,
    SERVICE_LIST_SERVICES,
    SERVICE_MEDIA_ACTION,
    SERVICE_POWER_ACTION,
    SERVICE_PROCESS_ACTION,
    SERVICE_REFRESH,
    SERVICE_SERVICE_ACTION,
)
from .helpers import normalize_optional_string
from .models import EasyControlXRuntimeData

POWER_ACTION_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_CONFIG_ENTRY_ID): cv.string,
        vol.Required(ATTR_ACTION): vol.In(POWER_ACTIONS),
    }
)

MEDIA_ACTION_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_CONFIG_ENTRY_ID): cv.string,
        vol.Required(ATTR_ACTION): vol.In(MEDIA_ACTIONS),
    }
)

AUDIO_ACTION_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_CONFIG_ENTRY_ID): cv.string,
        vol.Required(ATTR_ACTION): vol.In(AUDIO_ACTIONS),
        vol.Optional(ATTR_VALUE): vol.All(vol.Coerce(int), vol.Range(min=0, max=100)),
    }
)

APP_LAUNCH_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_CONFIG_ENTRY_ID): cv.string,
        vol.Required(ATTR_TARGET): cv.string,
        vol.Optional(ATTR_ARGUMENTS): cv.string,
        vol.Optional(ATTR_WORKING_DIRECTORY): cv.string,
    }
)

PROCESS_ACTION_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_CONFIG_ENTRY_ID): cv.string,
        vol.Required(ATTR_ACTION): vol.In(PROCESS_ACTIONS),
        vol.Optional(ATTR_PROCESS_ID): vol.Coerce(int),
        vol.Optional(ATTR_PROCESS_NAME): cv.string,
        vol.Optional(ATTR_ALLOW_MULTIPLE_MATCHES, default=False): cv.boolean,
    }
)

SERVICE_ACTION_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_CONFIG_ENTRY_ID): cv.string,
        vol.Required(ATTR_ACTION): vol.In(MANAGED_SERVICE_ACTIONS),
        vol.Required(ATTR_SERVICE_NAME): cv.string,
    }
)

BROWSE_FILES_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_CONFIG_ENTRY_ID): cv.string,
        vol.Optional(ATTR_PATH): cv.string,
    }
)

COPY_FILE_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_CONFIG_ENTRY_ID): cv.string,
        vol.Required(ATTR_SOURCE_PATH): cv.string,
        vol.Required(ATTR_DESTINATION_PATH): cv.string,
        vol.Optional(ATTR_OVERWRITE, default=False): cv.boolean,
    }
)

LIST_PROCESSES_SCHEMA = vol.Schema({vol.Optional(CONF_CONFIG_ENTRY_ID): cv.string})
LIST_SERVICES_SCHEMA = vol.Schema({vol.Optional(CONF_CONFIG_ENTRY_ID): cv.string})
REFRESH_SCHEMA = vol.Schema({vol.Optional(CONF_CONFIG_ENTRY_ID): cv.string})


async def async_register_services(hass: HomeAssistant) -> None:
    """Register EasyControlX domain services."""
    _register_service(
        hass,
        SERVICE_POWER_ACTION,
        _async_handle_power_action,
        POWER_ACTION_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    _register_service(
        hass,
        SERVICE_MEDIA_ACTION,
        _async_handle_media_action,
        MEDIA_ACTION_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    _register_service(
        hass,
        SERVICE_AUDIO_ACTION,
        _async_handle_audio_action,
        AUDIO_ACTION_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    _register_service(
        hass,
        SERVICE_APP_LAUNCH,
        _async_handle_app_launch,
        APP_LAUNCH_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    _register_service(
        hass,
        SERVICE_PROCESS_ACTION,
        _async_handle_process_action,
        PROCESS_ACTION_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    _register_service(
        hass,
        SERVICE_SERVICE_ACTION,
        _async_handle_service_action,
        SERVICE_ACTION_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    _register_service(
        hass,
        SERVICE_LIST_PROCESSES,
        _async_handle_list_processes,
        LIST_PROCESSES_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    _register_service(
        hass,
        SERVICE_LIST_SERVICES,
        _async_handle_list_services,
        LIST_SERVICES_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    _register_service(
        hass,
        SERVICE_BROWSE_FILES,
        _async_handle_browse_files,
        BROWSE_FILES_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    _register_service(
        hass,
        SERVICE_COPY_FILE,
        _async_handle_copy_file,
        COPY_FILE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    _register_service(
        hass,
        SERVICE_REFRESH,
        _async_handle_refresh,
        REFRESH_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )


def async_unregister_services(hass: HomeAssistant) -> None:
    """Remove EasyControlX domain services."""
    for service in (
        SERVICE_POWER_ACTION,
        SERVICE_MEDIA_ACTION,
        SERVICE_AUDIO_ACTION,
        SERVICE_APP_LAUNCH,
        SERVICE_PROCESS_ACTION,
        SERVICE_SERVICE_ACTION,
        SERVICE_LIST_PROCESSES,
        SERVICE_LIST_SERVICES,
        SERVICE_BROWSE_FILES,
        SERVICE_COPY_FILE,
        SERVICE_REFRESH,
    ):
        if hass.services.has_service(DOMAIN, service):
            hass.services.async_remove(DOMAIN, service)


async def _async_handle_power_action(call: ServiceCall) -> dict[str, Any]:
    """Run a host power action."""
    runtime_data = _resolve_runtime_data(call.hass, call)
    action = cast(str, call.data[ATTR_ACTION])
    _ensure_supported_power_action(runtime_data, action)

    response = await runtime_data.client.async_post_power(
        action,
        confirmed=action in DESTRUCTIVE_POWER_ACTIONS,
    )
    await runtime_data.coordinator.async_request_refresh()
    return response


async def _async_handle_media_action(call: ServiceCall) -> dict[str, Any]:
    """Run a host media action."""
    runtime_data = _resolve_runtime_data(call.hass, call)
    _ensure_feature_supported(
        runtime_data,
        supported=supports_media(runtime_data.coordinator.data),
        error_message="This EasyControlX host does not expose media controls.",
    )

    action = cast(str, call.data[ATTR_ACTION])
    response = await runtime_data.client.async_post_media(action)
    await runtime_data.coordinator.async_request_refresh()
    return response


async def _async_handle_audio_action(call: ServiceCall) -> dict[str, Any]:
    """Run a host audio action."""
    runtime_data = _resolve_runtime_data(call.hass, call)
    _ensure_feature_supported(
        runtime_data,
        supported=supports_audio(runtime_data.coordinator.data),
        error_message="This EasyControlX host does not expose audio controls.",
    )

    action = cast(str, call.data[ATTR_ACTION])
    value = cast(int | None, call.data.get(ATTR_VALUE))

    if action == "SetOutputVolume" and value is None:
        raise ServiceValidationError("The value field is required for SetOutputVolume.")

    response = await runtime_data.client.async_post_audio(action, value)
    await runtime_data.coordinator.async_request_refresh()
    return response


async def _async_handle_app_launch(call: ServiceCall) -> dict[str, Any]:
    """Launch an application or command target on the host."""
    runtime_data = _resolve_runtime_data(call.hass, call)
    _ensure_feature_supported(
        runtime_data,
        supported=supports_app_launch(runtime_data.coordinator.data),
        error_message="This EasyControlX host does not expose app launch.",
    )

    target = normalize_optional_string(cast(str | None, call.data.get(ATTR_TARGET)))
    if target is None:
        raise ServiceValidationError("The target field is required for app launch.")

    response = await runtime_data.client.async_post_app_launch(
        target,
        arguments=cast(str | None, call.data.get(ATTR_ARGUMENTS)),
        working_directory=cast(str | None, call.data.get(ATTR_WORKING_DIRECTORY)),
    )
    await runtime_data.coordinator.async_request_refresh()
    return response


async def _async_handle_process_action(call: ServiceCall) -> dict[str, Any]:
    """Run a process action on the host."""
    runtime_data = _resolve_runtime_data(call.hass, call)
    _ensure_feature_supported(
        runtime_data,
        supported=supports_process_control(runtime_data.coordinator.data),
        error_message="This EasyControlX host does not expose process control.",
    )

    process_id = cast(int | None, call.data.get(ATTR_PROCESS_ID))
    process_name = normalize_optional_string(cast(str | None, call.data.get(ATTR_PROCESS_NAME)))
    if process_id is None and process_name is None:
        raise ServiceValidationError(
            "Provide process_id or process_name for an EasyControlX process action."
        )

    response = await runtime_data.client.async_post_process(
        cast(str, call.data[ATTR_ACTION]),
        process_id=process_id,
        process_name=process_name,
        allow_multiple_matches=cast(bool, call.data.get(ATTR_ALLOW_MULTIPLE_MATCHES, False)),
    )
    await runtime_data.coordinator.async_request_refresh()
    return response


async def _async_handle_list_processes(call: ServiceCall) -> dict[str, Any]:
    """Return the current process inventory."""
    runtime_data = _resolve_runtime_data(call.hass, call)
    _ensure_feature_supported(
        runtime_data,
        supported=supports_process_inventory(runtime_data.coordinator.data),
        error_message="This EasyControlX host does not expose process inventory.",
    )
    return await runtime_data.client.async_get_processes()


async def _async_handle_service_action(call: ServiceCall) -> dict[str, Any]:
    """Run a curated Windows service action on the host."""
    runtime_data = _resolve_runtime_data(call.hass, call)
    _ensure_feature_supported(
        runtime_data,
        supported=supports_service_control(runtime_data.coordinator.data),
        error_message="This EasyControlX host does not expose managed service control.",
    )

    service_name = normalize_optional_string(cast(str | None, call.data.get(ATTR_SERVICE_NAME)))
    if service_name is None:
        raise ServiceValidationError("The service_name field is required for service control.")

    response = await runtime_data.client.async_post_service(
        cast(str, call.data[ATTR_ACTION]),
        service_name,
    )
    await runtime_data.coordinator.async_request_refresh()
    return response


async def _async_handle_list_services(call: ServiceCall) -> dict[str, Any]:
    """Return the current curated service inventory."""
    runtime_data = _resolve_runtime_data(call.hass, call)
    _ensure_feature_supported(
        runtime_data,
        supported=supports_service_inventory(runtime_data.coordinator.data),
        error_message="This EasyControlX host does not expose managed services.",
    )

    cached_items = service_inventory_items(runtime_data.coordinator.data)
    if cached_items:
        return {
            "services": cached_items,
            "totalServiceCount": len(cached_items),
            "source": "coordinator",
        }

    return await runtime_data.client.async_get_services()


async def _async_handle_browse_files(call: ServiceCall) -> dict[str, Any]:
    """Browse the host file system."""
    runtime_data = _resolve_runtime_data(call.hass, call)
    _ensure_feature_supported(
        runtime_data,
        supported=supports_file_browse(runtime_data.coordinator.data),
        error_message="This EasyControlX host does not expose file browsing.",
    )
    return await runtime_data.client.async_get_files_browse(
        cast(str | None, call.data.get(ATTR_PATH))
    )


async def _async_handle_copy_file(call: ServiceCall) -> dict[str, Any]:
    """Copy a file or directory on the host."""
    runtime_data = _resolve_runtime_data(call.hass, call)
    _ensure_feature_supported(
        runtime_data,
        supported=supports_file_copy(runtime_data.coordinator.data),
        error_message="This EasyControlX host does not expose file copy.",
    )

    source_path = normalize_optional_string(cast(str | None, call.data.get(ATTR_SOURCE_PATH)))
    destination_path = normalize_optional_string(
        cast(str | None, call.data.get(ATTR_DESTINATION_PATH))
    )
    if source_path is None or destination_path is None:
        raise ServiceValidationError(
            "The source_path and destination_path fields are required for file copy."
        )

    response = await runtime_data.client.async_post_files_copy(
        source_path,
        destination_path,
        overwrite=cast(bool, call.data.get(ATTR_OVERWRITE, False)),
    )
    await runtime_data.coordinator.async_request_refresh()
    return response


async def _async_handle_refresh(call: ServiceCall) -> dict[str, Any]:
    """Force a refresh for a configured host."""
    runtime_data = _resolve_runtime_data(call.hass, call)
    await runtime_data.coordinator.async_request_refresh()
    return {"refreshed": True}


def _register_service(
    hass: HomeAssistant,
    service_name: str,
    handler,
    schema: vol.Schema,
    *,
    supports_response: SupportsResponse,
) -> None:
    """Register a service if it does not already exist."""
    if hass.services.has_service(DOMAIN, service_name):
        return

    hass.services.async_register(
        DOMAIN,
        service_name,
        handler,
        schema=schema,
        supports_response=supports_response,
    )


def _ensure_supported_power_action(runtime_data: EasyControlXRuntimeData, action: str) -> None:
    """Validate that the host exposes the requested power action."""
    supported_actions = supported_power_actions(runtime_data.coordinator.data)
    if action not in supported_actions:
        raise ServiceValidationError(
            f"This EasyControlX host does not expose the power action '{action}'."
        )


def _ensure_feature_supported(
    runtime_data: EasyControlXRuntimeData,
    *,
    supported: bool,
    error_message: str,
) -> None:
    """Raise a clean validation error when a host feature is unavailable."""
    if not supported:
        raise ServiceValidationError(error_message)


def _resolve_runtime_data(
    hass: HomeAssistant,
    call: ServiceCall,
) -> EasyControlXRuntimeData:
    """Resolve runtime data for a service call."""
    requested_entry_id = cast(str | None, call.data.get(CONF_CONFIG_ENTRY_ID))
    entries = hass.config_entries.async_entries(DOMAIN)

    entry: ConfigEntry | None = None
    if requested_entry_id:
        entry = next((item for item in entries if item.entry_id == requested_entry_id), None)
        if entry is None:
            raise ServiceValidationError(
                f"EasyControlX config entry '{requested_entry_id}' was not found."
            )
    elif len(entries) == 1:
        entry = entries[0]
    elif not entries:
        raise ServiceValidationError("No EasyControlX hosts are configured.")
    else:
        raise ServiceValidationError(
            "Multiple EasyControlX hosts are configured; provide config_entry_id."
        )

    runtime_data = getattr(entry, "runtime_data", None)
    if runtime_data is None:
        raise ServiceValidationError(
            f"EasyControlX host '{entry.title or entry.entry_id}' is not currently loaded."
        )

    return cast(EasyControlXRuntimeData, runtime_data)
