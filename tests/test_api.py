from __future__ import annotations

import ssl
from unittest.mock import AsyncMock, Mock

import pytest
from aiohttp import (
    ClientConnectionError,
    ClientConnectorCertificateError,
    ClientResponseError,
    Fingerprint,
    ServerFingerprintMismatch,
)
from aiohttp.client_reqrep import RequestInfo
from multidict import CIMultiDict, CIMultiDictProxy
from yarl import URL

from custom_components.easycontrolx.api import (
    EasyControlXApiClient,
    normalize_base_url,
    normalize_tls_fingerprint,
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


def test_normalize_base_url_adds_scheme() -> None:
    assert normalize_base_url("192.168.1.20:5188") == "https://192.168.1.20:5188"


def test_normalize_base_url_trims_trailing_slash() -> None:
    assert normalize_base_url("https://host.local:5188/") == "https://host.local:5188"


def test_normalize_base_url_rejects_plain_http() -> None:
    with pytest.raises(ValueError, match="require HTTPS"):
        normalize_base_url("http://host.local:5188")


@pytest.mark.parametrize(
    "value",
    [
        "https://user:secret@host.local:5188",
        "https://host.local:invalid",
        "ftp://host.local:5188",
    ],
)
def test_normalize_base_url_rejects_non_host_urls(value: str) -> None:
    with pytest.raises(ValueError):
        normalize_base_url(value)


def test_normalize_base_url_preserves_reverse_proxy_path() -> None:
    assert normalize_base_url("https://host.local/easycontrolx/") == (
        "https://host.local/easycontrolx"
    )


def test_normalize_base_url_accepts_case_insensitive_https_scheme() -> None:
    assert normalize_base_url("HTTPS://host.local:5188/") == "https://host.local:5188"


def test_normalize_base_url_rejects_blank_value() -> None:
    with pytest.raises(ValueError):
        normalize_base_url("   ")


def test_normalize_tls_fingerprint_accepts_colon_separated_sha256() -> None:
    fingerprint = ":".join(["a1"] * 32)

    assert normalize_tls_fingerprint(fingerprint) == "A1" * 32


def test_normalize_tls_fingerprint_rejects_malformed_value() -> None:
    with pytest.raises(ValueError, match="64 hexadecimal"):
        normalize_tls_fingerprint("not-a-fingerprint")


@pytest.mark.asyncio
async def test_status_requires_token() -> None:
    session = AsyncMock()
    client = EasyControlXApiClient(session, "https://host.local:5188")

    with pytest.raises(InvalidAuth):
        await client.async_get_status()


@pytest.mark.asyncio
async def test_get_device_returns_json_payload() -> None:
    response = Mock()
    response.raise_for_status.return_value = None
    response.json = AsyncMock(return_value={"deviceId": "abc123"})

    session = AsyncMock()
    session.request = AsyncMock(return_value=response)

    client = EasyControlXApiClient(session, "https://host.local:5188")
    result = await client.async_get_device()

    assert result == {"deviceId": "abc123"}
    session.request.assert_awaited_once()


@pytest.mark.asyncio
async def test_requests_preserve_reverse_proxy_base_path() -> None:
    response = Mock()
    response.raise_for_status.return_value = None
    response.json = AsyncMock(return_value={"deviceId": "abc123"})
    session = AsyncMock()
    session.request = AsyncMock(return_value=response)
    client = EasyControlXApiClient(session, "https://host.local/easycontrolx")

    await client.async_get_device()

    assert session.request.await_args.args[1] == (
        "https://host.local/easycontrolx/api/v1/device"
    )


@pytest.mark.asyncio
async def test_request_uses_strict_certificate_fingerprint() -> None:
    response = Mock()
    response.raise_for_status.return_value = None
    response.json = AsyncMock(return_value={"deviceId": "abc123"})
    session = AsyncMock()
    session.request = AsyncMock(return_value=response)
    client = EasyControlXApiClient(
        session,
        "https://host.local:5188",
        tls_fingerprint="A1" * 32,
    )

    await client.async_get_device()

    assert isinstance(session.request.await_args.kwargs["ssl"], Fingerprint)


@pytest.mark.asyncio
async def test_app_launch_posts_expected_payload() -> None:
    response = Mock()
    response.raise_for_status.return_value = None
    response.json = AsyncMock(return_value={"accepted": True})

    session = AsyncMock()
    session.request = AsyncMock(return_value=response)

    client = EasyControlXApiClient(session, "https://host.local:5188", "token")
    result = await client.async_post_app_launch(
        "notepad.exe",
        arguments=" --new-window ",
        working_directory=" C:\\Users\\Public ",
    )

    assert result == {"accepted": True}
    request = session.request.await_args
    assert request.args[0] == "POST"
    assert request.args[1] == "https://host.local:5188/api/v1/actions/apps/launch"
    assert request.kwargs["headers"] == {"X-EasyControlX-Token": "token"}
    assert request.kwargs["json"] == {
        "target": "notepad.exe",
        "arguments": "--new-window",
        "workingDirectory": "C:\\Users\\Public",
    }


@pytest.mark.asyncio
async def test_process_list_requests_inventory_endpoint() -> None:
    response = Mock()
    response.raise_for_status.return_value = None
    response.json = AsyncMock(return_value={"totalProcessCount": 42})

    session = AsyncMock()
    session.request = AsyncMock(return_value=response)

    client = EasyControlXApiClient(session, "https://host.local:5188", "token")
    result = await client.async_get_processes()

    assert result == {"totalProcessCount": 42}
    request = session.request.await_args
    assert request.args[0] == "GET"
    assert request.args[1] == "https://host.local:5188/api/v1/processes"
    assert request.kwargs["headers"] == {"X-EasyControlX-Token": "token"}


@pytest.mark.asyncio
async def test_service_list_requests_inventory_endpoint() -> None:
    response = Mock()
    response.raise_for_status.return_value = None
    response.json = AsyncMock(return_value={"totalServiceCount": 2})

    session = AsyncMock()
    session.request = AsyncMock(return_value=response)

    client = EasyControlXApiClient(session, "https://host.local:5188", "token")
    result = await client.async_get_services()

    assert result == {"totalServiceCount": 2}
    request = session.request.await_args
    assert request.args[0] == "GET"
    assert request.args[1] == "https://host.local:5188/api/v1/services"
    assert request.kwargs["headers"] == {"X-EasyControlX-Token": "token"}


@pytest.mark.asyncio
async def test_service_action_posts_expected_payload() -> None:
    response = Mock()
    response.raise_for_status.return_value = None
    response.json = AsyncMock(return_value={"accepted": True})

    session = AsyncMock()
    session.request = AsyncMock(return_value=response)

    client = EasyControlXApiClient(session, "https://host.local:5188", "token")
    result = await client.async_post_service("Restart", "EasyControlX Windows Agent")

    assert result == {"accepted": True}
    request = session.request.await_args
    assert request.args[0] == "POST"
    assert request.args[1] == "https://host.local:5188/api/v1/actions/service"
    assert request.kwargs["json"] == {
        "action": "Restart",
        "serviceName": "EasyControlX Windows Agent",
    }


@pytest.mark.asyncio
async def test_file_browse_omits_path_when_not_provided() -> None:
    response = Mock()
    response.raise_for_status.return_value = None
    response.json = AsyncMock(return_value={"entries": []})

    session = AsyncMock()
    session.request = AsyncMock(return_value=response)

    client = EasyControlXApiClient(session, "https://host.local:5188", "token")
    result = await client.async_get_files_browse()

    assert result == {"entries": []}
    request = session.request.await_args
    assert request.args[0] == "GET"
    assert request.args[1] == "https://host.local:5188/api/v1/files/browse"
    assert request.kwargs["params"] is None


@pytest.mark.asyncio
async def test_file_copy_posts_expected_payload() -> None:
    response = Mock()
    response.raise_for_status.return_value = None
    response.json = AsyncMock(return_value={"accepted": True})

    session = AsyncMock()
    session.request = AsyncMock(return_value=response)

    client = EasyControlXApiClient(session, "https://host.local:5188", "token")
    result = await client.async_post_files_copy(
        "C:\\Source.txt",
        "C:\\Dest.txt",
        overwrite=True,
    )

    assert result == {"accepted": True}
    request = session.request.await_args
    assert request.args[0] == "POST"
    assert request.args[1] == "https://host.local:5188/api/v1/actions/files/copy"
    assert request.kwargs["json"] == {
        "sourcePath": "C:\\Source.txt",
        "destinationPath": "C:\\Dest.txt",
        "overwrite": True,
    }


@pytest.mark.asyncio
async def test_transport_error_maps_to_cannot_connect() -> None:
    session = AsyncMock()
    session.request = AsyncMock(side_effect=ClientConnectionError())
    client = EasyControlXApiClient(session, "https://host.local:5188", "token")

    with pytest.raises(CannotConnect):
        await client.async_get_status()


@pytest.mark.asyncio
async def test_timeout_maps_to_cannot_connect() -> None:
    session = AsyncMock()
    session.request = AsyncMock(side_effect=TimeoutError())
    client = EasyControlXApiClient(session, "https://host.local:5188", "token")

    with pytest.raises(CannotConnect):
        await client.async_get_status()


@pytest.mark.asyncio
async def test_fingerprint_mismatch_maps_to_repair_error() -> None:
    session = AsyncMock()
    session.request = AsyncMock(
        side_effect=ServerFingerprintMismatch(
            b"\xA1" * 32,
            b"\xB2" * 32,
            "host.local",
            5188,
        )
    )
    client = EasyControlXApiClient(
        session,
        "https://host.local:5188",
        "token",
        "A1" * 32,
    )

    with pytest.raises(TLSFingerprintMismatch, match="certificate changed"):
        await client.async_get_status()


@pytest.mark.asyncio
async def test_untrusted_certificate_maps_to_explicit_approval_error() -> None:
    session = AsyncMock()
    session.request = AsyncMock(
        side_effect=ClientConnectorCertificateError(
            None,
            ssl.SSLCertVerificationError("self-signed certificate"),
        )
    )
    client = EasyControlXApiClient(session, "https://host.local:5188", "token")

    with pytest.raises(TLSCertificateUntrusted, match="fingerprint"):
        await client.async_get_status()


@pytest.mark.asyncio
async def test_unauthorized_maps_to_invalid_auth() -> None:
    response = Mock()
    response.raise_for_status.side_effect = _client_response_error(401)

    session = AsyncMock()
    session.request = AsyncMock(return_value=response)
    client = EasyControlXApiClient(session, "https://host.local:5188", "token")

    with pytest.raises(InvalidAuth):
        await client.async_get_status()


@pytest.mark.asyncio
async def test_forbidden_maps_to_invalid_auth() -> None:
    response = Mock()
    response.raise_for_status.side_effect = _client_response_error(403)
    session = AsyncMock()
    session.request = AsyncMock(return_value=response)
    client = EasyControlXApiClient(session, "https://host.local:5188", "token")

    with pytest.raises(InvalidAuth):
        await client.async_get_status()


@pytest.mark.asyncio
async def test_invalid_json_maps_to_api_error() -> None:
    response = Mock()
    response.raise_for_status.return_value = None
    response.json = AsyncMock(side_effect=ValueError("invalid JSON"))
    session = AsyncMock()
    session.request = AsyncMock(return_value=response)
    client = EasyControlXApiClient(session, "https://host.local:5188", "token")

    with pytest.raises(ApiError, match="invalid JSON"):
        await client.async_get_status()


@pytest.mark.asyncio
async def test_pair_confirm_pending_maps_to_pairing_pending() -> None:
    response = Mock()
    response.raise_for_status.side_effect = _client_response_error(202)

    session = AsyncMock()
    session.request = AsyncMock(return_value=response)
    client = EasyControlXApiClient(session, "https://host.local:5188")

    with pytest.raises(PairingPending):
        await client.async_confirm_pairing("session", "123456")


@pytest.mark.asyncio
async def test_pair_confirm_expired_maps_to_pairing_expired() -> None:
    response = Mock()
    response.raise_for_status.side_effect = _client_response_error(410)

    session = AsyncMock()
    session.request = AsyncMock(return_value=response)
    client = EasyControlXApiClient(session, "https://host.local:5188")

    with pytest.raises(PairingExpired):
        await client.async_confirm_pairing("session", "123456")


@pytest.mark.asyncio
async def test_unexpected_response_maps_to_api_error() -> None:
    response = Mock()
    response.raise_for_status.side_effect = _client_response_error(500)

    session = AsyncMock()
    session.request = AsyncMock(return_value=response)
    client = EasyControlXApiClient(session, "https://host.local:5188", "token")

    with pytest.raises(ApiError):
        await client.async_get_status()


def _client_response_error(status: int) -> ClientResponseError:
    return ClientResponseError(
        request_info=RequestInfo(
            url=URL("https://host.local"),
            method="GET",
            headers=CIMultiDictProxy(CIMultiDict()),
            real_url=URL("https://host.local"),
        ),
        history=(),
        status=status,
        message="boom",
        headers=CIMultiDictProxy(CIMultiDict()),
    )
