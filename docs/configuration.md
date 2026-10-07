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

| Option | Default and effect |
| --- | --- |
| Polling interval | 30 seconds; accepts 10–300 seconds. Controls regular host-status refreshes. |
| Preferred monitor ID | Empty by default. When set, sends that host-provided monitor ID with desktop-preview requests. |

Saving options reloads the integration. Leave the monitor ID empty to omit the
monitor selection from the request. This setting does not select the active
window or change the polling interval. Use an ID reported by the connected host;
a monitor name or an ID copied from another computer may not identify a display.

Use **Reconfigure** to change the base URL or approved fingerprint. Verify a
replacement certificate on the host before saving it.

If a token expires or is revoked, the reauthentication flow accepts a fresh token
or starts a new host-approved pairing. Never place tokens in automation YAML,
screenshots, logs, or issue attachments.

## How data updates

The integration polls the host's authenticated `/api/v1/status` endpoint. It does
not subscribe to a continuous stream of host-status updates. With the default
options, regular refreshes are scheduled every 30 seconds. Network delays and
failed requests can make displayed state older than the configured interval.

When the host advertises service inventory or supplies a services section, a
refresh also requests `/api/v1/services`. An ordinary inventory request failure
does not discard a successful main status response. Authentication and
certificate failures require recovery rather than silently accepting partial
data. Inventory availability does not grant permission to control services.

Successful state-changing buttons, switches and integration actions request a
coordinator refresh. These additional refreshes mean the polling interval is
not a limit on the number of HTTP requests. A shorter interval increases status
and, where applicable, inventory traffic.

Camera previews are fetched separately when Home Assistant requests an image;
they are not downloaded as part of each status poll. Dashboard cards and other
camera consumers can therefore add image traffic independently of the polling
option. The desktop preview uses the preferred monitor ID when configured. The
active-window preview uses the latest polled window identity, so a change of
active window may not be reflected immediately. That camera is disabled by
default and becomes unavailable when the current status has no active window.

If the main status request fails, coordinator-backed entities become
unavailable until a successful update. An authentication or certificate failure
can require the reauthentication or fingerprint steps above. Use these recovery
paths before deleting and recreating an entry.

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
| Unexpected redirect | Configure the final HTTPS origin/base path and make the reverse proxy serve the API directly without redirecting |
| Missing action | Check whether the host advertises that capability |

Download diagnostics after reproducing an issue. Review the file before posting,
and keep tokens, pairing codes, private desktop images, and sensitive paths out
of public reports.
