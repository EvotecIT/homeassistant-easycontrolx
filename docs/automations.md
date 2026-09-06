# Automations

[Back to the README](../README.md) · [Configuration](configuration.md)

Use the entities your host actually exposes. A read-only inventory does not
grant permission to control the listed apps, processes, files, or services.

## Start with an entity action

For a supported host, a Lock button can be called with Home Assistant's standard
button action:

```yaml
action: button.press
target:
  entity_id: button.my_computer_lock
```

Replace the placeholder with the Lock entity from your EasyControlX device.
Test it deliberately: locking affects the person using the computer.

## Example: refresh the status

If you want a scheduled refresh in addition to normal polling, this example
requests one every 15 minutes. With one configured host, the integration can
select it automatically.

```yaml
alias: EasyControlX periodic refresh
triggers:
  - trigger: time_pattern
    minutes: "/15"
actions:
  - action: easycontrolx.refresh
mode: single
```

With multiple hosts, select the intended host's config entry in the action
editor and supply its `config_entry_id`. A config-entry ID is not an entity ID.
The normal polling option is usually sufficient without this automation.

## Available action groups

| Group | Actions |
| --- | --- |
| Power | Lock and Sleep only |
| Media and audio | Supported playback, mute, and volume operations |
| Apps and processes | Supported launch and process actions |
| Managed services | Curated Windows service inventory and supported control |
| Files | Supported browsing and copy workflows |
| Status | Explicit refresh |

Use **Developer tools → Actions** to inspect fields and supported choices.
The full field definitions are in
[services.yaml](../custom_components/easycontrolx/services.yaml).

For managed services, prefer the native switch or restart button when exposed.
Inventory-only hosts may have a running-state sensor but no control entity.

## Safety

Keep restart and shutdown on the host, where they require real per-action human
confirmation. Do not manufacture that confirmation in Home Assistant.

Process, service, and file actions can interrupt work or change data. Scope them
to the intended host and item; avoid broad recurring actions or automatic retries
that repeat a destructive operation. Never include controller tokens in YAML.
