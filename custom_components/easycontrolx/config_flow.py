from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.zeroconf import ZeroconfServiceInfo
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EasyControlXApiClient, normalize_base_url
from .const import (
    CONF_BASE_URL,
    CONF_CONTROLLER_NAME,
    CONF_DEVICE_ID,
    CONF_PREFERRED_MONITOR_ID,
    CONF_SCAN_INTERVAL,
    DEFAULT_CONTROLLER_NAME,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    OPTIONAL_OPTIONS,
    SCAN_INTERVAL_MAX,
    SCAN_INTERVAL_MIN,
)
from .exceptions import ApiError, CannotConnect, InvalidAuth, PairingExpired, PairingPending
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


async def _async_build_client(
    hass: HomeAssistant,
    base_url: str,
    access_token: str | None = None,
) -> EasyControlXApiClient:
    """Build an API client."""
    return EasyControlXApiClient(async_get_clientsession(hass), base_url, access_token)


class EasyControlXConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for EasyControlX."""

    VERSION = 1
    MINOR_VERSION = 0

    _discovered_base_url: str | None = None
    _discovered_title: str | None = None
    _pending_pairing: PendingPairing | None = None
    _reauth_entry: config_entries.ConfigEntry | None = None

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
            try:
                return await self._async_handle_user_or_reconfigure(user_input)
            except ValueError:
                errors["base"] = "cannot_connect"
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
        }

        schema = self.add_suggested_values_to_schema(
            vol.Schema(
                {
                    vol.Required(CONF_BASE_URL): str,
                    vol.Optional(CONF_ACCESS_TOKEN): str,
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

        errors: dict[str, str] = {}
        if user_input is not None:
            client = await _async_build_client(self.hass, self._pending_pairing.base_url)
            try:
                result = await client.async_confirm_pairing(
                    self._pending_pairing.session_id,
                    self._pending_pairing.verification_code,
                )
            except PairingPending:
                errors["base"] = "pairing_pending"
            except PairingExpired:
                errors["base"] = "pairing_expired"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except ApiError:
                errors["base"] = "pairing_failed"
            else:
                access_token = normalize_optional_string(result.get("accessToken"))
                if access_token:
                    return await self._async_finish_setup(
                        title=self._pending_pairing.title,
                        device_id=self._pending_pairing.device_id,
                        base_url=self._pending_pairing.base_url,
                        access_token=access_token,
                    )
                errors["base"] = "pairing_pending"

        return self.async_show_form(
            step_id="pair",
            data_schema=vol.Schema({}),
            errors=errors,
            description_placeholders={
                "host_name": self._pending_pairing.title,
                "controller_name": self._pending_pairing.controller_name,
                "verification_code": self._pending_pairing.verification_code,
            },
        )

    async def async_step_zeroconf(self, discovery_info: ZeroconfServiceInfo) -> FlowResult:
        """Handle zeroconf discovery."""
        base_url = self._async_base_url_from_discovery(discovery_info)
        if base_url is None:
            return self.async_abort(reason="unsupported_device")

        device_id = discovery_info.properties.get("deviceId")
        title = discovery_info.name.removesuffix("._easycontrolx._tcp.local.")

        if device_id:
            await self.async_set_unique_id(device_id)
            self._abort_if_unique_id_configured(updates={CONF_BASE_URL: base_url})

        self._discovered_base_url = base_url
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

            try:
                client = await _async_build_client(self.hass, base_url, access_token)
                device = await client.async_get_device()
                await client.async_get_status()
            except ValueError:
                errors["base"] = "cannot_connect"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except ApiError:
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(device["deviceId"])
                self._abort_if_unique_id_mismatch()
                return self.async_update_reload_and_abort(
                    self._get_reauth_entry(),
                    data_updates={CONF_ACCESS_TOKEN: access_token},
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_ACCESS_TOKEN): str}),
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
            base_url = normalize_base_url(user_input[CONF_BASE_URL])
            access_token = entry.data[CONF_ACCESS_TOKEN]
            try:
                client = await _async_build_client(self.hass, base_url, access_token)
                device = await client.async_get_device()
                await client.async_get_status()
            except ValueError:
                errors["base"] = "cannot_connect"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except ApiError:
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(device["deviceId"])
                self._abort_if_unique_id_mismatch()
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={CONF_BASE_URL: base_url},
                )

        schema = self.add_suggested_values_to_schema(
            vol.Schema({vol.Required(CONF_BASE_URL): str}),
            {CONF_BASE_URL: entry.data[CONF_BASE_URL]},
        )
        return self.async_show_form(step_id="reconfigure", data_schema=schema, errors=errors)

    async def _async_handle_user_or_reconfigure(self, user_input: dict[str, Any]) -> FlowResult:
        """Handle user-provided connection information."""
        base_url = normalize_base_url(user_input[CONF_BASE_URL])
        access_token = normalize_optional_string(user_input.get(CONF_ACCESS_TOKEN))
        controller_name = (
            normalize_optional_string(user_input.get(CONF_CONTROLLER_NAME))
            or DEFAULT_CONTROLLER_NAME
        )

        if access_token:
            client = await _async_build_client(self.hass, base_url, access_token)
            device = await client.async_get_device()
            await client.async_get_status()
            return await self._async_finish_setup(
                title=device["name"],
                device_id=device["deviceId"],
                base_url=base_url,
                access_token=access_token,
            )

        client = await _async_build_client(self.hass, base_url)
        device = await client.async_get_device()
        pairing = await client.async_start_pairing(controller_name)
        self._pending_pairing = PendingPairing(
            base_url=base_url,
            title=device["name"],
            device_id=device["deviceId"],
            controller_name=controller_name,
            session_id=pairing["sessionId"],
            verification_code=pairing["verificationCode"],
        )
        return await self.async_step_pair()

    async def _async_finish_setup(
        self,
        *,
        title: str,
        device_id: str,
        base_url: str,
        access_token: str,
    ) -> FlowResult:
        """Finish entry creation or update."""
        data = {
            CONF_BASE_URL: base_url,
            CONF_ACCESS_TOKEN: access_token,
            CONF_DEVICE_ID: device_id,
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
        host = discovery_info.host.rstrip(".")
        if not host or not discovery_info.port:
            return None
        return normalize_base_url(f"http://{host}:{discovery_info.port}")


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
