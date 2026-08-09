from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
import voluptuous as vol
from homeassistant.core import SupportsResponse
from homeassistant.exceptions import ServiceValidationError

from custom_components.easycontrolx.const import (
    ATTR_ACTION,
    ATTR_ALLOW_MULTIPLE_MATCHES,
    ATTR_ARGUMENTS,
    ATTR_DESTINATION_PATH,
    ATTR_OVERWRITE,
    ATTR_PATH,
    ATTR_PROCESS_NAME,
    ATTR_SERVICE_NAME,
    ATTR_SOURCE_PATH,
    ATTR_TARGET,
    ATTR_VALUE,
    ATTR_WORKING_DIRECTORY,
    CONF_CONFIG_ENTRY_ID,
    DOMAIN,
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
from custom_components.easycontrolx.models import EasyControlXRuntimeData
from custom_components.easycontrolx.services import (
    POWER_ACTION_SCHEMA,
    _async_handle_app_launch,
    _async_handle_audio_action,
    _async_handle_browse_files,
    _async_handle_copy_file,
    _async_handle_list_processes,
    _async_handle_list_services,
    _async_handle_media_action,
    _async_handle_power_action,
    _async_handle_process_action,
    _async_handle_refresh,
    _async_handle_service_action,
    _resolve_runtime_data,
    async_register_services,
    async_unregister_services,
)

DEFAULT_STATUS = {
    "device": {
        "capabilities": [
            "applications.launch",
            "processes.list",
            "processes.control",
            "files.browse",
            "files.copy",
            "media",
            "audio.output",
            "windows.services.list",
            "windows.services.control",
        ]
    },
    "power": {"supportedActions": ["Lock", "Sleep", "Restart", "Shutdown"]},
    "media": {"isAvailable": True},
    "audio": {"isAvailable": True},
    "processes": {"itemCount": 42},
    "services": {"itemCount": 2},
    "serviceInventory": {
        "services": [
            {
                "serviceName": "EasyControlX Windows Agent",
                "displayName": "EasyControlX Windows Agent",
            },
            {"serviceName": "Spooler", "displayName": "Print Spooler"},
        ]
    },
}


class _FakeServices:
    def __init__(self) -> None:
        self._handlers: dict[tuple[str, str], tuple[object, object, SupportsResponse]] = {}

    def has_service(self, domain: str, service: str) -> bool:
        return (domain, service) in self._handlers

    def async_register(
        self,
        domain: str,
        service: str,
        handler,
        schema=None,
        *,
        supports_response: SupportsResponse = SupportsResponse.NONE,
    ) -> None:
        self._handlers[(domain, service)] = (handler, schema, supports_response)

    def async_remove(self, domain: str, service: str) -> None:
        self._handlers.pop((domain, service), None)


def _make_hass(entries: list[object] | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        config_entries=SimpleNamespace(async_entries=lambda domain: entries or []),
        services=_FakeServices(),
    )


def _make_entry(
    device_id: str,
    *,
    status: dict | None = None,
) -> tuple[SimpleNamespace, SimpleNamespace, SimpleNamespace]:
    client = SimpleNamespace(
        async_post_power=AsyncMock(return_value={"accepted": True, "operationId": "power"}),
        async_post_media=AsyncMock(return_value={"accepted": True, "operationId": "media"}),
        async_post_audio=AsyncMock(return_value={"accepted": True, "operationId": "audio"}),
        async_post_app_launch=AsyncMock(
            return_value={"accepted": True, "operationId": "launch", "targetProcessId": 1234}
        ),
        async_get_processes=AsyncMock(return_value={"totalProcessCount": 42, "processes": []}),
        async_post_process=AsyncMock(return_value={"accepted": True, "operationId": "process"}),
        async_get_services=AsyncMock(return_value={
            "totalServiceCount": 2,
            "services": DEFAULT_STATUS["serviceInventory"]["services"],
        }),
        async_post_service=AsyncMock(return_value={"accepted": True, "operationId": "service"}),
        async_get_files_browse=AsyncMock(return_value={"currentPath": "C:\\", "entries": []}),
        async_post_files_copy=AsyncMock(return_value={"accepted": True, "operationId": "copy"}),
    )
    coordinator = SimpleNamespace(
        async_request_refresh=AsyncMock(),
        data=status or DEFAULT_STATUS,
    )
    entry = SimpleNamespace(
        entry_id=f"{device_id}-entry",
        title=device_id,
        runtime_data=EasyControlXRuntimeData(client=client, coordinator=coordinator),
    )
    return entry, client, coordinator


def _make_call(hass: SimpleNamespace, data: dict[str, object]) -> SimpleNamespace:
    return SimpleNamespace(hass=hass, data=data)


@pytest.mark.asyncio
async def test_register_and_unregister_services() -> None:
    hass = _make_hass()

    await async_register_services(hass)

    assert hass.services.has_service(DOMAIN, SERVICE_POWER_ACTION)
    assert hass.services.has_service(DOMAIN, SERVICE_MEDIA_ACTION)
    assert hass.services.has_service(DOMAIN, SERVICE_AUDIO_ACTION)
    assert hass.services.has_service(DOMAIN, SERVICE_APP_LAUNCH)
    assert hass.services.has_service(DOMAIN, SERVICE_PROCESS_ACTION)
    assert hass.services.has_service(DOMAIN, SERVICE_SERVICE_ACTION)
    assert hass.services.has_service(DOMAIN, SERVICE_LIST_PROCESSES)
    assert hass.services.has_service(DOMAIN, SERVICE_LIST_SERVICES)
    assert hass.services.has_service(DOMAIN, SERVICE_BROWSE_FILES)
    assert hass.services.has_service(DOMAIN, SERVICE_COPY_FILE)
    assert hass.services.has_service(DOMAIN, SERVICE_REFRESH)
    assert hass.services._handlers[(DOMAIN, SERVICE_LIST_PROCESSES)][2] == SupportsResponse.ONLY
    assert hass.services._handlers[(DOMAIN, SERVICE_POWER_ACTION)][2] == SupportsResponse.OPTIONAL

    async_unregister_services(hass)

    assert not hass.services.has_service(DOMAIN, SERVICE_POWER_ACTION)
    assert not hass.services.has_service(DOMAIN, SERVICE_MEDIA_ACTION)
    assert not hass.services.has_service(DOMAIN, SERVICE_AUDIO_ACTION)
    assert not hass.services.has_service(DOMAIN, SERVICE_APP_LAUNCH)
    assert not hass.services.has_service(DOMAIN, SERVICE_PROCESS_ACTION)
    assert not hass.services.has_service(DOMAIN, SERVICE_SERVICE_ACTION)
    assert not hass.services.has_service(DOMAIN, SERVICE_LIST_PROCESSES)
    assert not hass.services.has_service(DOMAIN, SERVICE_LIST_SERVICES)
    assert not hass.services.has_service(DOMAIN, SERVICE_BROWSE_FILES)
    assert not hass.services.has_service(DOMAIN, SERVICE_COPY_FILE)
    assert not hass.services.has_service(DOMAIN, SERVICE_REFRESH)


@pytest.mark.asyncio
async def test_power_action_targets_only_configured_host() -> None:
    entry, client, coordinator = _make_entry("host-one")
    hass = _make_hass([entry])

    response = await _async_handle_power_action(_make_call(hass, {ATTR_ACTION: "Lock"}))

    assert response == {"accepted": True, "operationId": "power"}
    client.async_post_power.assert_awaited_once_with("Lock", confirmed=False)
    coordinator.async_request_refresh.assert_awaited_once()


def test_power_action_schema_excludes_destructive_host_actions() -> None:
    with pytest.raises(vol.Invalid):
        POWER_ACTION_SCHEMA({ATTR_ACTION: "Restart"})

    with pytest.raises(vol.Invalid):
        POWER_ACTION_SCHEMA({ATTR_ACTION: "Shutdown"})


@pytest.mark.asyncio
async def test_media_action_uses_requested_config_entry() -> None:
    entry_one, client_one, _coordinator_one = _make_entry("host-one")
    entry_two, client_two, coordinator_two = _make_entry("host-two")
    hass = _make_hass([entry_one, entry_two])

    response = await _async_handle_media_action(
        _make_call(
            hass,
            {
                CONF_CONFIG_ENTRY_ID: entry_two.entry_id,
                ATTR_ACTION: "NextTrack",
            },
        )
    )

    assert response == {"accepted": True, "operationId": "media"}
    client_one.async_post_media.assert_not_awaited()
    client_two.async_post_media.assert_awaited_once_with("NextTrack")
    coordinator_two.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_audio_set_volume_requires_value() -> None:
    entry, _client, _coordinator = _make_entry("host-one")
    hass = _make_hass([entry])

    with pytest.raises(ServiceValidationError, match="value field is required"):
        await _async_handle_audio_action(_make_call(hass, {ATTR_ACTION: "SetOutputVolume"}))


@pytest.mark.asyncio
async def test_refresh_requires_config_entry_id_when_multiple_hosts_exist() -> None:
    entry_one, _client_one, _coordinator_one = _make_entry("host-one")
    entry_two, _client_two, _coordinator_two = _make_entry("host-two")
    hass = _make_hass([entry_one, entry_two])

    with pytest.raises(ServiceValidationError, match="provide config_entry_id"):
        await _async_handle_refresh(_make_call(hass, {}))


@pytest.mark.asyncio
async def test_audio_action_refreshes_after_call() -> None:
    entry, client, coordinator = _make_entry("host-one")
    hass = _make_hass([entry])

    response = await _async_handle_audio_action(
        _make_call(
            hass,
            {
                ATTR_ACTION: "SetOutputVolume",
                ATTR_VALUE: 35,
            },
        )
    )

    assert response == {"accepted": True, "operationId": "audio"}
    client.async_post_audio.assert_awaited_once_with("SetOutputVolume", 35)
    coordinator.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_app_launch_returns_action_response() -> None:
    entry, client, coordinator = _make_entry("host-one")
    hass = _make_hass([entry])

    response = await _async_handle_app_launch(
        _make_call(
            hass,
            {
                ATTR_TARGET: "notepad.exe",
                ATTR_ARGUMENTS: " --new-window ",
                ATTR_WORKING_DIRECTORY: " C:\\Users\\Public ",
            },
        )
    )

    assert response["targetProcessId"] == 1234
    client.async_post_app_launch.assert_awaited_once_with(
        "notepad.exe",
        arguments=" --new-window ",
        working_directory=" C:\\Users\\Public ",
    )
    coordinator.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_action_requires_process_identifier() -> None:
    entry, _client, _coordinator = _make_entry("host-one")
    hass = _make_hass([entry])

    with pytest.raises(ServiceValidationError, match="Provide process_id or process_name"):
        await _async_handle_process_action(
            _make_call(
                hass,
                {
                    ATTR_ACTION: "Terminate",
                    ATTR_ALLOW_MULTIPLE_MATCHES: True,
                },
            )
        )


@pytest.mark.asyncio
async def test_process_action_returns_action_response() -> None:
    entry, client, coordinator = _make_entry("host-one")
    hass = _make_hass([entry])

    response = await _async_handle_process_action(
        _make_call(
            hass,
            {
                ATTR_ACTION: "CloseMainWindow",
                ATTR_PROCESS_NAME: "notepad",
                ATTR_ALLOW_MULTIPLE_MATCHES: True,
            },
        )
    )

    assert response == {"accepted": True, "operationId": "process"}
    client.async_post_process.assert_awaited_once_with(
        "CloseMainWindow",
        process_id=None,
        process_name="notepad",
        allow_multiple_matches=True,
    )
    coordinator.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_processes_returns_inventory_payload() -> None:
    entry, client, _coordinator = _make_entry("host-one")
    hass = _make_hass([entry])

    response = await _async_handle_list_processes(_make_call(hass, {}))

    assert response == {"totalProcessCount": 42, "processes": []}
    client.async_get_processes.assert_awaited_once_with()


@pytest.mark.asyncio
async def test_service_action_returns_action_response() -> None:
    entry, client, coordinator = _make_entry("host-one")
    hass = _make_hass([entry])

    response = await _async_handle_service_action(
        _make_call(
            hass,
            {
                ATTR_ACTION: "Restart",
                ATTR_SERVICE_NAME: "EasyControlX Windows Agent",
            },
        )
    )

    assert response == {"accepted": True, "operationId": "service"}
    client.async_post_service.assert_awaited_once_with(
        "Restart",
        "EasyControlX Windows Agent",
    )
    coordinator.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_services_prefers_coordinator_inventory_when_available() -> None:
    entry, client, _coordinator = _make_entry("host-one")
    hass = _make_hass([entry])

    response = await _async_handle_list_services(_make_call(hass, {}))

    assert response["source"] == "coordinator"
    assert len(response["services"]) == 2
    client.async_get_services.assert_not_awaited()


@pytest.mark.asyncio
async def test_browse_files_returns_inventory_payload() -> None:
    entry, client, _coordinator = _make_entry("host-one")
    hass = _make_hass([entry])

    response = await _async_handle_browse_files(
        _make_call(
            hass,
            {
                ATTR_PATH: " C:\\Users ",
            },
        )
    )

    assert response == {"currentPath": "C:\\", "entries": []}
    client.async_get_files_browse.assert_awaited_once_with(" C:\\Users ")


@pytest.mark.asyncio
async def test_copy_file_returns_action_response() -> None:
    entry, client, coordinator = _make_entry("host-one")
    hass = _make_hass([entry])

    response = await _async_handle_copy_file(
        _make_call(
            hass,
            {
                ATTR_SOURCE_PATH: " C:\\Source.txt ",
                ATTR_DESTINATION_PATH: " C:\\Dest.txt ",
                ATTR_OVERWRITE: True,
            },
        )
    )

    assert response == {"accepted": True, "operationId": "copy"}
    client.async_post_files_copy.assert_awaited_once_with(
        "C:\\Source.txt",
        "C:\\Dest.txt",
        overwrite=True,
    )
    coordinator.async_request_refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_capability_checks_raise_clean_errors() -> None:
    unsupported_status = {
        "device": {"capabilities": []},
        "power": {"supportedActions": []},
    }
    entry, _client, _coordinator = _make_entry("host-one", status=unsupported_status)
    hass = _make_hass([entry])

    with pytest.raises(ServiceValidationError, match="does not expose app launch"):
        await _async_handle_app_launch(_make_call(hass, {ATTR_TARGET: "notepad.exe"}))

    with pytest.raises(ServiceValidationError, match="does not expose file browsing"):
        await _async_handle_browse_files(_make_call(hass, {}))


def test_resolve_runtime_data_requires_known_entry_id() -> None:
    entry, _client, _coordinator = _make_entry("host-one")
    hass = _make_hass([entry])

    with pytest.raises(ServiceValidationError, match="was not found"):
        _resolve_runtime_data(
            hass,
            _make_call(hass, {CONF_CONFIG_ENTRY_ID: "missing-entry"}),
        )


def test_resolve_runtime_data_requires_loaded_runtime_data() -> None:
    entry = SimpleNamespace(entry_id="host-one-entry", title="host-one", runtime_data=None)
    hass = _make_hass([entry])

    with pytest.raises(ServiceValidationError, match="not currently loaded"):
        _resolve_runtime_data(hass, _make_call(hass, {}))
