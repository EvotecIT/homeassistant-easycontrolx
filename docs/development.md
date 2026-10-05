# Development

[Back to the README](../README.md) · [Architecture](ARCHITECTURE.md) ·
[Host contract](CONTRACT.md)

## Local checks

Install development and Home Assistant test dependencies:

```bash
python -m pip install -r requirements-dev.txt -r requirements-ha-tests.txt
ruff check .
pytest -q
```

GitHub Actions also runs Home Assistant hassfest and HACS validation.

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
