"""Credential repair reloads through one owner without replacing the entry."""

from unittest.mock import AsyncMock

import pytest
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.easycontrolx import async_reload_entry
from custom_components.easycontrolx.const import (
    CONF_BASE_URL,
    CONF_DEVICE_ID,
    CONF_TLS_FINGERPRINT,
    DOMAIN,
)

BASE_URL = "https://controller.example.test:7443"
FINGERPRINT = "AB" * 32
DEVICE = {"deviceId": "device-123", "name": "Studio PC"}


@pytest.mark.parametrize("kind", ["token", "reconfigure", "pairing"])
@pytest.mark.parametrize("changed", [True, False])
@pytest.mark.parametrize("state", [ConfigEntryState.LOADED, ConfigEntryState.NOT_LOADED])
async def test_connection_repair_reloads_once(hass, monkeypatch, kind, changed, state):
    """Changed and unchanged repairs reload once with or without a listener."""
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
        entry.async_on_unload(entry.add_update_listener(async_reload_entry))
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
