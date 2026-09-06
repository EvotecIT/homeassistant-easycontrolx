# Configuration and migration

[Back to the README](../README.md) · [Automations](automations.md)

## Before setup

Install and run a compatible EasyControlX host on the computer you want to
connect. This integration does not install the host.

Have its HTTPS base URL and either an existing controller token or permission
to approve a new pairing. For a self-signed certificate, obtain the SHA-256
fingerprint directly from the host.

## Pair a host

1. Add **EasyControlX** in **Settings → Devices & services**.
2. Enter the host's HTTPS base URL without credentials, a query string, or a
   fragment.
3. If needed, compare and enter its certificate fingerprint: 64 hexadecimal
   characters for SHA-256.
4. Enter an existing controller token, or leave it blank to start pairing.
5. For pairing, compare the verification code, approve the request on the host,
   and enter the matching code in Home Assistant.

Discovery is a connection hint, not proof of trust. Do not approve a new
certificate fingerprint solely because it appeared in a discovery message.

## Options

Use **Configure** for:

- polling interval in seconds;
- preferred monitor ID for desktop preview.

Use **Reconfigure** to change the base URL or approved fingerprint. Verify a
replacement certificate on the host before saving it.

If a token expires or is revoked, the reauthentication flow accepts a fresh token
or starts a new host-approved pairing. Never place tokens in automation YAML,
screenshots, logs, or issue attachments.

## Upgrading from version 0.1

The integration migrates old HTTP entries to HTTPS. Upgrade the host so its
current HTTPS API is available first.

A self-signed host requires an explicit repair step to approve its fingerprint.
Do not work around this by disabling HTTPS or sending the old token to an
unverified destination.

## Entities and missing controls

Entities depend on host capabilities. An inventory sensor does not imply the
host permits changes to the item it reports.

- Desktop and active-window cameras require preview support.
- Managed-service switches require control support, not only service inventory.
- Restart and shutdown remain on the host with per-action human confirmation.
- Windows and macOS hosts may expose different controls through the same
  integration.

See [the entity model](ENTITY_MODEL.md) for the detailed mapping.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| HTTPS required | Replace an HTTP URL with the host's actual HTTPS endpoint |
| Fingerprint mismatch | Compare the certificate currently shown by the host; do not blindly accept a replacement |
| Pairing pending | Approve the request on the host and enter the matching code |
| Pairing expired | Start a new pairing flow |
| Cannot connect | Check the host is running, reachable, and serving the expected HTTPS API |
| Missing action | Check whether the host advertises that capability |

Download diagnostics after reproducing an issue. Review the file before posting,
and keep tokens, pairing codes, private desktop images, and sensitive paths out
of public reports.
