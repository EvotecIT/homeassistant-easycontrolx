# EasyControlX for Home Assistant

`homeassistant-easycontrolx` is a public Home Assistant custom integration for
EasyControlX hosts.

The goal is simple: make EasyControlX the long-term replacement for brittle
Windows desktop helper stacks such as Hass.Agent-style setups, while keeping the
Home Assistant side clean, public, and easy to install.

## Design Goals

- Native Home Assistant integration, not pasted YAML as the primary UX
- Public custom integration repo with a stable API boundary to EasyControlX
- Future-friendly config entries, diagnostics, reauth, and reconfigure flows
- A path to grow from host controls into a broader workstation automation stack
- No direct dependency on DesktopManager or private EasyControlX source code

## Current Scope

The first scaffold includes:

- UI config flow
- Zeroconf discovery for `_easycontrolx._tcp.local.`
- Pairing flow scaffold based on EasyControlX `/pair/start` and `/pair/confirm`
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

Local development and CI now use:

- `ruff check .`
- `pytest -q`
- Home Assistant `hassfest` in GitHub Actions

Install development dependencies with:

```powershell
python -m pip install -r requirements-dev.txt
```

If you later add deeper Home Assistant runtime tests that need the HA pytest
harness, install:

```powershell
python -m pip install -r requirements-ha-tests.txt
```
