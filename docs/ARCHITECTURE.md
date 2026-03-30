# Architecture Notes

## Repo Boundary

This repository is intentionally separate from the main EasyControlX codebase.

- `EasyControlX` remains the host/service product and may stay private.
- `homeassistant-easycontrolx` remains the public Home Assistant integration.
- The integration depends only on the documented EasyControlX API contract.

That split gives us cleaner licensing, easier public releases, and a safer
upgrade story.

## Layering

### EasyControlX host

Owns:

- discovery
- pairing and trust
- controller tokens
- desktop control
- previews
- file/process/window/power actions

### Home Assistant integration

Owns:

- Home Assistant config entry lifecycle
- entity mapping
- polling cadence
- diagnostics
- reauth/reconfigure flows
- future HA-specific services and automations

## Compatibility Philosophy

- Prefer additive changes over breaking changes.
- Avoid storing derived runtime state in config entries.
- Keep entity unique IDs stable even if labels or capabilities expand.
- Keep discovery optional; manual setup must remain first-class.
- Use one integration for all EasyControlX hosts and let capabilities decide
  which entities and services exist per host.

## Entity Rules

The Home Assistant mapping is intentionally capability-driven.

- Inventory visibility and control must be treated separately.
- Read-only host sections may create read-only entities without implying
  control.
- Control entities should exist only when the host advertises the matching
  action capability.
- Optional enrichment endpoints may add detail, but they must not change the
  unique-ID model or the capability rules.

The more detailed entity mapping rules live in
[`ENTITY_MODEL.md`](ENTITY_MODEL.md).
