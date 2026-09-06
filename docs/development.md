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
