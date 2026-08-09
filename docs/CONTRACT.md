# Shared Host Contract

This document defines the cross-platform host contract that the Home Assistant
integration should rely on.

The rule is:

- Home Assistant integrates with an `EasyControlX host`
- the host may be Windows or macOS
- platform-specific features are additive and capability-driven
- the Home Assistant integration should not fork into separate platform
  integrations unless the protocol itself forks

## Shared Core Endpoints

Every host that wants to be first-class in Home Assistant should expose:

- `GET /api/v1/health`
- `GET /api/v1/device`
- `GET /api/v1/capabilities`
- `GET /api/v1/status`
- `POST /api/v1/pair/start`
- `POST /api/v1/pair/confirm`
- `GET /api/v1/controllers`
- `DELETE /api/v1/controllers/{controllerId}`
- `GET /ws/v1/control`

Action endpoints should exist only when the host advertises the matching
capability.

## Discovery

Hosts should advertise `_easycontrolx._tcp.local.` and expose TXT keys:

- `deviceId`
- `platform`
- `protocol`
- `paired`
- `api`
- `ws`
- `baseUrl` when the advertised API endpoint is HTTPS
- `tlsFingerprint` when the host uses a certificate that clients should pin

The `deviceId` must stay stable and should be used as the Home Assistant unique
ID. Discovery data is unauthenticated and is therefore a hint only: clients must
not use it to change an existing credential destination or silently approve a
certificate fingerprint.

## Transport And Trust

- Home Assistant connections use HTTPS.
- A host may use a publicly trusted or private/self-signed certificate.
- For a private/self-signed certificate, the user compares and explicitly
  approves the SHA-256 leaf-certificate fingerprint shown by the host.
- A changed fingerprint fails closed and enters the repair flow. The replacement
  pin is stored only after the user compares it with the host again.
- Controller tokens are sent only in the `X-EasyControlX-Token` header and are
  validated before the integration stores or replaces them.
- Pairing completes only after host approval, verification-code comparison, and
  a successful authenticated request with the issued token.

## Shared `/api/v1/status` Shape

Every host should expose an aggregate status payload with this top-level shape:

```json
{
  "status": "ok",
  "service": "EasyControlX.<PlatformHost>",
  "serverTimeUtc": "2026-03-30T14:00:00Z",
  "device": {
    "deviceId": "host-123",
    "name": "Office Mac",
    "platform": "macOS",
    "operatingSystem": "macOS 15",
    "protocolVersion": "1",
    "capabilities": ["media", "audio.output"],
    "isPaired": true,
    "serverTimeUtc": "2026-03-30T14:00:00Z"
  },
  "discovery": {
    "enabled": true,
    "serviceType": "_easycontrolx._tcp",
    "instanceName": "Office Mac"
  },
  "trust": {
    "hasTrustedControllers": true,
    "trustedControllerCount": 2
  },
  "power": {
    "enabled": true,
    "destructiveActionsEnabled": true,
    "supportedActions": ["Lock", "Sleep", "Restart"]
  },
  "audio": {
    "isAvailable": true,
    "summary": "Output available.",
    "itemCount": null
  },
  "media": {
    "isAvailable": true,
    "summary": "Media available.",
    "itemCount": null
  },
  "bluetooth": {
    "isAvailable": true,
    "summary": "2 connected Bluetooth device(s).",
    "itemCount": 2
  }
}
```

Hosts may add extra sections such as:

- `system`
- `storage`
- `network`
- `services`
- `interactiveSession`
- `helper`
- `windows`
- `monitors`
- `processes`
- `files`
- `virtualization`

But the shared top-level sections above should be present for both Windows and
macOS when the subsystem is relevant.

## Capability Namespaces

### Core cross-platform capabilities

- `pointer`
- `keyboard`
- `media`
- `media.metadata`
- `audio.output`
- `bluetooth.list`
- `bluetooth.control`
- `system.cpu`
- `system.memory`
- `system.uptime`
- `system.storage`
- `system.network`
- `power.lock`
- `power.sleep`
- `power.restart`
- `power.shutdown`
- `desktop.preview`

### Windows-specific capabilities

- `windows.windows.list`
- `windows.windows.preview`
- `windows.monitors.list`
- `windows.monitors.preview`
- `windows.processes.list`
- `windows.processes.control`
- `windows.files.browse`
- `windows.files.download`
- `windows.files.copy`
- `windows.services.list`
- `windows.services.control`
- `windows.hyperv.list`
- `windows.hyperv.control`

### macOS-specific capabilities

- `macos.helper.status`
- `macos.permissions`
- `macos.bluetooth.control`

## Legacy Compatibility

The current Windows host already exposes some non-namespaced capability names:

- `windows.list`
- `windows.preview`
- `monitors.list`
- `monitors.preview`
- `processes.list`
- `processes.control`
- `files.browse`
- `files.download`
- `files.copy`

The Home Assistant integration should accept both the legacy and namespaced
forms during migration.

## Home Assistant Mapping Rules

- The integration should create only entities whose required capabilities are
  present.
- Missing platform-specific capabilities must not be treated as errors.
- Home Assistant exposes only `Lock` and `Sleep` from the host power surface.
  `Restart` and `Shutdown` stay host-side because the protocol requires genuine
  per-action human confirmation.
- New features should be added as new entities or services, not by changing old
  entity unique IDs.
- Platform-specific sections in `/status` should be treated as optional.
- Telemetry should start as stable host-level sensors. Per-volume,
  per-interface, or per-service entities should be added later.

## Telemetry Extensions

To support workstation observability cleanly, the shared status payload should
grow with these optional sections:

```json
{
  "system": {
    "uptimeSeconds": 86400,
    "cpu": {
      "usagePercent": 12.5
    },
    "memory": {
      "usagePercent": 46.1,
      "availableBytes": 17179869184,
      "totalBytes": 34359738368
    }
  },
  "storage": {
    "itemCount": 3,
    "summary": "3 storage volume(s)."
  },
  "network": {
    "itemCount": 2,
    "summary": "2 active network interface(s)."
  },
  "services": {
    "itemCount": 5,
    "summary": "5 curated service(s) exposed for management."
  }
}
```

The `services` section is intentionally curated. Home Assistant should manage a
safe, host-defined subset of services rather than mirroring the entire
`services.msc` surface by default.
