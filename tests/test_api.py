from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest
from aiohttp import ClientConnectionError, ClientResponseError
from aiohttp.client_reqrep import RequestInfo
from multidict import CIMultiDict, CIMultiDictProxy
from yarl import URL

from custom_components.easycontrolx.api import EasyControlXApiClient, normalize_base_url
from custom_components.easycontrolx.exceptions import (
    ApiError,
    CannotConnect,
    InvalidAuth,
    PairingExpired,
    PairingPending,
)


def test_normalize_base_url_adds_scheme() -> None:
    assert normalize_base_url("192.168.1.20:5188") == "http://192.168.1.20:5188"


def test_normalize_base_url_trims_trailing_slash() -> None:
    assert normalize_base_url("http://host.local:5188/") == "http://host.local:5188"


def test_normalize_base_url_rejects_blank_value() -> None:
    with pytest.raises(ValueError):
        normalize_base_url("   ")


@pytest.mark.asyncio
async def test_status_requires_token() -> None:
    session = AsyncMock()
    client = EasyControlXApiClient(session, "http://host.local:5188")

    with pytest.raises(InvalidAuth):
        await client.async_get_status()


@pytest.mark.asyncio
async def test_get_device_returns_json_payload() -> None:
    response = Mock()
    response.raise_for_status.return_value = None
    response.json = AsyncMock(return_value={"deviceId": "abc123"})

    session = AsyncMock()
    session.request = AsyncMock(return_value=response)

    client = EasyControlXApiClient(session, "http://host.local:5188")
    result = await client.async_get_device()

    assert result == {"deviceId": "abc123"}
    session.request.assert_awaited_once()


@pytest.mark.asyncio
async def test_app_launch_posts_expected_payload() -> None:
    response = Mock()
    response.raise_for_status.return_value = None
    response.json = AsyncMock(return_value={"accepted": True})

    session = AsyncMock()
    session.request = AsyncMock(return_value=response)

    client = EasyControlXApiClient(session, "http://host.local:5188", "token")
    result = await client.async_post_app_launch(
        "notepad.exe",
        arguments=" --new-window ",
        working_directory=" C:\\Users\\Public ",
    )

    assert result == {"accepted": True}
    request = session.request.await_args
    assert request.args[0] == "POST"
    assert request.args[1] == "http://host.local:5188/api/v1/actions/apps/launch"
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

    client = EasyControlXApiClient(session, "http://host.local:5188", "token")
    result = await client.async_get_processes()

    assert result == {"totalProcessCount": 42}
    request = session.request.await_args
    assert request.args[0] == "GET"
    assert request.args[1] == "http://host.local:5188/api/v1/processes"
    assert request.kwargs["headers"] == {"X-EasyControlX-Token": "token"}


@pytest.mark.asyncio
async def test_service_list_requests_inventory_endpoint() -> None:
    response = Mock()
    response.raise_for_status.return_value = None
    response.json = AsyncMock(return_value={"totalServiceCount": 2})

    session = AsyncMock()
    session.request = AsyncMock(return_value=response)

    client = EasyControlXApiClient(session, "http://host.local:5188", "token")
    result = await client.async_get_services()

    assert result == {"totalServiceCount": 2}
    request = session.request.await_args
    assert request.args[0] == "GET"
    assert request.args[1] == "http://host.local:5188/api/v1/services"
    assert request.kwargs["headers"] == {"X-EasyControlX-Token": "token"}


@pytest.mark.asyncio
async def test_service_action_posts_expected_payload() -> None:
    response = Mock()
    response.raise_for_status.return_value = None
    response.json = AsyncMock(return_value={"accepted": True})

    session = AsyncMock()
    session.request = AsyncMock(return_value=response)

    client = EasyControlXApiClient(session, "http://host.local:5188", "token")
    result = await client.async_post_service("Restart", "EasyControlX Windows Agent")

    assert result == {"accepted": True}
    request = session.request.await_args
    assert request.args[0] == "POST"
    assert request.args[1] == "http://host.local:5188/api/v1/actions/service"
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

    client = EasyControlXApiClient(session, "http://host.local:5188", "token")
    result = await client.async_get_files_browse()

    assert result == {"entries": []}
    request = session.request.await_args
    assert request.args[0] == "GET"
    assert request.args[1] == "http://host.local:5188/api/v1/files/browse"
    assert request.kwargs["params"] is None


@pytest.mark.asyncio
async def test_file_copy_posts_expected_payload() -> None:
    response = Mock()
    response.raise_for_status.return_value = None
    response.json = AsyncMock(return_value={"accepted": True})

    session = AsyncMock()
    session.request = AsyncMock(return_value=response)

    client = EasyControlXApiClient(session, "http://host.local:5188", "token")
    result = await client.async_post_files_copy(
        "C:\\Source.txt",
        "C:\\Dest.txt",
        overwrite=True,
    )

    assert result == {"accepted": True}
    request = session.request.await_args
    assert request.args[0] == "POST"
    assert request.args[1] == "http://host.local:5188/api/v1/actions/files/copy"
    assert request.kwargs["json"] == {
        "sourcePath": "C:\\Source.txt",
        "destinationPath": "C:\\Dest.txt",
        "overwrite": True,
    }


@pytest.mark.asyncio
async def test_transport_error_maps_to_cannot_connect() -> None:
    session = AsyncMock()
    session.request = AsyncMock(side_effect=ClientConnectionError())
    client = EasyControlXApiClient(session, "http://host.local:5188", "token")

    with pytest.raises(CannotConnect):
        await client.async_get_status()


@pytest.mark.asyncio
async def test_unauthorized_maps_to_invalid_auth() -> None:
    response = Mock()
    response.raise_for_status.side_effect = _client_response_error(401)

    session = AsyncMock()
    session.request = AsyncMock(return_value=response)
    client = EasyControlXApiClient(session, "http://host.local:5188", "token")

    with pytest.raises(InvalidAuth):
        await client.async_get_status()


@pytest.mark.asyncio
async def test_pair_confirm_pending_maps_to_pairing_pending() -> None:
    response = Mock()
    response.raise_for_status.side_effect = _client_response_error(202)

    session = AsyncMock()
    session.request = AsyncMock(return_value=response)
    client = EasyControlXApiClient(session, "http://host.local:5188")

    with pytest.raises(PairingPending):
        await client.async_confirm_pairing("session", "123456")


@pytest.mark.asyncio
async def test_pair_confirm_expired_maps_to_pairing_expired() -> None:
    response = Mock()
    response.raise_for_status.side_effect = _client_response_error(410)

    session = AsyncMock()
    session.request = AsyncMock(return_value=response)
    client = EasyControlXApiClient(session, "http://host.local:5188")

    with pytest.raises(PairingExpired):
        await client.async_confirm_pairing("session", "123456")


@pytest.mark.asyncio
async def test_unexpected_response_maps_to_api_error() -> None:
    response = Mock()
    response.raise_for_status.side_effect = _client_response_error(500)

    session = AsyncMock()
    session.request = AsyncMock(return_value=response)
    client = EasyControlXApiClient(session, "http://host.local:5188", "token")

    with pytest.raises(ApiError):
        await client.async_get_status()


def _client_response_error(status: int) -> ClientResponseError:
    return ClientResponseError(
        request_info=RequestInfo(
            url=URL("http://host.local"),
            method="GET",
            headers=CIMultiDictProxy(CIMultiDict()),
            real_url=URL("http://host.local"),
        ),
        history=(),
        status=status,
        message="boom",
        headers=CIMultiDictProxy(CIMultiDict()),
    )
