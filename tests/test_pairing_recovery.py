"""Recovery after a host has approved pairing but setup is not yet valid."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.data_entry_flow import FlowResultType

from custom_components.easycontrolx.const import CONF_BASE_URL, CONF_TLS_FINGERPRINT, DOMAIN
from custom_components.easycontrolx.exceptions import (
    InvalidAuth,
    TLSCertificateUntrusted,
    TLSFingerprintMismatch,
)

BASE_URL = "https://host.example.test:7443"
DEVICE = {"deviceId": "device-123", "name": "Test host", "platform": "Windows"}
PIN = "A1" * 32


@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        (InvalidAuth, "pairing_failed"),
        (TLSFingerprintMismatch, "fingerprint_mismatch"),
        (TLSCertificateUntrusted, "fingerprint_required"),
        ("changed_host", "unique_id_mismatch"),
    ],
)
async def test_issued_token_is_not_saved_until_validation_succeeds(hass, failure, expected):
    client = AsyncMock()
    client.async_get_device.side_effect = [
        DEVICE,
        {**DEVICE, "deviceId": "different-host"} if failure == "changed_host" else DEVICE,
        DEVICE,
    ]
    client.async_start_pairing.return_value = {
        "sessionId": "session-one",
        "verificationCode": "123456",
    }
    client.async_confirm_pairing.return_value = {"accessToken": "issued-token"}
    if failure != "changed_host":
        client.async_get_status.side_effect = [failure("validation rejected"), {}]
    with patch(
        "custom_components.easycontrolx.config_flow._async_build_client",
        new_callable=AsyncMock,
        return_value=client,
    ) as build:
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data={CONF_BASE_URL: BASE_URL, CONF_ACCESS_TOKEN: "", CONF_TLS_FINGERPRINT: PIN},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"verification_code": "123456"},
        )
        assert hass.config_entries.async_entries(DOMAIN) == []
        assert build.await_args.args[2] == "issued-token"
        if failure in (InvalidAuth, "changed_host"):
            assert result["type"] is FlowResultType.ABORT
            assert result["reason"] == expected
            if failure == "changed_host":
                client.async_get_status.assert_not_awaited()
        else:
            assert result["step_id"] == "pairing_retry"
            assert result["errors"] == {CONF_TLS_FINGERPRINT: expected}
            result = await hass.config_entries.flow.async_configure(result["flow_id"], None)
            assert result["step_id"] == "pairing_retry"
            assert result["data_schema"]({})[CONF_TLS_FINGERPRINT] == PIN
            result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
            assert result["type"] is FlowResultType.CREATE_ENTRY
            assert result["data"][CONF_ACCESS_TOKEN] == "issued-token"
            assert result["data"][CONF_TLS_FINGERPRINT] == PIN
    client.async_start_pairing.assert_awaited_once()
    client.async_confirm_pairing.assert_awaited_once_with("session-one", "123456")


@pytest.mark.parametrize("replacement", ["", "B2" * 32])
async def test_certificate_repair_rejects_bad_pin_and_retains_pairing(hass, replacement):
    client = AsyncMock()
    client.async_get_device.return_value = DEVICE
    client.async_start_pairing.return_value = {
        "sessionId": "session-one",
        "verificationCode": "123456",
    }
    client.async_confirm_pairing.side_effect = [
        TLSFingerprintMismatch("certificate changed"),
        {"accessToken": "issued-token"},
    ]
    client.async_get_status.return_value = {}
    with patch(
        "custom_components.easycontrolx.config_flow._async_build_client",
        new_callable=AsyncMock,
        return_value=client,
    ) as build:
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data={CONF_BASE_URL: BASE_URL, CONF_ACCESS_TOKEN: "", CONF_TLS_FINGERPRINT: PIN},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"verification_code": "123456"},
        )
        assert result["step_id"] == "pair_transport_repair"
        result = await hass.config_entries.flow.async_configure(result["flow_id"], None)
        assert result["data_schema"]({})[CONF_TLS_FINGERPRINT] == PIN
        before = build.await_count
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_TLS_FINGERPRINT: "invalid-pin"},
        )
        assert result["errors"] == {CONF_TLS_FINGERPRINT: "invalid_fingerprint"}
        assert build.await_count == before
        assert hass.config_entries.async_entries(DOMAIN) == []
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_TLS_FINGERPRINT: replacement},
        )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_ACCESS_TOKEN] == "issued-token"
    assert result["data"][CONF_TLS_FINGERPRINT] == (replacement or PIN)
    client.async_start_pairing.assert_awaited_once()
    assert client.async_confirm_pairing.await_count == 2
