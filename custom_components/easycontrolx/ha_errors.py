"""Translate client failures at Home Assistant presentation boundaries."""

from collections.abc import Iterator
from contextlib import contextmanager

from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN
from .exceptions import (
    CannotConnect,
    EasyControlXError,
    InvalidAuth,
    TLSCertificateUntrusted,
    TLSFingerprintMismatch,
)


def api_error_translation_key(error: EasyControlXError) -> str:
    """Choose recovery guidance without including a raw server response."""
    if isinstance(error, TLSFingerprintMismatch):
        return "certificate_changed"
    if isinstance(error, TLSCertificateUntrusted):
        return "certificate_untrusted"
    if isinstance(error, InvalidAuth):
        return "authentication_failed"
    if isinstance(error, CannotConnect):
        return "host_unavailable"
    return "request_failed"


@contextmanager
def translate_api_errors() -> Iterator[None]:
    """Preserve client errors as causes of translated HA action failures."""
    try:
        yield
    except EasyControlXError as error:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key=api_error_translation_key(error),
        ) from error
