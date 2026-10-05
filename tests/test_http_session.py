"""Borrowed-session and redirect contracts against local HTTPS endpoints."""

import gzip
import json
import ssl
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from ipaddress import ip_address

import pytest
from aiohttp import ClientSession, web
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

from custom_components.easycontrolx.api import EasyControlXApiClient
from custom_components.easycontrolx.const import TOKEN_HEADER
from custom_components.easycontrolx.exceptions import (
    ApiError,
    InvalidAuth,
    PairingExpired,
    PairingPending,
)

pytestmark = pytest.mark.usefixtures("socket_enabled")


@pytest.fixture
def tls_material(tmp_path):
    """Generate a temporary certificate trusted only through the tested pin."""
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "loopback test")])
    now = datetime.now(UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(hours=1))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(
            x509.SubjectAlternativeName([x509.IPAddress(ip_address("127.0.0.1"))]), critical=False
        )
        .sign(key, hashes.SHA256())
    )
    certificate = tmp_path / "loopback.crt"
    private_key = tmp_path / "loopback.key"
    certificate.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    private_key.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    try:
        context.load_cert_chain(certificate, private_key)
    finally:
        certificate.unlink()
        private_key.unlink()
    return context, cert.fingerprint(hashes.SHA256()).hex()


@asynccontextmanager
async def local_server(tls_material, handler):
    app = web.Application()
    app.router.add_route("*", "/{tail:.*}", handler)
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    try:
        await web.TCPSite(runner, "127.0.0.1", 0, ssl_context=tls_material[0]).start()
        yield f"https://127.0.0.1:{runner.addresses[0][1]}"
    finally:
        await runner.cleanup()


@pytest.mark.parametrize(
    ("operation", "status", "error"),
    [
        ("status", 401, InvalidAuth),
        ("confirm", 410, PairingExpired),
        ("confirm", 403, ApiError),
        ("confirm", 202, PairingPending),
    ],
)
async def test_session_status_policy_preserves_auth_and_pairing_errors(
    tls_material, operation, status, error
):
    async def handler(request):
        return web.Response(status=status)

    async with (
        local_server(tls_material, handler) as base_url,
        ClientSession(raise_for_status=True) as session,
    ):
        client = EasyControlXApiClient(
            session,
            base_url,
            access_token="fixture-only-token",
            tls_fingerprint=tls_material[1],
        )
        with pytest.raises(error):
            if operation == "status":
                await client.async_get_status()
            else:
                await client.async_confirm_pairing("fixture-session", "123456")
        assert not session.closed


async def test_session_decompression_policy_preserves_json(tls_material):
    async def handler(request):
        return web.Response(
            body=gzip.compress(json.dumps({"deviceId": "local-fixture"}).encode()),
            headers={"Content-Encoding": "gzip"},
            content_type="application/json",
        )

    async with (
        local_server(tls_material, handler) as base_url,
        ClientSession(auto_decompress=False) as session,
    ):
        client = EasyControlXApiClient(session, base_url, tls_fingerprint=tls_material[1])
        assert await client.async_get_device() == {"deviceId": "local-fixture"}
        assert not session.closed


async def test_redirect_does_not_forward_access_token_to_another_origin(tls_material):
    received_tokens = []

    async def destination(request):
        received_tokens.append(request.headers.get(TOKEN_HEADER))
        return web.json_response({"status": "redirected"})

    async with local_server(tls_material, destination) as destination_url:

        async def redirect(request):
            return web.Response(status=302, headers={"Location": destination_url})

        async with (
            local_server(tls_material, redirect) as base_url,
            ClientSession() as session,
        ):
            client = EasyControlXApiClient(
                session,
                base_url,
                access_token="fixture-only-token",
                tls_fingerprint=tls_material[1],
            )
            error = None
            try:
                await client.async_get_status()
            except ApiError as caught:
                error = caught
            assert received_tokens == []
            assert isinstance(error, ApiError)
            assert not session.closed
