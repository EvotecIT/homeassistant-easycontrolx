# Entity Model

This document explains how `homeassistant-easycontrolx` decides which Home
Assistant entities and services to create for a given EasyControlX host.

## Core Rule

The integration represents an `EasyControlX host`, not a specific operating
system implementation.

That means:

- one config entry per host
- one shared coordinator based on `GET /api/v1/status`
- optional enrichment calls only when a feature needs more detail
- entities and services are created only when the host advertises the right
  capability or section

## Capability-First Behavior

Entity creation follows these rules:

- if a feature has an explicit capability, that capability is the primary
  source of truth
- if a status section already exists and is stable enough to map, the
  integration may use that section as a fallback
- missing platform-specific capabilities are treated as normal, not as errors

Examples:

- `windows.services.list` allows the integration to expose managed-service
  inventory sensors and optional enrichment from `/api/v1/services`
- `windows.services.control` is required before control entities such as
  switches or restart buttons are created
- `system.cpu`, `system.memory`, and `system.uptime` allow shared telemetry
  sensors for both Windows and macOS

## Read-Only Versus Control Entities

The integration intentionally separates inventory from control.

Examples:

- a host with service inventory only may expose a managed-services sensor
- that same host may expose per-service running-state binary sensors
- that same host must not expose service switches or restart buttons unless
  service control is also supported
- a host with remote-session summary data may expose diagnostic entities
  without exposing any remote input features

This is important because it keeps Home Assistant honest about what the host
can actually do.

## Shared Versus Enriched Data

The coordinator always starts with `/api/v1/status`.

Optional enrichment is allowed when:

- the base status says a feature exists
- the host exposes a more detailed endpoint for that feature
- using the richer endpoint does not change entity identity rules

Current example:

- managed-service entities use `/api/v1/status` for summary presence
- if service inventory is supported, the coordinator may enrich the status with
  `/api/v1/services`

## Stability Rules

- unique IDs are based on stable host identifiers and stable service names
- adding a capability should add new entities, not rename old ones
- changing labels or summaries must not change entity unique IDs
- inventory-only hosts must stay inventory-only in Home Assistant until the
  host explicitly advertises control

## Why This Matters

This capability-gated model is what keeps one integration usable for Windows,
macOS, and future EasyControlX hosts without forking into separate HA
integrations or leaking host internals into Home Assistant.
