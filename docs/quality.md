# Integration quality qualification

EasyControlX targets the [Home Assistant quality rules](https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/)
through Platinum as a custom integration. This is a self-assessment, not an official
HA rating. Qualification is incomplete. The index checked on 2026-10-05 contains
54 cumulative rules.

`Partial` means an implementation or focused test exists, but the complete rule
has not been qualified. `Gap` is known missing work. `Review` requires a bounded
contract or applicability audit. Exemptions require a rule-permitted explanation.

## Bronze

| Rule | State | Evidence or next acceptance step |
| --- | --- | --- |
| action-setup | Implemented | Actions register in integration setup and remain available after unload. Real HA lifecycle tests verify calls before configuration, while loaded, and after unload; unloaded entries reject retained runtime data. |
| appropriate-polling | Partial | Coordinator interval and options exist; measure normal/offline request counts. |
| brands | Review | Verify installed HA/HACS branding assets. |
| common-modules | Partial | API, coordinator, entity, capability, and managed-service owners exist; inspect remaining duplication. |
| config-flow-test-coverage | Source verified | All 317 flow statements and 68 branches are covered on HA 2026.3.0 and 2026.9.4, with no flow exclusions. Public HA flows cover setup, reauthentication, reconfiguration, options, identity checks, certificate repair and pairing recovery. Direct dispatch to a pairing step without a session aborts before network access. Validated pairing state is passed explicitly to internal helpers, and reauthentication reads the entry through HA's owner. See [flow tests](../tests/test_config_flow.py) and [pairing recovery tests](../tests/test_pairing_recovery.py). Installed frontend and release qualification remain separate. |
| config-flow | Partial | UI, discovery, pairing, and token flows have tests; verify actual installed UI. |
| dependency-transparency | Partial | Host contract and HTTPS boundary are documented; inspect shipped requirements and network behaviour. |
| docs-actions | Partial | Automation guide exists; validate each supported action and its parameters. |
| docs-triggers | Exempt | No custom trigger platform or registration is provided. The [HA rule](https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/docs-triggers/) explicitly exempts integrations without triggers. The automation guide explains standard HA entity-state triggers and polling limits. |
| docs-conditions | Exempt | No custom condition platform or registration is provided. The [HA rule](https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/docs-conditions/) explicitly exempts integrations without conditions. The automation guide explains standard state/numeric-state conditions and unavailable-state behavior. |
| docs-high-level-description | Partial | README describes host control; reconcile platform-specific support. |
| docs-installation-instructions | Partial | HACS/manual instructions exist; install a released artifact. |
| docs-removal-instructions | Review | Verify entry removal, host trust revocation guidance, and HACS uninstall instructions. |
| entity-event-setup | Partial | Real HA setup/reload tests retain entity IDs across two reloads and prove old coordinator errors cannot mark replacement entities unavailable. A platform-forwarding failure retries with a fresh runtime owner. Installed-host qualification remains open. |
| entity-unique-id | Partial | Device-based identifiers exist; verify host address changes and upgrades preserve them. |
| has-entity-name | Partial | Shared entity metadata exists; audit primary and companion names. |
| runtime-data | Partial | Typed entry-owned client/coordinator are published after first refresh. Real HA tests verify offline setup has no runtime or entities and repeated reloads replace the owner without changing entity IDs. Failed platform unloading retains the existing runtime owner; failed forwarding recovers with a fresh owner. Installed-host resource qualification remains open. |
| test-before-configure | Partial | Public HA flow tests verify device identity, authentication and certificate trust before creating an entry. Real-host onboarding and installed-release proof remain open. |
| test-before-setup | Partial | Real HA tests prove offline startup enters SETUP_RETRY without runtime or registry entities; reloading after connection recovery creates a healthy owner. Installed-host proof remains open. |
| unique-config-entry | Partial | Duplicate/identity checks exist; cover all supported discovery/manual combinations. |

## Silver

| Rule | State | Evidence or next acceptance step |
| --- | --- | --- |
| action-exceptions | Partial | API maps transport/authentication/status failures; audit every action and response-body failure. |
| config-entry-unloading | Partial | Real HA tests verify successful unload rejects stale runtime data, failed unloading retains its owner in HA FAILED_UNLOAD state, and actions remain registered. Repeated reloads retain entity IDs and detach old coordinators. Installed-host proof remains open. |
| docs-configuration-parameters | Source verified | The configuration guide documents the 30-second polling default, 10–300-second range, empty preferred-monitor default, request selection and reload behavior. Checked against constants, options flow, entry update listener and camera implementation. Installed UI qualification remains open. |
| docs-installation-parameters | Partial | HTTPS, tokens, pairing, and fingerprint approval are documented; validate instructions in HA. |
| entity-unavailable | Partial | Coordinator and capability availability exist; exercise host, service, and active-window loss/recovery. |
| integration-owner | Partial | Maintainers and issue tracker are declared; verify support and security-reporting paths. |
| log-when-unavailable | Review | Inspect one disconnect/reconnect cycle for useful non-repeating logging. |
| parallel-updates | Partial | Buttons and switches declare one parallel update per platform and entry; coordinator-state platforms declare zero. A real HA multi-button action reproduces overlapping commands before the change and verifies serialization afterward. Integration-wide actions, polling, and camera image requests are outside this semaphore. |
| reauthentication-flow | Partial | Reauth and certificate-change checks have tests; verify actual UI and credential replacement. |
| test-coverage | Partial | 253 tests pass on HA 2026.3.0 and 2026.9.4. The combined measurement covers 1,265/1,277 statements (99.06%) and 215/230 branches (93.48%). Flow coverage is complete, the HTTP client covers 142/143 statements and all 38 branches, and the coordinator covers all 34 statements and both branches. Real local HTTPS tests exercise supported commands, file browsing and preview responses; real HA refresh tests exercise optional-inventory failure and recovery. Helpers, managed-service matching and integration actions remain below the above-95% combined module target; the aggregate percentage does not qualify them. Flow-only tests isolate entry setup so they cannot start an unrelated host connection after creating an entry; lifecycle tests exercise real setup separately. |

## Gold

| Rule | State | Evidence or next acceptance step |
| --- | --- | --- |
| devices | Partial | Host device metadata exists; verify registry identity on Windows/macOS and upgrades. |
| diagnostics | Partial | Redaction/nonmutation tests pass for current host/service contracts; inspect downloaded artifacts. |
| discovery-update-info | Partial | Discovery trust/identity tests exist; verify safe address changes and recovery. |
| discovery | Partial | Zeroconf flow exists; verify advertised host platforms and unrelated-device rejection. |
| docs-data-update | Source verified | Guide explains status polling, conditional service-inventory enrichment and its failure policy, action-triggered refreshes, separately requested preview images, polled active-window identity and recovery. Checked against coordinator, capability predicates, actions and camera owners. Real-host request budgets and timing remain unmeasured. |
| docs-examples | Partial | Automation guide exists; execute examples against supported test-host capabilities. |
| docs-known-limitations | Partial | Architecture and entity model describe capability boundaries; reconcile preview/platform limitations. |
| docs-supported-devices | Partial | Host contract defines platform boundary; publish a tested host-version matrix. |
| docs-supported-functions | Partial | Entity model and automation docs exist; reconcile capability-dependent entities/actions. |
| docs-troubleshooting | Review | Verify actionable connection, pairing, certificate, availability, and diagnostic guidance. |
| docs-use-cases | Partial | Automation examples exist; qualify complete supported user workflows. |
| dynamic-devices | Review | Determine applicability for one-host-per-entry and changes in managed-service inventory. |
| entity-category | Partial | Diagnostic/configuration categories exist; audit all platforms. |
| entity-device-class | Partial | Platform metadata exists; audit units, classes, and state classes. |
| entity-disabled-by-default | Partial | Active-window preview is disabled by default; audit other private/noisy entities. |
| entity-translations | Partial | Entities use translation keys; verify complete supported-language names and fallback. |
| exception-translations | Partial | Domain actions, buttons, switches, previews, and refreshes translate client failures through shared HA exception keys. Tests verify English fallback, preserved causes, private-response exclusion from displayed messages, and authentication recovery. Service-validation errors also use keys and named placeholders; all unsupported-capability paths reject before any host call. Rendered frontend and installed-artifact proof remain open. |
| icon-translations | Partial | Custom sensor/button icons use icons.json and entity translation keys; HA loader coverage passes on minimum and current HA. Device-class binary-sensor defaults remain in use. Installed frontend appearance still needs verification. |
| reconfiguration-flow | Partial | Reconfigure validates destination/identity/fingerprint; verify installed UI and preserved bindings. |
| repair-issues | Partial | Authentication and changed-certificate flows exist; audit other failures requiring intervention. |
| stale-devices | Review | Verify removal behaviour and applicability to host/service registry entries. |

## Platinum

| Rule | State | Evidence or next acceptance step |
| --- | --- | --- |
| async-dependency | Partial | API uses aiohttp; cancellation/body/pairing response cleanup has regressions. Complete live resource proof. |
| inject-websession | Partial | Setup/flows inject HA's shared session. Local HTTPS tests verify caller ownership, status/decompression policy, pairing errors, and prevention of cross-origin token forwarding through redirects. Live ownership/resource qualification remains open. |
| strict-typing | Source gate | Strict mypy covers all 19 production modules without import suppression or type-ignore exemptions. CI tests the declared minimum and current qualification HA versions. The API client is shipped inside the integration, with no standalone wrapper package or separate installed-client typing contract. |

## Release qualification

- [ ] Complete all applicable rule rows with evidence or a justified exemption.
- [ ] Validate real Windows/macOS host versions and actual HA onboarding/editor flows.
- [ ] Install and upgrade published HACS artifacts while retaining configuration and entity identity.
- [ ] Measure requests, cancellation, retained resources, and recovery against documented budgets.
- [ ] Record release version, commit, artifact identity, environments, and evidence dates.

See [development](development.md) for reproducible checks and the explicit
minimum-version test-fixture exception. Source tests, downloaded diagnostics,
published artifacts, and installed host behaviour remain separate proof layers.
