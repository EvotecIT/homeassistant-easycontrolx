# Development

[Back to the README](../README.md) · [Architecture](ARCHITECTURE.md) ·
[Host contract](CONTRACT.md)

The [quality ledger](quality.md) tracks each applicable HA rule and the remaining
source, artifact, and installed-host qualification work.

## Local checks

Install development and Home Assistant test dependencies:

```bash
python -m pip install -r requirements-dev.txt -r requirements-ha-tests.txt
ruff check .
python -m mypy
pytest -q
```

GitHub Actions also runs Home Assistant hassfest and HACS validation.

The Python 3.14 CI lanes install the declared minimum HA 2026.3.0 and the
current qualification target HA 2026.9.4 explicitly. Update the current target
as part of a validated compatibility change. An unconstrained install on an
older Python can silently select an older HA version and does not prove the
declared support range.

The test plugin has no release for HA 2026.3.0. The minimum lane installs the
0.13.317 fixtures for HA 2026.3.1, then replaces only Home Assistant with
2026.3.0 using `pip install --no-deps homeassistant==2026.3.0`. Both core releases
declare the same runtime dependencies. This is an explicit test-fixture version
exception: tests and typing run against the actual minimum core, while the
fixture package metadata still names 2026.3.1. The current lane uses a matching
core and fixture release.

Mypy checks every production module in strict mode without import suppression
or project-wide type ignores. Its pinned development dependency is not included
in the HACS manifest or required by an installed integration. JSON responses are
validated as objects at the API boundary, and HTTP responses are released after
body reads, cancellation, and rejected pairing/status responses.

## Diagnostics privacy

Diagnostics redact credentials, host identity and address, certificate fingerprint,
the preferred monitor identifier, and identifying names in host and service status.
Free-text descriptions and summaries are redacted because hosts can include private
content in those fields. Platform, protocol version, capabilities, availability,
service state, and numeric health information remain available for troubleshooting.
Redaction leaves config-entry data, options, and coordinator state unchanged.

When adding host response fields, check whether they identify a person, machine,
window, or application before including them in diagnostics. Review downloaded
diagnostics before sharing them. The diagnostics regression tests cover the public
status shape and service inventory; they do not establish live-host qualification.

## Integration boundary

The EasyControlX host owns pairing, trust, desktop operations, and capabilities.
This public integration depends on the documented API, not private host source
or DesktopManager internals.

Keep setup-critical values in config-entry data, optional tuning in options, and
runtime state in `ConfigEntry.runtime_data`. Use the host's stable `deviceId`
for identity. New entities should follow host capabilities without changing
existing entity IDs.

The [architecture](ARCHITECTURE.md), [host contract](CONTRACT.md), and
[entity model](ENTITY_MODEL.md) are the sources for those boundaries. Planned
work belongs in the [roadmap](ROADMAP.md), not in the README's feature list.
