# Automations

[Back to the README](../README.md) · [Configuration](configuration.md)

Use the entities your host actually exposes. A read-only inventory does not
grant permission to control the listed apps, processes, files, or services.

## Triggers and conditions

EasyControlX provides entities and actions; it does not register custom automation
triggers or conditions. Use Home Assistant's standard state and numeric-state
triggers and conditions with the entities available on your host.

In the automation editor, add a state trigger under **When** and select an
EasyControlX entity. For example, a Helper ready binary sensor can trigger a
notification when it changes from `on` to `off`. That sensor is available only
when the host reports helper or interactive-session information. Its state is
updated by polling, so detection follows the configured polling interval.

Under **And if**, add a state condition to require an entity to be `on`, or a
numeric-state condition to compare a supported count sensor with a threshold.
A condition checks the current state when the automation runs; it does not start
the automation. An explicit `on` condition does not match `unknown` or
`unavailable`. Select your actual entity from the editor rather than assuming a
generated entity ID.

Entity state describes the latest reported host state. It does not grant host
permissions or guarantee that a later action will succeed; actions still validate
capabilities, authorization, and connectivity.

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
