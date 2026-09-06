# EasyControlX for Home Assistant

![EasyControlX for Home Assistant](assets/homeassistant-easycontrolx-social.png)

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://hacs.xyz/)
[![CI](https://img.shields.io/github/actions/workflow/status/EvotecIT/homeassistant-easycontrolx/ci.yml?branch=main&style=for-the-badge&label=CI)](https://github.com/EvotecIT/homeassistant-easycontrolx/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/EvotecIT/homeassistant-easycontrolx?style=for-the-badge)](LICENSE)

## Overview

Connect an EasyControlX host to Home Assistant over HTTPS. Use host status,
desktop previews, and the controls that the host makes available from the same
Home Assistant setup.

- Host, session, audio, media, and system-status entities.
- Lock, Sleep, playback, and mute buttons where supported.
- Desktop and active-window preview cameras.
- Capability-gated app, process, file, and managed-service actions.

You need a running EasyControlX host; this repository installs only the Home
Assistant integration. Windows and macOS capabilities can differ. Restart and
shutdown remain host-side actions with per-action human confirmation.

## Sponsor

Support development and maintenance through
[GitHub Sponsors](https://github.com/sponsors/PrzemyslawKlys).
Sponsorship is optional; these projects remain open source.

## More for your Home Assistant home

Other integrations and dashboards we maintain:

- [Dreame & MOVA mowers](https://github.com/EvotecIT/homeassistant-dreamelawnmower) — Mowing controls, maps, schedules, and supported cameras.
- [Lawn Mower Card](https://github.com/EvotecIT/lovelace-lawn-mower-card) — A dashboard for mower state, maps, and controls.
- [KEF](https://github.com/EvotecIT/homeassistant-kef) — Local control for modern and legacy speaker families.
- [Devialet](https://github.com/EvotecIT/homeassistant-devialet) — Local speaker control, with Dione support.
- [Siegenia](https://github.com/EvotecIT/homeassistant-siegenia) — Local control for supported window controllers.

For a native app connected to the same Home Assistant setup:

- [CasaRay](https://casaray.dev/) — rooms, devices, cameras, and home activity on
  iPhone, iPad, and Mac.
- [Tactra Remote](https://tactra.dev/) — media players, speakers, and TV controls
  on iPhone, iPad, Apple Watch, and Mac.

Neither app is required to use this project.

## Installation

### HACS

[![Open this repository in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=EvotecIT&repository=homeassistant-easycontrolx&category=integration)

1. Open the repository with the button above. Alternatively, in HACS choose
   **Custom repositories**, add `https://github.com/EvotecIT/homeassistant-easycontrolx`,
   and select **Integration**.
2. Download **EasyControlX** and restart Home Assistant.
3. Open **Settings → Devices & services → Add integration**, then choose
   **EasyControlX**.

### Manual

1. Download the repository and copy `custom_components/easycontrolx` into your
   Home Assistant `config/custom_components` directory.
2. Restart Home Assistant.
3. Add **EasyControlX** from **Settings → Devices & services**.

## Configuration

1. Enter the EasyControlX host's **HTTPS URL**.
2. For a self-signed certificate, compare and enter the SHA-256 fingerprint
   shown by the host.
3. Paste an existing controller token, or leave it blank to start pairing.
4. For pairing, approve the request on the host and enter the matching
   verification code in Home Assistant.

Use **Configure** to adjust polling and the preferred preview monitor. If the
host address or certificate changes, use the reconfigure or repair flow and
verify the new fingerprint on the host itself.

Upgrading from integration version 0.1 requires the host's HTTPS API. Existing
HTTP entries migrate to HTTPS, and self-signed hosts require fingerprint
approval. See [configuration and migration](docs/configuration.md).

## Documentation

| I want to… | Guide |
| --- | --- |
| Pair a host, change connection settings, or migrate from HTTP | [Configuration](docs/configuration.md) |
| Use buttons and services in automations | [Automations](docs/automations.md) |
| Understand which entities my host provides | [Entity model](docs/ENTITY_MODEL.md) |
| Contribute or implement a compatible host | [Development](docs/development.md) · [Host contract](docs/CONTRACT.md) |
| Understand the integration boundary or planned work | [Architecture](docs/ARCHITECTURE.md) · [Roadmap](docs/ROADMAP.md) |

## Support

[Report an issue](https://github.com/EvotecIT/homeassistant-easycontrolx/issues)
with the host platform and version, integration version, and the failed action.
Include diagnostics only after reviewing them. Never post controller tokens,
pairing codes, or screenshots containing private desktop content.
