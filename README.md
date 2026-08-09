# EasyControlX for Home Assistant

`homeassistant-easycontrolx` is a public Home Assistant custom integration for
EasyControlX hosts.

The goal is simple: make EasyControlX the long-term replacement for brittle
Windows desktop helper stacks such as Hass.Agent-style setups, while keeping the
Home Assistant side clean, public, and easy to install.

## 🧩 More from Evotec

Our Home Assistant projects:

- [Dreame Lawn Mower](https://github.com/EvotecIT/homeassistant-dreamelawnmower)
  with its companion
  [Lawn Mower Card](https://github.com/EvotecIT/lovelace-lawn-mower-card)
- [Siegenia](https://github.com/EvotecIT/homeassistant-siegenia) for local
  window control
- [KEF](https://github.com/EvotecIT/homeassistant-kef) for local speaker control
- [Devialet](https://github.com/EvotecIT/homeassistant-devialet) for local
  speaker control
- [EasyControlX](https://github.com/EvotecIT/homeassistant-easycontrolx) for
  workstation control

Our Apple apps:

- [CasaRay](https://casaray.dev/) offers a calm whole-home view on iPhone, iPad,
  and Mac. [View it on the App Store](https://apps.apple.com/us/app/casaray/id6778025328).
- [Tactra Remote](https://tactra.dev/) focuses on Home Assistant media control
  across iPhone, iPad, Apple Watch, and Mac.
  [View it on the App Store](https://apps.apple.com/us/app/tactra-remote/id6775426723).

CasaRay's complete-home Free experience remains genuinely useful. CasaRay Plus
and Tactra purchases help fund continued work on that free experience and these
open-source Home Assistant projects. If you prefer to support the open-source
work directly, [GitHub Sponsors](https://github.com/sponsors/PrzemyslawKlys) is
another option. None of them is required to use this project.

## Design Goals

- Native Home Assistant integration, not pasted YAML as the primary UX
- Public custom integration repo with a stable API boundary to EasyControlX
- Future-friendly config entries, diagnostics, reauth, and reconfigure flows
- A path to grow from host controls into a broader workstation automation stack
- No direct dependency on DesktopManager or private EasyControlX source code

## Installation

EasyControlX is available as a HACS custom repository:

1. In HACS, open the three-dot menu and choose **Custom repositories**.
2. Add `https://github.com/EvotecIT/homeassistant-easycontrolx` as an
   **Integration** repository.
3. Search for **EasyControlX**, install it, and restart Home Assistant.
4. Open **Settings → Devices & services → Add integration**, then choose
   **EasyControlX**.

Use the host's HTTPS URL. If EasyControlX uses a self-signed certificate, copy
the SHA-256 certificate fingerprint shown by the host and compare it before
continuing. You may paste an existing controller token or use the guided pairing
flow. Pairing requires both host approval and entry of the matching verification
code.

Entries created by version 0.1 are migrated from HTTP to HTTPS. If the host uses
a self-signed certificate, Home Assistant starts a repair flow so you can compare
and approve its fingerprint. The host must expose the current HTTPS API before
upgrading the integration.

Restart and shutdown deliberately remain host-side actions because they require
a real, per-action human confirmation. Home Assistant exposes Lock and Sleep,
plus safe capability-gated media, audio, app, process, file, and managed-service
controls.

## Current Scope

The integration includes:

- UI config flow
- Zeroconf discovery for `_easycontrolx._tcp.local.`
- Secure HTTPS pairing based on EasyControlX `/pair/start` and `/pair/confirm`
- Optional SHA-256 certificate pinning with explicit certificate-rotation repair
- A typed runtime-data setup with `DataUpdateCoordinator`
- Initial `sensor`, `binary_sensor`, `button`, and `camera` platforms
- Native `switch` entities for curated managed Windows services
- Per-service restart buttons for curated managed Windows services
- Per-service running-state binary sensors for inventory-only managed-service hosts
- Native Home Assistant services for power, media, audio, refresh, app launch,
  process actions, managed service actions, and file workflows
- Diagnostics with token redaction
- Options flow for polling interval and preferred preview monitor

## Future-Friendly Rules

- Keep the integration bound to the documented EasyControlX HTTP contract only
- Store setup-critical data in config-entry data and optional tuning in options
- Use the EasyControlX `deviceId` as the Home Assistant unique ID
- Add new features as new entity platforms or services without breaking existing entity IDs
- Keep runtime state in `ConfigEntry.runtime_data`
- Treat diagnostics, reauth, and reconfigure as first-class features, not cleanup work
- Keep entity creation capability-driven so Windows and macOS share one
  integration cleanly

## Replacement Strategy

This repo is meant to grow into a serious workstation integration, not just a
few power buttons. The roadmap in [`docs/ROADMAP.md`](docs/ROADMAP.md) is aimed
at replacing the common "Windows agent plus fragile custom scripts" pattern with
a more coherent host-control stack.

The shared host contract and capability namespace plan live in
[`docs/CONTRACT.md`](docs/CONTRACT.md).

The Home Assistant entity creation rules and capability-gated mapping model
live in [`docs/ENTITY_MODEL.md`](docs/ENTITY_MODEL.md).

## Development Checks

Local development and CI use:

- `ruff check .`
- `pytest -q`
- Home Assistant `hassfest` in GitHub Actions

Install all development and Home Assistant test dependencies with:

```powershell
python -m pip install -r requirements-dev.txt -r requirements-ha-tests.txt
```
