from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit, urlunsplit

from aiohttp import (
    ClientConnectorCertificateError,
    ClientConnectorSSLError,
    ClientError,
    ClientResponseError,
    ClientSession,
    ClientTimeout,
    Fingerprint,
    ServerFingerprintMismatch,
)

from .const import DEFAULT_TIMEOUT_SECONDS, TOKEN_HEADER
from .exceptions import (
    ApiError,
    CannotConnect,
    InvalidAuth,
    PairingExpired,
    PairingPending,
    TLSCertificateUntrusted,
    TLSFingerprintMismatch,
)
from .helpers import normalize_optional_string


def normalize_base_url(base_url: str) -> str:
    """Normalize a base URL for the EasyControlX host."""
    normalized = base_url.strip().rstrip("/")
    if not normalized:
        msg = "Base URL is required."
        raise ValueError(msg)
    if any(character.isspace() for character in normalized):
        msg = "EasyControlX host URL must not contain whitespace."
        raise ValueError(msg)

    if "://" not in normalized:
        normalized = f"https://{normalized}"

    try:
        parsed = urlsplit(normalized)
        _ = parsed.port
    except ValueError as err:
        msg = "EasyControlX host URL is invalid."
        raise ValueError(msg) from err

    if parsed.scheme.lower() != "https":
        msg = "EasyControlX Home Assistant connections require HTTPS."
        raise ValueError(msg)
    if not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        msg = "EasyControlX host URL must not contain credentials, a query, or a fragment."
        raise ValueError(msg)

    base_path = parsed.path.rstrip("/")
    return urlunsplit(("https", parsed.netloc, base_path, "", ""))


class EasyControlXApiClient:
    """Async client for the EasyControlX host API."""

    def __init__(
        self,
        session: ClientSession,
        base_url: str,
        access_token: str | None = None,
        tls_fingerprint: str | None = None,
    ) -> None:
        self._session = session
        self._base_url = normalize_base_url(base_url)
        self._access_token = access_token.strip() if access_token else None
        self._ssl = self._build_ssl_fingerprint(tls_fingerprint)

    @property
    def base_url(self) -> str:
        """Return the configured base URL."""
        return self._base_url

    async def async_get_device(self) -> dict[str, Any]:
        """Fetch host identity information."""
        return await self._async_request_json("GET", "/api/v1/device", auth_required=False)

    async def async_get_status(self) -> dict[str, Any]:
        """Fetch the aggregated host status."""
        return await self._async_request_json("GET", "/api/v1/status", auth_required=True)

    async def async_start_pairing(self, controller_name: str) -> dict[str, Any]:
        """Start a pairing session."""
        return await self._async_request_json(
            "POST",
            "/api/v1/pair/start",
            json_body={"controllerName": controller_name},
            auth_required=False,
        )

    async def async_confirm_pairing(
        self,
        session_id: str,
        verification_code: str,
    ) -> dict[str, Any]:
        """Confirm an existing pairing session."""
        return await self._async_request_json(
            "POST",
            "/api/v1/pair/confirm",
            json_body={
                "sessionId": session_id,
                "verificationCode": verification_code,
            },
            auth_required=False,
        )

    async def async_post_power(self, action: str, confirmed: bool) -> dict[str, Any]:
        """Invoke a power action."""
        return await self._async_request_json(
            "POST",
            "/api/v1/actions/power",
            json_body={"action": action, "confirmed": confirmed},
            auth_required=True,
        )

    async def async_post_media(self, action: str) -> dict[str, Any]:
        """Invoke a media action."""
        return await self._async_request_json(
            "POST",
            "/api/v1/actions/media",
            json_body={"action": action},
            auth_required=True,
        )

    async def async_post_audio(self, action: str, value: int | None = None) -> dict[str, Any]:
        """Invoke an audio action."""
        return await self._async_request_json(
            "POST",
            "/api/v1/actions/audio",
            json_body={"action": action, "value": value},
            auth_required=True,
        )

    async def async_post_app_launch(
        self,
        target: str,
        arguments: str | None = None,
        working_directory: str | None = None,
    ) -> dict[str, Any]:
        """Launch an application or command target."""
        return await self._async_request_json(
            "POST",
            "/api/v1/actions/apps/launch",
            json_body={
                "target": target,
                "arguments": normalize_optional_string(arguments),
                "workingDirectory": normalize_optional_string(working_directory),
            },
            auth_required=True,
        )

    async def async_get_processes(self) -> dict[str, Any]:
        """Fetch the current process inventory."""
        return await self._async_request_json(
            "GET",
            "/api/v1/processes",
            auth_required=True,
        )

    async def async_get_services(self) -> dict[str, Any]:
        """Fetch the curated Windows service inventory."""
        return await self._async_request_json(
            "GET",
            "/api/v1/services",
            auth_required=True,
        )

    async def async_post_process(
        self,
        action: str,
        *,
        process_id: int | None = None,
        process_name: str | None = None,
        allow_multiple_matches: bool = False,
    ) -> dict[str, Any]:
        """Invoke a process action."""
        return await self._async_request_json(
            "POST",
            "/api/v1/actions/process",
            json_body={
                "action": action,
                "processId": process_id,
                "processName": normalize_optional_string(process_name),
                "allowMultipleMatches": allow_multiple_matches,
            },
            auth_required=True,
        )

    async def async_post_service(self, action: str, service_name: str) -> dict[str, Any]:
        """Invoke a curated Windows service action."""
        return await self._async_request_json(
            "POST",
            "/api/v1/actions/service",
            json_body={
                "action": action,
                "serviceName": service_name,
            },
            auth_required=True,
        )

    async def async_get_files_browse(self, path: str | None = None) -> dict[str, Any]:
        """Browse the exposed host file system."""
        params: dict[str, Any] | None = None
        normalized_path = normalize_optional_string(path)
        if normalized_path is not None:
            params = {"path": normalized_path}

        return await self._async_request_json(
            "GET",
            "/api/v1/files/browse",
            params=params,
            auth_required=True,
        )

    async def async_post_files_copy(
        self,
        source_path: str,
        destination_path: str,
        *,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        """Copy a file or directory on the host."""
        return await self._async_request_json(
            "POST",
            "/api/v1/actions/files/copy",
            json_body={
                "sourcePath": source_path,
                "destinationPath": destination_path,
                "overwrite": overwrite,
            },
            auth_required=True,
        )

    async def async_get_desktop_preview(
        self,
        monitor_id: str | None = None,
        *,
        max_width: int = 1280,
        max_height: int = 720,
    ) -> bytes:
        """Fetch a desktop preview image."""
        params: dict[str, Any] = {
            "maxWidth": max_width,
            "maxHeight": max_height,
        }
        if monitor_id:
            params["monitorId"] = monitor_id

        return await self._async_request_bytes(
            "GET",
            "/api/v1/desktop/preview",
            params=params,
            auth_required=True,
        )

    async def async_get_window_preview(
        self,
        window_id: str,
        *,
        max_width: int = 960,
        max_height: int = 540,
    ) -> bytes:
        """Fetch a window preview image."""
        return await self._async_request_bytes(
            "GET",
            f"/api/v1/windows/{window_id}/preview",
            params={"maxWidth": max_width, "maxHeight": max_height},
            auth_required=True,
        )

    async def _async_request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        auth_required: bool,
    ) -> dict[str, Any]:
        """Perform a JSON request."""
        response = await self._async_request(
            method,
            path,
            params=params,
            json_body=json_body,
            auth_required=auth_required,
        )
        try:
            return await response.json()
        except (ClientError, ValueError) as err:
            raise ApiError("EasyControlX returned an invalid JSON response.") from err

    async def _async_request_bytes(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        auth_required: bool,
    ) -> bytes:
        """Perform a byte response request."""
        response = await self._async_request(
            method,
            path,
            params=params,
            auth_required=auth_required,
        )
        return await response.read()

    async def _async_request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
        auth_required: bool,
    ):
        """Perform a request and map transport/auth errors."""
        headers: dict[str, str] = {}
        if auth_required:
            if not self._access_token:
                raise InvalidAuth("Missing EasyControlX access token.")
            headers[TOKEN_HEADER] = self._access_token

        try:
            response = await self._session.request(
                method,
                f"{self._base_url}{path}",
                headers=headers,
                json=json_body,
                params=params,
                timeout=ClientTimeout(total=DEFAULT_TIMEOUT_SECONDS),
                ssl=self._ssl,
            )
        except ServerFingerprintMismatch as err:
            raise TLSFingerprintMismatch(
                "The EasyControlX host certificate changed. Compare the SHA-256 "
                "fingerprint currently shown by the host before reconnecting."
            ) from err
        except (ClientConnectorCertificateError, ClientConnectorSSLError) as err:
            raise TLSCertificateUntrusted(
                "The EasyControlX host certificate is not publicly trusted. Compare and "
                "approve its SHA-256 fingerprint before reconnecting."
            ) from err
        except (ClientError, TimeoutError) as err:
            raise CannotConnect from err

        try:
            response.raise_for_status()
        except ClientResponseError as err:
            if err.status in (401, 403):
                raise InvalidAuth from err
            if err.status == 202 and path == "/api/v1/pair/confirm":
                raise PairingPending from err
            if err.status == 410 and path == "/api/v1/pair/confirm":
                raise PairingExpired from err
            raise ApiError(f"EasyControlX request failed with status {err.status}.") from err

        return response

    @staticmethod
    def _build_ssl_fingerprint(value: str | None) -> Fingerprint | None:
        """Return aiohttp's strict SHA-256 leaf-certificate verifier."""
        normalized = normalize_tls_fingerprint(value)
        return Fingerprint(bytes.fromhex(normalized)) if normalized else None


def normalize_tls_fingerprint(value: Any) -> str | None:
    """Normalize a SHA-256 certificate fingerprint for storage and comparison."""
    if value is None:
        return None

    normalized = str(value).replace(":", "").strip().upper()
    if not normalized:
        return None
    if len(normalized) != 64 or any(
        character not in "0123456789ABCDEF" for character in normalized
    ):
        msg = "Host TLS fingerprint must contain 64 hexadecimal characters."
        raise ValueError(msg)
    return normalized
