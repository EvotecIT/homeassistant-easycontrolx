"""Client failures retain recovery semantics at HA presentation boundaries."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.translation import async_get_translations
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.easycontrolx.const import DOMAIN, SERVICE_POWER_ACTION
from custom_components.easycontrolx.coordinator import EasyControlXCoordinator
from custom_components.easycontrolx.exceptions import (
    ApiError,
    CannotConnect,
    InvalidAuth,
    TLSCertificateUntrusted,
    TLSFingerprintMismatch,
)

FAILURES = [
    (InvalidAuth, "authentication_failed"),
    (TLSFingerprintMismatch, "certificate_changed"),
    (TLSCertificateUntrusted, "certificate_untrusted"),
    (CannotConnect, "host_unavailable"),
    (ApiError, "request_failed"),
]


@pytest.mark.parametrize(("failure_type", "key"), FAILURES)
@pytest.mark.parametrize("boundary", ["domain", "button"])
@pytest.mark.parametrize("language", ["en", "fr"])
async def test_actions_translate_client_errors(hass, failure_type, key, boundary, language):
    hass.config.language = language
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
        "power": {"supportedActions": ["Lock"]},
    }
    failure = failure_type("private-server-response")
    with patch(
        "custom_components.easycontrolx.api.EasyControlXApiClient.async_get_status",
        new_callable=AsyncMock,
        return_value=status,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        resources = await async_get_translations(hass, language, "exceptions", {DOMAIN})
        with patch.object(
            entry.runtime_data.client,
            "async_post_power",
            new_callable=AsyncMock,
            side_effect=failure,
        ) as action:
            with pytest.raises(HomeAssistantError) as error:
                if boundary == "domain":
                    await hass.services.async_call(
                        DOMAIN,
                        SERVICE_POWER_ACTION,
                        {"action": "Lock"},
                        blocking=True,
                    )
                else:
                    entity_id = er.async_get(hass).async_get_entity_id(
                        "button",
                        DOMAIN,
                        "host-one_lock",
                    )
                    await hass.services.async_call(
                        "button",
                        "press",
                        {"entity_id": entity_id},
                        blocking=True,
                    )
            action.assert_awaited_once()
        assert error.value.translation_domain == DOMAIN
        assert error.value.translation_key == key
        assert error.value.__cause__ is failure
        assert "private-server-response" not in str(error.value)
        message = resources[f"component.{DOMAIN}.exceptions.{key}.message"]
        assert message
        assert "private-server-response" not in message
        assert await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.parametrize(("failure_type", "key"), FAILURES)
async def test_refresh_errors_preserve_authentication_recovery(hass, failure_type, key):
    client = AsyncMock()
    failure = failure_type("private-server-response")
    client.async_get_status.side_effect = failure
    coordinator = EasyControlXCoordinator(hass, client)
    expected = (
        ConfigEntryAuthFailed
        if failure_type in (InvalidAuth, TLSFingerprintMismatch, TLSCertificateUntrusted)
        else UpdateFailed
    )
    with pytest.raises(expected) as error:
        await coordinator._async_update_data()
    assert error.value.translation_domain == DOMAIN
    assert error.value.translation_key == key
    assert error.value.__cause__ is failure
    assert "private-server-response" not in str(error.value)
