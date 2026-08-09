from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .api import EasyControlXApiClient, normalize_base_url, normalize_tls_fingerprint
from .const import (
    CONF_BASE_URL,
    CONF_CONTROLLER_NAME,
    CONF_DEVICE_ID,
    CONF_PREFERRED_MONITOR_ID,
    CONF_SCAN_INTERVAL,
    CONF_TLS_FINGERPRINT,
    DEFAULT_CONTROLLER_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    OPTIONAL_OPTIONS,
    SCAN_INTERVAL_MAX,
    SCAN_INTERVAL_MIN,
)
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


@dataclass(slots=True)
class PendingPairing:
    """State for a config-flow pairing session."""

    base_url: str
    title: str
    device_id: str
    controller_name: str
    session_id: str
    verification_code: str
    tls_fingerprint: str | None


async def _async_build_client(
    hass: HomeAssistant,
    base_url: str,
    access_token: str | None = None,
    tls_fingerprint: str | None = None,
) -> EasyControlXApiClient:
    """Build an API client."""
    return EasyControlXApiClient(
        async_get_clientsession(hass),
        base_url,
        access_token,
        tls_fingerprint,
    )


class EasyControlXConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for EasyControlX."""

    VERSION = 1
    MINOR_VERSION = 1

    _discovered_base_url: str | None = None
    _discovered_device_id: str | None = None
    _discovered_tls_fingerprint: str | None = None
    _discovered_title: str | None = None
    _pending_pairing: PendingPairing | None = None
    _reauth_entry: config_entries.ConfigEntry | None = None
    _issued_access_token: str | None = None

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow."""
        return EasyControlXOptionsFlow(config_entry)

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle manual setup."""
        errors: dict[str, str] = {}

        if user_input is not None:
            base_url, tls_fingerprint, errors = self._validate_connection_input(user_input)
            if not errors:
                try:
                    return await self._async_handle_user_or_reconfigure(
                        user_input,
                        base_url=base_url,
                        tls_fingerprint=tls_fingerprint,
                    )
                except TLSFingerprintMismatch:
                    errors[CONF_TLS_FINGERPRINT] = "fingerprint_mismatch"
                except TLSCertificateUntrusted:
                    errors[CONF_TLS_FINGERPRINT] = "fingerprint_required"
                except CannotConnect:
                    errors["base"] = "cannot_connect"
                except InvalidAuth:
                    errors["base"] = "invalid_auth"
                except ApiError:
                    errors["base"] = "unknown"

        defaults = {
            CONF_BASE_URL: self._discovered_base_url or "",
            CONF_CONTROLLER_NAME: DEFAULT_CONTROLLER_NAME,
            CONF_ACCESS_TOKEN: "",
            CONF_TLS_FINGERPRINT: "",
        }

        schema = self.add_suggested_values_to_schema(
            vol.Schema(
                {
                    vol.Required(CONF_BASE_URL): str,
                    vol.Optional(CONF_ACCESS_TOKEN): str,
                    vol.Optional(CONF_TLS_FINGERPRINT): str,
                    vol.Optional(CONF_CONTROLLER_NAME, default=DEFAULT_CONTROLLER_NAME): str,
                }
            ),
            defaults,
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_pair(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle host-approved pairing."""
        if self._pending_pairing is None:
            return self.async_abort(reason="pairing_not_started")

        if user_input is not None:
            entered_code = str(user_input.get("verification_code", "")).strip()
            if entered_code != self._pending_pairing.verification_code:
                return self._show_pair(error="code_mismatch")
            return await self._async_confirm_pending_pairing()

        return self._show_pair()

    async def async_step_pair_transport_repair(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Repair certificate trust without discarding an approved pairing session."""
        if self._pending_pairing is None:
            return self.async_abort(reason="pairing_not_started")
        if user_input is not None:
            try:
                raw_fingerprint = user_input.get(
                    CONF_TLS_FINGERPRINT,
                    self._pending_pairing.tls_fingerprint,
                )
                if (
                    not str(raw_fingerprint or "").strip()
                    and self._pending_pairing.tls_fingerprint
                ):
                    raw_fingerprint = self._pending_pairing.tls_fingerprint
                self._pending_pairing.tls_fingerprint = normalize_tls_fingerprint(
                    raw_fingerprint
                )
            except ValueError:
                return self._show_pair_transport_repair(
                    fingerprint_error="invalid_fingerprint"
                )
            return await self._async_confirm_pending_pairing()
        return self._show_pair_transport_repair()

    async def async_step_pairing_retry(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Retry validation with a token already issued by the host."""
        if not self._issued_access_token or self._pending_pairing is None:
            return self.async_abort(reason="pairing_failed")
        if user_input is not None:
            try:
                raw_fingerprint = user_input.get(
                    CONF_TLS_FINGERPRINT,
                    self._pending_pairing.tls_fingerprint,
                )
                if (
                    not str(raw_fingerprint or "").strip()
                    and self._pending_pairing.tls_fingerprint
                ):
                    raw_fingerprint = self._pending_pairing.tls_fingerprint
                self._pending_pairing.tls_fingerprint = normalize_tls_fingerprint(
                    raw_fingerprint
                )
            except ValueError:
                return self._show_pairing_retry(fingerprint_error="invalid_fingerprint")
            return await self._async_finish_paired_setup(self._issued_access_token)
        return self._show_pairing_retry()

    async def async_step_zeroconf(self, discovery_info: ZeroconfServiceInfo) -> FlowResult:
        """Handle zeroconf discovery."""
        base_url = self._async_base_url_from_discovery(discovery_info)
        if base_url is None:
            return self.async_abort(reason="unsupported_device")

        device_id = discovery_info.properties.get("deviceId") or discovery_info.properties.get(
            "deviceid"
        )
        title = discovery_info.name.removesuffix("._easycontrolx._tcp.local.")

        if device_id:
            await self.async_set_unique_id(device_id)
            self._abort_if_unique_id_configured()

        self._discovered_base_url = base_url
        self._discovered_device_id = device_id
        self._discovered_tls_fingerprint = self._discovery_fingerprint(
            discovery_info.properties
        )
        self._discovered_title = title
        return await self.async_step_user()

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> FlowResult:
        """Start a reauth flow."""
        self._reauth_entry = self._get_reauth_entry()
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Confirm reauthentication."""
        if self._reauth_entry is None:
            self._reauth_entry = self._get_reauth_entry()

        errors: dict[str, str] = {}
        if user_input is not None:
            base_url = self._reauth_entry.data[CONF_BASE_URL]
            access_token = normalize_optional_string(user_input.get(CONF_ACCESS_TOKEN))
            raw_fingerprint = user_input.get(
                CONF_TLS_FINGERPRINT,
                self._reauth_entry.data.get(CONF_TLS_FINGERPRINT, ""),
            )
            stored_fingerprint = self._reauth_entry.data.get(CONF_TLS_FINGERPRINT, "")
            if not str(raw_fingerprint or "").strip() and stored_fingerprint:
                raw_fingerprint = stored_fingerprint
            try:
                tls_fingerprint = normalize_tls_fingerprint(raw_fingerprint)
            except ValueError:
                errors[CONF_TLS_FINGERPRINT] = "invalid_fingerprint"

            try:
                if errors:
                    raise ValueError
                client = await _async_build_client(
                    self.hass,
                    base_url,
                    access_token,
                    tls_fingerprint,
                )
                device = await client.async_get_device()
                await self.async_set_unique_id(device["deviceId"])
                self._abort_if_unique_id_mismatch()
                if access_token:
                    await client.async_get_status()
                else:
                    controller_name = DEFAULT_CONTROLLER_NAME
                    pairing = await client.async_start_pairing(controller_name)
            except ValueError:
                pass
            except TLSFingerprintMismatch:
                errors[CONF_TLS_FINGERPRINT] = "fingerprint_mismatch"
            except TLSCertificateUntrusted:
                errors[CONF_TLS_FINGERPRINT] = "fingerprint_required"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except ApiError:
                errors["base"] = "unknown"
            else:
                if access_token:
                    updates = {
                        CONF_ACCESS_TOKEN: access_token,
                        CONF_TLS_FINGERPRINT: tls_fingerprint or "",
                    }
                    return self.async_update_reload_and_abort(
                        self._get_reauth_entry(),
                        data_updates=updates,
                    )

                self._pending_pairing = PendingPairing(
                    base_url=base_url,
                    title=device["name"],
                    device_id=device["deviceId"],
                    controller_name=DEFAULT_CONTROLLER_NAME,
                    session_id=pairing["sessionId"],
                    verification_code=pairing["verificationCode"],
                    tls_fingerprint=tls_fingerprint,
                )
                return await self.async_step_pair()

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_ACCESS_TOKEN, default=""): str,
                    vol.Optional(
                        CONF_TLS_FINGERPRINT,
                        default=self._reauth_entry.data.get(CONF_TLS_FINGERPRINT, ""),
                    ): str,
                }
            ),
            errors=errors,
        )

    async def async_step_reconfigure(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Allow the user to reconfigure connection settings."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            base_url, tls_fingerprint, errors = self._validate_connection_input(
                user_input,
                default_fingerprint=entry.data.get(CONF_TLS_FINGERPRINT),
                require_discovered_fingerprint=False,
            )
            access_token = entry.data[CONF_ACCESS_TOKEN]
            try:
                if errors:
                    raise ValueError
                client = await _async_build_client(
                    self.hass,
                    base_url,
                    access_token,
                    tls_fingerprint,
                )
                device = await client.async_get_device()
                await self.async_set_unique_id(device["deviceId"])
                self._abort_if_unique_id_mismatch()
                await client.async_get_status()
            except ValueError:
                pass
            except TLSFingerprintMismatch:
                errors[CONF_TLS_FINGERPRINT] = "fingerprint_mismatch"
            except TLSCertificateUntrusted:
                errors[CONF_TLS_FINGERPRINT] = "fingerprint_required"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except ApiError:
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_BASE_URL: base_url,
                        CONF_TLS_FINGERPRINT: tls_fingerprint or "",
                    },
                )

        schema = self.add_suggested_values_to_schema(
            vol.Schema(
                {
                    vol.Required(CONF_BASE_URL): str,
                    vol.Optional(CONF_TLS_FINGERPRINT): str,
                }
            ),
            {
                CONF_BASE_URL: entry.data[CONF_BASE_URL],
                CONF_TLS_FINGERPRINT: entry.data.get(CONF_TLS_FINGERPRINT, ""),
            },
        )
        return self.async_show_form(step_id="reconfigure", data_schema=schema, errors=errors)

    async def _async_handle_user_or_reconfigure(
        self,
        user_input: dict[str, Any],
        *,
        base_url: str,
        tls_fingerprint: str | None,
    ) -> FlowResult:
        """Handle user-provided connection information."""
        access_token = normalize_optional_string(user_input.get(CONF_ACCESS_TOKEN))
        controller_name = (
            normalize_optional_string(user_input.get(CONF_CONTROLLER_NAME))
            or DEFAULT_CONTROLLER_NAME
        )

        if access_token:
            client = await _async_build_client(
                self.hass,
                base_url,
                access_token,
                tls_fingerprint,
            )
            device = await client.async_get_device()
            if (
                self._discovered_device_id
                and device["deviceId"] != self._discovered_device_id
            ):
                return self.async_abort(reason="unique_id_mismatch")
            await client.async_get_status()
            return await self._async_finish_setup(
                title=device["name"],
                device_id=device["deviceId"],
                base_url=base_url,
                access_token=access_token,
                tls_fingerprint=tls_fingerprint,
            )

        client = await _async_build_client(
            self.hass,
            base_url,
            tls_fingerprint=tls_fingerprint,
        )
        device = await client.async_get_device()
        if self._discovered_device_id and device["deviceId"] != self._discovered_device_id:
            return self.async_abort(reason="unique_id_mismatch")
        pairing = await client.async_start_pairing(controller_name)
        self._pending_pairing = PendingPairing(
            base_url=base_url,
            title=device["name"],
            device_id=device["deviceId"],
            controller_name=controller_name,
            session_id=pairing["sessionId"],
            verification_code=pairing["verificationCode"],
            tls_fingerprint=tls_fingerprint,
        )
        return await self.async_step_pair()

    async def _async_finish_setup(
        self,
        *,
        title: str,
        device_id: str,
        base_url: str,
        access_token: str,
        tls_fingerprint: str | None,
    ) -> FlowResult:
        """Finish entry creation or update."""
        data = {
            CONF_BASE_URL: base_url,
            CONF_ACCESS_TOKEN: access_token,
            CONF_DEVICE_ID: device_id,
            CONF_TLS_FINGERPRINT: tls_fingerprint or "",
        }

        await self.async_set_unique_id(device_id)
        if self.source == config_entries.SOURCE_REAUTH:
            self._abort_if_unique_id_mismatch()
            return self.async_update_reload_and_abort(
                self._get_reauth_entry(),
                data_updates=data,
            )

        if self.source == config_entries.SOURCE_RECONFIGURE:
            self._abort_if_unique_id_mismatch()
            return self.async_update_reload_and_abort(
                self._get_reconfigure_entry(),
                data_updates=data,
            )

        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=title,
            data=data,
            options=dict(OPTIONAL_OPTIONS),
        )

    @staticmethod
    def _async_base_url_from_discovery(discovery_info: ZeroconfServiceInfo) -> str | None:
        """Build a base URL from zeroconf data."""
        properties = discovery_info.properties
        advertised = properties.get("baseUrl") or properties.get("baseurl")
        if isinstance(advertised, str) and advertised.lower().startswith("https://"):
            try:
                return normalize_base_url(advertised)
            except ValueError:
                return None

        if EasyControlXConfigFlow._discovery_fingerprint(properties) is None:
            return None

        host = discovery_info.hostname.rstrip(".")
        if not host or not discovery_info.port:
            return None
        if ":" in host and not host.startswith("["):
            host = f"[{host.replace('%', '%25')}]"
        return normalize_base_url(f"https://{host}:{discovery_info.port}")

    @staticmethod
    def _discovery_fingerprint(properties: dict[str, Any]) -> str | None:
        """Read a fingerprint hint without treating discovery as approval."""
        try:
            return normalize_tls_fingerprint(
                properties.get("tlsFingerprint") or properties.get("tlsfingerprint")
            )
        except ValueError:
            return None

    def _validate_connection_input(
        self,
        user_input: dict[str, Any],
        *,
        default_fingerprint: Any = None,
        require_discovered_fingerprint: bool = True,
    ) -> tuple[str, str | None, dict[str, str]]:
        """Validate a secure endpoint and an explicitly approved certificate pin."""
        errors: dict[str, str] = {}
        raw_url = str(user_input.get(CONF_BASE_URL, "")).strip()
        try:
            base_url = normalize_base_url(raw_url)
        except ValueError:
            base_url = raw_url.rstrip("/")
            errors[CONF_BASE_URL] = (
                "https_required" if raw_url.lower().startswith("http://") else "invalid_url"
            )

        raw_fingerprint = user_input.get(CONF_TLS_FINGERPRINT, default_fingerprint)
        if not str(raw_fingerprint or "").strip() and default_fingerprint:
            raw_fingerprint = default_fingerprint
        try:
            tls_fingerprint = normalize_tls_fingerprint(raw_fingerprint)
        except ValueError:
            tls_fingerprint = None
            errors[CONF_TLS_FINGERPRINT] = "invalid_fingerprint"

        if (
            require_discovered_fingerprint
            and self._discovered_tls_fingerprint
            and base_url == self._discovered_base_url
            and not tls_fingerprint
        ):
            errors[CONF_TLS_FINGERPRINT] = "fingerprint_required"

        return base_url, tls_fingerprint, errors

    def _pairing_schema(self) -> vol.Schema:
        """Require an explicit code comparison before polling for approval."""
        return vol.Schema({vol.Required("verification_code"): str})

    def _pairing_placeholders(self) -> dict[str, str]:
        pending = self._pending_pairing
        if pending is None:
            return {}
        return {
            "host_name": pending.title,
            "controller_name": pending.controller_name,
            "verification_code": pending.verification_code,
        }

    async def _async_confirm_pending_pairing(self) -> FlowResult:
        """Confirm a code already compared by the user and retain repair state."""
        pending = self._pending_pairing
        if pending is None:
            return self.async_abort(reason="pairing_not_started")

        client = await _async_build_client(
            self.hass,
            pending.base_url,
            tls_fingerprint=pending.tls_fingerprint,
        )
        try:
            result = await client.async_confirm_pairing(
                pending.session_id,
                pending.verification_code,
            )
        except PairingPending:
            return self._show_pair(error="pairing_pending")
        except PairingExpired:
            return self._show_pair(error="pairing_expired")
        except TLSFingerprintMismatch:
            return self._show_pair_transport_repair(
                fingerprint_error="fingerprint_mismatch"
            )
        except TLSCertificateUntrusted:
            return self._show_pair_transport_repair(
                fingerprint_error="fingerprint_required"
            )
        except CannotConnect:
            return self._show_pair(error="cannot_connect")
        except (InvalidAuth, ApiError):
            return self._show_pair(error="pairing_failed")

        access_token = normalize_optional_string(result.get("accessToken"))
        if access_token:
            return await self._async_finish_paired_setup(access_token)
        return self._show_pair(error="pairing_pending")

    def _show_pair(self, error: str | None = None) -> FlowResult:
        """Show the pairing-code confirmation form."""
        return self.async_show_form(
            step_id="pair",
            data_schema=self._pairing_schema(),
            errors={"base": error} if error else {},
            description_placeholders=self._pairing_placeholders(),
        )

    async def _async_finish_paired_setup(self, access_token: str) -> FlowResult:
        """Validate the issued token before persisting the paired entry."""
        pending = self._pending_pairing
        if pending is None:
            return self.async_abort(reason="pairing_not_started")

        self._issued_access_token = access_token
        client = await _async_build_client(
            self.hass,
            pending.base_url,
            access_token,
            pending.tls_fingerprint,
        )
        try:
            device = await client.async_get_device()
            if device["deviceId"] != pending.device_id:
                return self.async_abort(reason="unique_id_mismatch")
            await client.async_get_status()
        except TLSFingerprintMismatch:
            return self._show_pairing_retry(fingerprint_error="fingerprint_mismatch")
        except TLSCertificateUntrusted:
            return self._show_pairing_retry(fingerprint_error="fingerprint_required")
        except (CannotConnect, ApiError):
            return self._show_pairing_retry(error="cannot_connect")
        except InvalidAuth:
            self._issued_access_token = None
            return self.async_abort(reason="pairing_failed")

        self._issued_access_token = None
        return await self._async_finish_setup(
            title=device["name"],
            device_id=device["deviceId"],
            base_url=pending.base_url,
            access_token=access_token,
            tls_fingerprint=pending.tls_fingerprint,
        )

    def _show_pairing_retry(
        self,
        error: str | None = None,
        fingerprint_error: str | None = None,
    ) -> FlowResult:
        fingerprint = (
            self._pending_pairing.tls_fingerprint if self._pending_pairing else ""
        ) or ""
        return self.async_show_form(
            step_id="pairing_retry",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_TLS_FINGERPRINT,
                        default=fingerprint,
                    ): str,
                }
            ),
            errors=(
                {CONF_TLS_FINGERPRINT: fingerprint_error}
                if fingerprint_error
                else {"base": error} if error else {}
            ),
        )

    def _show_pair_transport_repair(
        self,
        fingerprint_error: str | None = None,
    ) -> FlowResult:
        """Show certificate repair while preserving the pending pairing session."""
        fingerprint = (
            self._pending_pairing.tls_fingerprint if self._pending_pairing else ""
        ) or ""
        return self.async_show_form(
            step_id="pair_transport_repair",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_TLS_FINGERPRINT,
                        default=fingerprint,
                    ): str,
                }
            ),
            errors=(
                {CONF_TLS_FINGERPRINT: fingerprint_error}
                if fingerprint_error
                else {}
            ),
        )


class EasyControlXOptionsFlow(config_entries.OptionsFlow):
    """EasyControlX options flow."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage optional runtime settings."""
        if user_input is not None:
            preferred_monitor_id = normalize_optional_string(
                user_input.get(CONF_PREFERRED_MONITOR_ID)
            ) or ""
            return self.async_create_entry(
                title="",
                data={
                    CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL]),
                    CONF_PREFERRED_MONITOR_ID: preferred_monitor_id,
                },
            )

        schema = self.add_suggested_values_to_schema(
            vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=self._config_entry.options.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=SCAN_INTERVAL_MIN, max=SCAN_INTERVAL_MAX),
                    ),
                    vol.Optional(CONF_PREFERRED_MONITOR_ID): str,
                }
            ),
            {
                CONF_SCAN_INTERVAL: self._config_entry.options.get(
                    CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                ),
                CONF_PREFERRED_MONITOR_ID: self._config_entry.options.get(
                    CONF_PREFERRED_MONITOR_ID, ""
                ),
            },
        )
        return self.async_show_form(step_id="init", data_schema=schema)
