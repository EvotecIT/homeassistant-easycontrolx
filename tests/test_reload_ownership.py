"""Credential repair reloads through one owner without replacing the entry."""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant import config_entries
from homeassistant.components import websocket_api
from homeassistant.components.config.config_entries import config_entry_update
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.translation import async_get_translations
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.easycontrolx import async_setup_entry
from custom_components.easycontrolx.const import (
    CONF_BASE_URL,
    CONF_DEVICE_ID,
    CONF_TLS_FINGERPRINT,
    DOMAIN,
)

BASE_URL = "https://controller.example.test:7443"
FINGERPRINT = "AB" * 32
DEVICE = {"deviceId": "device-123", "name": "Studio PC"}


async def _entry(hass, monkeypatch, state):
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=DEVICE["deviceId"],
        title="Saved title",
        data={
            CONF_BASE_URL: BASE_URL,
            CONF_ACCESS_TOKEN: "saved-token",
            CONF_DEVICE_ID: DEVICE["deviceId"],
            CONF_TLS_FINGERPRINT: FINGERPRINT,
            "preserved_setting": "keep",
        },
        options={"scan_interval": 45},
    )
    entry.add_to_hass(hass)
    entry.mock_state(hass, state)
    if state is ConfigEntryState.LOADED:
        coordinator = Mock(async_config_entry_first_refresh=AsyncMock())
        monkeypatch.setattr(
            "custom_components.easycontrolx.api.EasyControlXApiClient", Mock()
        )
        monkeypatch.setattr(
            "custom_components.easycontrolx.coordinator.EasyControlXCoordinator",
            Mock(return_value=coordinator),
        )
        monkeypatch.setattr(
            hass.config_entries, "async_forward_entry_setups", AsyncMock()
        )
        assert await async_setup_entry(hass, entry)
    return entry


async def test_connection_success_messages_are_translated(hass):
    """The runtime translation catalog resolves both successful repair reasons."""
    translations = await async_get_translations(hass, "en", "config", {DOMAIN})
    for reason in ("reauth_successful", "reconfigure_successful"):
        assert translations[f"component.{DOMAIN}.config.abort.{reason}"]


@pytest.mark.parametrize("kind", ["token", "reconfigure", "pairing"])
@pytest.mark.parametrize("changed", [True, False])
@pytest.mark.parametrize("state", [ConfigEntryState.LOADED, ConfigEntryState.NOT_LOADED])
async def test_connection_repair_reloads_once(hass, monkeypatch, kind, changed, state):
    """Changed and unchanged repairs reload once with or without a listener."""
    entry = await _entry(hass, monkeypatch, state)
    old_identity = (entry.entry_id, entry.unique_id, entry.title)
    token = "replacement-token" if changed else "saved-token"
    new_url = "https://replacement.example.test:7443" if changed else BASE_URL
    client = AsyncMock()
    client.async_get_device.return_value = DEVICE
    client.async_get_status.return_value = {"device": DEVICE}
    client.async_start_pairing.return_value = {
        "sessionId": "session-1", "verificationCode": "123456"
    }
    client.async_confirm_pairing.return_value = {"accessToken": token}
    monkeypatch.setattr(
        "custom_components.easycontrolx.config_flow._async_build_client",
        AsyncMock(return_value=client),
    )
    reload = AsyncMock(return_value=True)
    monkeypatch.setattr(hass.config_entries, "async_reload", reload)
    source = (
        config_entries.SOURCE_RECONFIGURE if kind == "reconfigure"
        else config_entries.SOURCE_REAUTH
    )
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": source, "entry_id": entry.entry_id},
        data=entry.data if source == config_entries.SOURCE_REAUTH else None,
    )
    user_input = {CONF_TLS_FINGERPRINT: FINGERPRINT}
    if kind == "reconfigure":
        user_input[CONF_BASE_URL] = new_url
    else:
        user_input[CONF_ACCESS_TOKEN] = token if kind == "token" else ""
    result = await hass.config_entries.flow.async_configure(result["flow_id"], user_input)
    if kind == "pairing":
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "pair"
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"verification_code": "123456"}
        )
        client.async_confirm_pairing.assert_awaited_once_with("session-1", "123456")
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == f"{source}_successful"
    reload.assert_awaited_once_with(entry.entry_id)
    assert (entry.entry_id, entry.unique_id, entry.title) == old_identity
    assert entry.options == {"scan_interval": 45}
    assert entry.data["preserved_setting"] == "keep"
    assert entry.data[CONF_TLS_FINGERPRINT] == FINGERPRINT
    assert entry.data[CONF_ACCESS_TOKEN] == ("saved-token" if kind == "reconfigure" else token)
    assert entry.data[CONF_BASE_URL] == (new_url if kind == "reconfigure" else BASE_URL)


async def test_system_polling_options_reload_once(hass, hass_ws_client, monkeypatch):
    """The actual HA system-options handler owns disable and restore reloads."""
    entry = await _entry(hass, monkeypatch, ConfigEntryState.LOADED)
    reload = AsyncMock(return_value=True)
    monkeypatch.setattr(hass.config_entries, "async_reload", reload)
    websocket_api.async_register_command(hass, config_entry_update)
    client = await hass_ws_client(hass)
    try:
        for message_id, disabled in enumerate((True, False), start=1):
            await client.send_json(
                {
                    "id": message_id,
                    "type": "config_entries/update",
                    "entry_id": entry.entry_id,
                    "pref_disable_polling": disabled,
                }
            )
            result = await client.receive_json()
            await hass.async_block_till_done()
            assert result["success"]
            assert entry.pref_disable_polling is disabled
            assert reload.await_count == message_id
    finally:
        await client.close()


@pytest.mark.parametrize("field", ["data", "options", "title", "unique_id"])
async def test_registered_listener_preserves_setting_reload(hass, monkeypatch, field):
    """Integration settings continue to reload through the production listener."""
    entry = await _entry(hass, monkeypatch, ConfigEntryState.LOADED)
    reload = AsyncMock(return_value=True)
    monkeypatch.setattr(hass.config_entries, "async_reload", reload)
    previous = getattr(entry, field)
    changed = (
        dict(previous, qualification_change=True)
        if field in {"data", "options"}
        else f"{previous}-updated"
    )

    hass.config_entries.async_update_entry(entry, **{field: changed})
    await hass.async_block_till_done()

    reload.assert_awaited_once_with(entry.entry_id)


@pytest.mark.parametrize("first_refresh_fails", [False, True])
async def test_options_during_setup_use_new_interval(
    hass, monkeypatch, first_refresh_fails
):
    """Options reload after the setup lock without losing a failed refresh update."""
    entry = await _entry(hass, monkeypatch, ConfigEntryState.NOT_LOADED)
    entered, release = asyncio.Event(), asyncio.Event()
    setup_intervals, unload_states = [], []

    async def first_refresh():
        entered.set()
        await release.wait()
        if first_refresh_fails:
            raise ConfigEntryNotReady("Controller is temporarily unavailable")

    def coordinator_factory(_hass, _client, *, update_interval):
        setup_intervals.append(update_interval.total_seconds())
        return Mock(async_config_entry_first_refresh=AsyncMock(
            side_effect=first_refresh if len(setup_intervals) == 1 else None
        ))

    monkeypatch.setattr("custom_components.easycontrolx.api.EasyControlXApiClient", Mock())
    monkeypatch.setattr(
        "custom_components.easycontrolx.coordinator.EasyControlXCoordinator",
        coordinator_factory,
    )
    monkeypatch.setattr(hass.config_entries, "async_forward_entry_setups", AsyncMock())
    monkeypatch.setattr(
        hass.config_entries, "async_unload_platforms", AsyncMock(return_value=True)
    )
    reload = AsyncMock(wraps=hass.config_entries.async_reload)
    monkeypatch.setattr(hass.config_entries, "async_reload", reload)
    original_unload = hass.config_entries.async_unload

    async def unload(*args, **kwargs):
        unload_states.append(entry.state)
        return await original_unload(*args, **kwargs)

    monkeypatch.setattr(hass.config_entries, "async_unload", unload)
    task = hass.async_create_task(hass.config_entries.async_setup(entry.entry_id))
    await asyncio.wait_for(entered.wait(), timeout=10)
    try:
        result = await hass.config_entries.options.async_init(
            entry.entry_id, data={"scan_interval": 60}
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert entry.state is ConfigEntryState.SETUP_IN_PROGRESS
    finally:
        release.set()
    await task
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert setup_intervals == [45, 60]
    assert unload_states == [
        ConfigEntryState.SETUP_RETRY if first_refresh_fails else ConfigEntryState.LOADED
    ]
    reload.assert_awaited_once_with(entry.entry_id)
    assert len(entry.update_listeners) == 1
