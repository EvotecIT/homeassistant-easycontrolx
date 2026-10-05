"""Contract tests for secure EasyControlX setup and repair flows."""

from __future__ import annotations

from ipaddress import ip_address
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import (
    SOURCE_REAUTH,
    SOURCE_RECONFIGURE,
    SOURCE_USER,
    SOURCE_ZEROCONF,
)
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType, InvalidData
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.easycontrolx.config_flow import EasyControlXConfigFlow
from custom_components.easycontrolx.const import (
    CONF_BASE_URL,
    CONF_CONTROLLER_NAME,
    CONF_DEVICE_ID,
    CONF_PREFERRED_MONITOR_ID,
    CONF_SCAN_INTERVAL,
    CONF_TLS_FINGERPRINT,
    DOMAIN,
)
from custom_components.easycontrolx.exceptions import (
    ApiError,
    CannotConnect,
    InvalidAuth,
    PairingExpired,
    PairingPending,
    TLSCertificateUntrusted,
    TLSFingerprintMismatch,
)

BASE_URL = "https://studio-pc.example.test:7443"
DEVICE_URL = f"{BASE_URL}/api/v1/device"
STATUS_URL = f"{BASE_URL}/api/v1/status"
PAIR_START_URL = f"{BASE_URL}/api/v1/pair/start"
PAIR_CONFIRM_URL = f"{BASE_URL}/api/v1/pair/confirm"
DEVICE = {
    "deviceId": "device-123",
    "name": "Studio PC",
    "platform": "Windows",
    "protocolVersion": "1",
}


def _zeroconf_info(
    *,
    hostname: str = "studio-pc.local.",
    properties: dict[str, str] | None = None,
) -> ZeroconfServiceInfo:
    return ZeroconfServiceInfo(
        ip_address=ip_address("192.0.2.15"),
        ip_addresses=[ip_address("192.0.2.15")],
        port=7443,
        hostname=hostname,
        type="_easycontrolx._tcp.local.",
        name="Studio PC._easycontrolx._tcp.local.",
        properties=properties or {},
    )


def test_discovery_with_certificate_hint_defaults_to_https() -> None:
    fingerprint = "A1" * 32
    info = _zeroconf_info(properties={"tlsFingerprint": fingerprint})

    assert EasyControlXConfigFlow._async_base_url_from_discovery(info) == (
        "https://studio-pc.local:7443"
    )
    assert EasyControlXConfigFlow._discovery_fingerprint(info.properties) == fingerprint


def test_discovery_preserves_valid_reverse_proxy_base_path() -> None:
    info = _zeroconf_info(
        properties={"baseUrl": "https://proxy.example.test/easycontrolx/"}
    )

    assert EasyControlXConfigFlow._async_base_url_from_discovery(info) == (
        "https://proxy.example.test/easycontrolx"
    )


def test_discovery_rejects_invalid_advertised_base_url_cleanly() -> None:
    info = _zeroconf_info(
        properties={"baseUrl": "https://user:secret@proxy.example.test/easycontrolx"}
    )

    assert EasyControlXConfigFlow._async_base_url_from_discovery(info) is None


async def test_discovery_fingerprint_requires_explicit_host_comparison(
    hass: HomeAssistant,
) -> None:
    fingerprint = "A1" * 32
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_ZEROCONF},
        data=_zeroconf_info(
            properties={"deviceid": "device-123", "tlsFingerprint": fingerprint}
        ),
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_BASE_URL: "https://studio-pc.local:7443",
            CONF_ACCESS_TOKEN: "",
            CONF_TLS_FINGERPRINT: "",
            CONF_CONTROLLER_NAME: "Home Assistant",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_TLS_FINGERPRINT: "fingerprint_required"}


async def test_manual_setup_rejects_plain_http(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={
            CONF_BASE_URL: "http://studio-pc.example.test:7443",
            CONF_ACCESS_TOKEN: "controller-token",
            CONF_TLS_FINGERPRINT: "A1" * 32,
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_BASE_URL: "https_required"}


async def test_manual_setup_rejects_malformed_fingerprint(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={
            CONF_BASE_URL: BASE_URL,
            CONF_ACCESS_TOKEN: "controller-token",
            CONF_TLS_FINGERPRINT: "not-a-fingerprint",
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_TLS_FINGERPRINT: "invalid_fingerprint"}


async def test_existing_token_is_validated_before_storage(
    hass: HomeAssistant,
    aioclient_mock,
) -> None:
    aioclient_mock.get(DEVICE_URL, json=DEVICE)
    aioclient_mock.get(STATUS_URL, json={"device": DEVICE})

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={
            CONF_BASE_URL: BASE_URL,
            CONF_ACCESS_TOKEN: "controller-token",
            CONF_TLS_FINGERPRINT: "",
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Studio PC"
    assert result["data"] == {
        CONF_BASE_URL: BASE_URL,
        CONF_ACCESS_TOKEN: "controller-token",
        CONF_DEVICE_ID: "device-123",
        CONF_TLS_FINGERPRINT: "",
    }


async def test_pairing_requires_typed_code_and_host_issued_token_validation(
    hass: HomeAssistant,
    aioclient_mock,
) -> None:
    aioclient_mock.get(DEVICE_URL, json=DEVICE)
    aioclient_mock.post(
        PAIR_START_URL,
        json={"sessionId": "session-1", "verificationCode": "741258"},
    )
    aioclient_mock.post(PAIR_CONFIRM_URL, json={"accessToken": "paired-token"})
    aioclient_mock.get(STATUS_URL, json={"device": DEVICE})

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_USER},
        data={
            CONF_BASE_URL: BASE_URL,
            CONF_ACCESS_TOKEN: "",
            CONF_TLS_FINGERPRINT: "",
            CONF_CONTROLLER_NAME: "Home Assistant",
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "pair"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"verification_code": "000000"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "code_mismatch"}

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"verification_code": "741258"}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_ACCESS_TOKEN] == "paired-token"
    assert result["data"][CONF_DEVICE_ID] == "device-123"


async def test_pairing_retry_preserves_token_and_accepts_verified_fingerprint(
    hass: HomeAssistant,
) -> None:
    client = AsyncMock()
    client.async_get_device.return_value = DEVICE
    client.async_start_pairing.return_value = {
        "sessionId": "session-1",
        "verificationCode": "741258",
    }
    client.async_confirm_pairing.return_value = {"accessToken": "paired-token"}
    client.async_get_status.side_effect = [
        CannotConnect("self-signed certificate"),
        {"device": DEVICE},
    ]

    with patch(
        "custom_components.easycontrolx.config_flow._async_build_client",
        AsyncMock(return_value=client),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data={
                CONF_BASE_URL: BASE_URL,
                CONF_ACCESS_TOKEN: "",
                CONF_TLS_FINGERPRINT: "A1" * 32,
                CONF_CONTROLLER_NAME: "Home Assistant",
            },
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"verification_code": "741258"}
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "pairing_retry"
        assert result["errors"] == {"base": "cannot_connect"}

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_TLS_FINGERPRINT: "not-a-fingerprint"}
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {CONF_TLS_FINGERPRINT: "invalid_fingerprint"}

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_TLS_FINGERPRINT: ""}
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_ACCESS_TOKEN] == "paired-token"
    assert result["data"][CONF_TLS_FINGERPRINT] == "A1" * 32
    client.async_confirm_pairing.assert_awaited_once_with("session-1", "741258")


async def test_pairing_certificate_repair_preserves_approved_session(
    hass: HomeAssistant,
) -> None:
    client = AsyncMock()
    client.async_get_device.return_value = DEVICE
    client.async_start_pairing.return_value = {
        "sessionId": "session-1",
        "verificationCode": "741258",
    }
    client.async_confirm_pairing.side_effect = [
        TLSFingerprintMismatch("certificate changed"),
        {"accessToken": "paired-token"},
    ]
    client.async_get_status.return_value = {"device": DEVICE}

    with patch(
        "custom_components.easycontrolx.config_flow._async_build_client",
        AsyncMock(return_value=client),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data={
                CONF_BASE_URL: BASE_URL,
                CONF_ACCESS_TOKEN: "",
                CONF_TLS_FINGERPRINT: "A1" * 32,
                CONF_CONTROLLER_NAME: "Home Assistant",
            },
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"verification_code": "741258"}
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "pair_transport_repair"
        assert result["errors"] == {CONF_TLS_FINGERPRINT: "fingerprint_mismatch"}

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_TLS_FINGERPRINT: "B2" * 32}
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_ACCESS_TOKEN] == "paired-token"
    assert result["data"][CONF_TLS_FINGERPRINT] == "B2" * 32
    assert client.async_confirm_pairing.await_count == 2


async def test_reauth_replaces_token_without_downgrading_certificate_trust(
    hass: HomeAssistant,
    aioclient_mock,
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="device-123",
        data={
            CONF_BASE_URL: BASE_URL,
            CONF_ACCESS_TOKEN: "revoked-token",
            CONF_DEVICE_ID: "device-123",
            CONF_TLS_FINGERPRINT: "A1" * 32,
        },
    )
    entry.add_to_hass(hass)
    aioclient_mock.get(DEVICE_URL, json=DEVICE)
    aioclient_mock.get(STATUS_URL, json={"device": DEVICE})

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_REAUTH, "entry_id": entry.entry_id},
        data=entry.data,
    )
    with patch.object(
        hass.config_entries,
        "async_reload",
        AsyncMock(return_value=True),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_ACCESS_TOKEN: "replacement-token",
                CONF_TLS_FINGERPRINT: "",
            },
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_ACCESS_TOKEN] == "replacement-token"
    assert entry.data[CONF_TLS_FINGERPRINT] == "A1" * 32
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1


async def test_reauth_checks_host_identity_before_sending_replacement_token(
    hass: HomeAssistant,
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="device-123",
        data={
            CONF_BASE_URL: BASE_URL,
            CONF_ACCESS_TOKEN: "revoked-token",
            CONF_DEVICE_ID: "device-123",
            CONF_TLS_FINGERPRINT: "A1" * 32,
        },
    )
    entry.add_to_hass(hass)
    client = AsyncMock()
    client.async_get_device.return_value = {**DEVICE, "deviceId": "attacker-device"}

    with patch(
        "custom_components.easycontrolx.config_flow._async_build_client",
        AsyncMock(return_value=client),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_REAUTH, "entry_id": entry.entry_id},
            data=entry.data,
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_ACCESS_TOKEN: "replacement-token",
                CONF_TLS_FINGERPRINT: "A1" * 32,
            },
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "unique_id_mismatch"
    client.async_get_status.assert_not_awaited()


async def test_reconfigure_checks_host_identity_before_sending_stored_token(
    hass: HomeAssistant,
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="device-123",
        data={
            CONF_BASE_URL: BASE_URL,
            CONF_ACCESS_TOKEN: "controller-token",
            CONF_DEVICE_ID: "device-123",
            CONF_TLS_FINGERPRINT: "A1" * 32,
        },
    )
    entry.add_to_hass(hass)
    client = AsyncMock()
    client.async_get_device.return_value = {**DEVICE, "deviceId": "attacker-device"}

    with patch(
        "custom_components.easycontrolx.config_flow._async_build_client",
        AsyncMock(return_value=client),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_RECONFIGURE, "entry_id": entry.entry_id},
            data=None,
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_BASE_URL: "https://replacement.example.test/easycontrolx",
                CONF_TLS_FINGERPRINT: "",
            },
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "unique_id_mismatch"
    client.async_get_status.assert_not_awaited()
    assert entry.data[CONF_TLS_FINGERPRINT] == "A1" * 32


async def test_reconfigure_preserves_pin_when_fingerprint_field_is_blank(
    hass: HomeAssistant,
) -> None:
    fingerprint = "A1" * 32
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="device-123",
        data={
            CONF_BASE_URL: BASE_URL,
            CONF_ACCESS_TOKEN: "controller-token",
            CONF_DEVICE_ID: "device-123",
            CONF_TLS_FINGERPRINT: fingerprint,
        },
    )
    entry.add_to_hass(hass)
    client = AsyncMock()
    client.async_get_device.return_value = DEVICE
    client.async_get_status.return_value = {"device": DEVICE}
    build_client = AsyncMock(return_value=client)

    with (
        patch(
            "custom_components.easycontrolx.config_flow._async_build_client",
            build_client,
        ),
        patch.object(
            hass.config_entries,
            "async_reload",
            AsyncMock(return_value=True),
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_RECONFIGURE, "entry_id": entry.entry_id},
            data=None,
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_BASE_URL: "https://replacement.example.test/easycontrolx",
                CONF_TLS_FINGERPRINT: "",
            },
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data[CONF_TLS_FINGERPRINT] == fingerprint
    build_client.assert_awaited_once_with(
        hass,
        "https://replacement.example.test/easycontrolx",
        "controller-token",
        fingerprint,
    )


async def test_zeroconf_cannot_repoint_an_existing_token(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="device-123",
        data={
            CONF_BASE_URL: BASE_URL,
            CONF_ACCESS_TOKEN: "controller-token",
            CONF_DEVICE_ID: "device-123",
            CONF_TLS_FINGERPRINT: "",
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_ZEROCONF},
        data=_zeroconf_info(
            hostname="attacker.example.test.",
            properties={
                "deviceid": "device-123",
                "baseUrl": "https://attacker.example.test:7443",
            },
        ),
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.data[CONF_BASE_URL] == BASE_URL
    assert entry.data[CONF_ACCESS_TOKEN] == "controller-token"


async def test_discovered_identity_is_checked_before_sending_user_token(
    hass: HomeAssistant,
) -> None:
    client = AsyncMock()
    client.async_get_device.return_value = {**DEVICE, "deviceId": "attacker-device"}

    with patch(
        "custom_components.easycontrolx.config_flow._async_build_client",
        AsyncMock(return_value=client),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_ZEROCONF},
            data=_zeroconf_info(
                properties={
                    "deviceid": "device-123",
                    "baseUrl": BASE_URL,
                }
            ),
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_BASE_URL: BASE_URL,
                CONF_ACCESS_TOKEN: "controller-token",
                CONF_TLS_FINGERPRINT: "",
                CONF_CONTROLLER_NAME: "Home Assistant",
            },
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "unique_id_mismatch"
    client.async_get_status.assert_not_awaited()


@pytest.mark.parametrize("source", [SOURCE_USER, SOURCE_REAUTH, SOURCE_RECONFIGURE])
@pytest.mark.parametrize("failure,errors", [
    (TLSFingerprintMismatch, {CONF_TLS_FINGERPRINT: "fingerprint_mismatch"}),
    (TLSCertificateUntrusted, {CONF_TLS_FINGERPRINT: "fingerprint_required"}),
    (CannotConnect, {"base": "cannot_connect"}),
    (InvalidAuth, {"base": "invalid_auth"}),
    (ApiError, {"base": "unknown"}),
])
async def test_connection_failures_preserve_configuration(hass, source, failure, errors):
    original = {
        CONF_BASE_URL: BASE_URL,
        CONF_ACCESS_TOKEN: "existing-token",
        CONF_DEVICE_ID: "device-123",
        CONF_TLS_FINGERPRINT: "A1" * 32,
    }
    entry = MockConfigEntry(domain=DOMAIN, unique_id="device-123", data=original)
    context = {"source": source}
    if source != SOURCE_USER:
        entry.add_to_hass(hass)
        context["entry_id"] = entry.entry_id
    client = AsyncMock()
    client.async_get_device.side_effect = failure("validation failed")
    with (
        patch("custom_components.easycontrolx.config_flow._async_build_client",
              new_callable=AsyncMock, return_value=client),
        patch.object(hass.config_entries, "async_reload", new_callable=AsyncMock) as reload,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context=context, data=original if source == SOURCE_REAUTH else None,
        )
        submitted = {
            CONF_BASE_URL: BASE_URL, CONF_ACCESS_TOKEN: "replacement-token",
            CONF_TLS_FINGERPRINT: "A1" * 32,
        }
        if source == SOURCE_REAUTH:
            submitted.pop(CONF_BASE_URL)
        elif source == SOURCE_RECONFIGURE:
            submitted.pop(CONF_ACCESS_TOKEN)
        result = await hass.config_entries.flow.async_configure(result["flow_id"], submitted)
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == errors
        assert dict(entry.data) == original
        reload.assert_not_awaited()
        client.async_get_status.assert_not_awaited()
        assert len(hass.config_entries.async_entries(DOMAIN)) == (source != SOURCE_USER)


async def test_options_validate_interval_and_reopen_saved_monitor(hass):
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_BASE_URL: BASE_URL, CONF_ACCESS_TOKEN: "token"},
        options={CONF_SCAN_INTERVAL: 20, CONF_PREFERRED_MONITOR_ID: "monitor-one"},
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    with pytest.raises(InvalidData):
        await hass.config_entries.options.async_configure(
            result["flow_id"], {CONF_SCAN_INTERVAL: 0},
        )
    assert entry.options[CONF_SCAN_INTERVAL] == 20
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_SCAN_INTERVAL: 30, CONF_PREFERRED_MONITOR_ID: " monitor-two "},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert dict(entry.options) == {
        CONF_SCAN_INTERVAL: 30, CONF_PREFERRED_MONITOR_ID: "monitor-two",
    }
    reopened = await hass.config_entries.options.async_init(entry.entry_id)
    assert reopened["data_schema"]({})[CONF_SCAN_INTERVAL] == 30
    monitor_key = next(
        key for key in reopened["data_schema"].schema
        if str(key) == CONF_PREFERRED_MONITOR_ID
    )
    assert monitor_key.description["suggested_value"] == "monitor-two"


@pytest.mark.parametrize("failure,step,errors", [
    (PairingPending, "pair", {"base": "pairing_pending"}),
    (PairingExpired, "pair", {"base": "pairing_expired"}),
    (CannotConnect, "pair", {"base": "cannot_connect"}),
    (InvalidAuth, "pair", {"base": "pairing_failed"}),
    (ApiError, "pair", {"base": "pairing_failed"}),
    (TLSCertificateUntrusted, "pair_transport_repair",
     {CONF_TLS_FINGERPRINT: "fingerprint_required"}),
    (None, "pair", {"base": "pairing_pending"}),
])
async def test_pairing_failures_do_not_store_unvalidated_credentials(hass, failure, step, errors):
    client = AsyncMock()
    client.async_get_device.return_value = DEVICE
    client.async_start_pairing.return_value = {
        "sessionId": "session-one", "verificationCode": "123456",
    }
    client.async_confirm_pairing.return_value = {}
    if failure is not None:
        client.async_confirm_pairing.side_effect = failure("approval unavailable")
    with patch("custom_components.easycontrolx.config_flow._async_build_client",
               new_callable=AsyncMock, return_value=client):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER},
            data={CONF_BASE_URL: BASE_URL, CONF_ACCESS_TOKEN: ""},
        )
        assert result["step_id"] == "pair"
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"verification_code": "123456"},
        )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == step
    assert result["errors"] == errors
    assert hass.config_entries.async_entries(DOMAIN) == []
    client.async_get_status.assert_not_awaited()
    client.async_confirm_pairing.assert_awaited_once_with("session-one", "123456")


async def test_reauth_pairing_replaces_credentials_only_after_host_approval(hass, aioclient_mock):
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id="device-123",
        data={
            CONF_BASE_URL: BASE_URL, CONF_ACCESS_TOKEN: "revoked-token",
            CONF_DEVICE_ID: "device-123", CONF_TLS_FINGERPRINT: "A1" * 32,
        },
    )
    entry.add_to_hass(hass)
    aioclient_mock.get(DEVICE_URL, json=DEVICE)
    aioclient_mock.post(PAIR_START_URL, json={
        "sessionId": "replacement-session", "verificationCode": "741258",
    })
    aioclient_mock.post(PAIR_CONFIRM_URL, json={"accessToken": "replacement-token"})
    aioclient_mock.get(STATUS_URL, json={"device": DEVICE})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_REAUTH, "entry_id": entry.entry_id},
        data=entry.data,
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_ACCESS_TOKEN: "", CONF_TLS_FINGERPRINT: ""},
    )
    assert result["step_id"] == "pair"
    assert entry.data[CONF_ACCESS_TOKEN] == "revoked-token"
    with patch.object(hass.config_entries, "async_reload", new_callable=AsyncMock) as reload:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"verification_code": "741258"},
        )
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_ACCESS_TOKEN] == "replacement-token"
    assert entry.data[CONF_TLS_FINGERPRINT] == "A1" * 32
    assert entry.unique_id == "device-123"
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    reload.assert_awaited_once_with(entry.entry_id)


@pytest.mark.parametrize("source", [SOURCE_REAUTH, SOURCE_RECONFIGURE])
async def test_repair_rejects_invalid_connection_input_without_network(hass, source):
    original = {
        CONF_BASE_URL: BASE_URL, CONF_ACCESS_TOKEN: "token",
        CONF_DEVICE_ID: "device-123", CONF_TLS_FINGERPRINT: "A1" * 32,
    }
    entry = MockConfigEntry(domain=DOMAIN, unique_id="device-123", data=original)
    entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": source, "entry_id": entry.entry_id},
        data=original if source == SOURCE_REAUTH else None,
    )
    submitted = {CONF_TLS_FINGERPRINT: "invalid"}
    if source == SOURCE_RECONFIGURE:
        submitted[CONF_BASE_URL] = BASE_URL
    with patch("custom_components.easycontrolx.config_flow._async_build_client",
               new_callable=AsyncMock) as build:
        result = await hass.config_entries.flow.async_configure(result["flow_id"], submitted)
        build.assert_not_awaited()
    assert result["errors"] == {CONF_TLS_FINGERPRINT: "invalid_fingerprint"}
    assert dict(entry.data) == original
