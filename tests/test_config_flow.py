"""Contract tests for secure EasyControlX setup and repair flows."""

from __future__ import annotations

from ipaddress import ip_address
from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import (
    SOURCE_REAUTH,
    SOURCE_RECONFIGURE,
    SOURCE_USER,
    SOURCE_ZEROCONF,
)
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.easycontrolx.config_flow import EasyControlXConfigFlow
from custom_components.easycontrolx.const import (
    CONF_BASE_URL,
    CONF_CONTROLLER_NAME,
    CONF_DEVICE_ID,
    CONF_TLS_FINGERPRINT,
    DOMAIN,
)
from custom_components.easycontrolx.exceptions import CannotConnect

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
