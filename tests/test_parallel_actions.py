"""Host-command concurrency through Home Assistant entity actions."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.easycontrolx.const import DOMAIN


async def test_multi_button_action_serializes_host_commands(hass):
    """One multi-target action must not overlap commands for the same host."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        minor_version=1,
        title="Test host",
        data={
            "base_url": "https://host.local:5188",
            "access_token": "token",
            "device_id": "host-one",
        },
    )
    entry.add_to_hass(hass)
    status = {
        "device": {"deviceId": "host-one", "platform": "Windows"},
        "power": {"supportedActions": ["Lock", "Sleep"]},
    }
    active = 0
    peak = 0
    commands = []

    async def post_power(action, **kwargs):
        nonlocal active, peak
        commands.append(action)
        active += 1
        peak = max(peak, active)
        try:
            await asyncio.sleep(0)
            return {}
        finally:
            active -= 1

    with patch(
        "custom_components.easycontrolx.api.EasyControlXApiClient.async_get_status",
        new_callable=AsyncMock,
        return_value=status,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        registry = er.async_get(hass)
        entity_ids = [
            registry.async_get_entity_id("button", DOMAIN, f"host-one_{key}")
            for key in ("lock", "sleep")
        ]
        assert all(entity_ids)
        with (
            patch.object(entry.runtime_data.client, "async_post_power", post_power),
            patch.object(
                entry.runtime_data.coordinator, "async_request_refresh", new_callable=AsyncMock
            ),
        ):
            await hass.services.async_call(
                "button",
                "press",
                {"entity_id": entity_ids},
                blocking=True,
            )
        assert sorted(commands) == ["Lock", "Sleep"]
        assert peak == 1
        assert await hass.config_entries.async_unload(entry.entry_id)
