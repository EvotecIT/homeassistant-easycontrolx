# Architecture Notes

## Repo Boundary

This repository is intentionally separate from the main EasyControlX codebase.

- `EasyControlX` remains the host/service product and may stay private.
- `homeassistant-easycontrolx` remains the public Home Assistant integration.
- The integration depends only on the documented EasyControlX API contract.

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
- explicit HTTPS certificate trust and certificate-rotation repair
- entity mapping
- polling cadence
- diagnostics
- reauth/reconfigure flows
- Home Assistant-specific services and automation examples

## Compatibility Philosophy

- Prefer additive changes over breaking changes.
- Avoid storing derived runtime state in config entries.
- Keep entity unique IDs stable even if labels or capabilities expand.
- Keep discovery optional; manual setup must remain first-class.
- Treat Zeroconf TXT data only as a connection hint. It must never repoint an
  existing token or silently approve a certificate fingerprint.
- Require HTTPS, validate tokens before storage, and preserve certificate pins
  until the user explicitly verifies a replacement on the host.
- Keep destructive host power actions behind the host's per-action human
  confirmation instead of manufacturing confirmation in an automation surface.
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
