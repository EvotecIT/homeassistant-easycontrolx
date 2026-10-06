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
| config-flow-test-coverage | Gap | Measured flow statement coverage is 96.6% (312/323), with 86.8% branch coverage (66/76). Tests cover post-approval token rejection, changed host identity, certificate repair without losing the pairing session, discovery trust checks, and options persistence. Defensive and remaining flow paths still need qualification. |
| config-flow | Partial | UI, discovery, pairing, and token flows have tests; verify actual installed UI. |
| dependency-transparency | Partial | Host contract and HTTPS boundary are documented; inspect shipped requirements and network behaviour. |
| docs-actions | Partial | Automation guide exists; validate each supported action and its parameters. |
| docs-triggers | Review | Audit applicability and document supported automation usage. |
| docs-conditions | Review | Audit applicability and document supported automation usage. |
| docs-high-level-description | Partial | README describes host control; reconcile platform-specific support. |
| docs-installation-instructions | Partial | HACS/manual instructions exist; install a released artifact. |
| docs-removal-instructions | Review | Verify entry removal, host trust revocation guidance, and HACS uninstall instructions. |
| entity-event-setup | Partial | Real HA setup/reload tests retain entity IDs across two reloads and prove old coordinator errors cannot mark replacement entities unavailable. Failed platform forwarding and installed-host qualification remain open. |
| entity-unique-id | Partial | Device-based identifiers exist; verify host address changes and upgrades preserve them. |
| has-entity-name | Partial | Shared entity metadata exists; audit primary and companion names. |
| runtime-data | Partial | Typed entry-owned client/coordinator are published after first refresh. Real HA tests verify offline setup has no runtime or entities and repeated reloads replace the owner without changing entity IDs. Failed-unload/forwarding resource proof remains open. |
| test-before-configure | Partial | Host validation, pairing, fingerprint, and authentication tests exist; finish flow coverage. |
| test-before-setup | Partial | Real HA tests prove offline startup enters SETUP_RETRY without runtime or registry entities; reloading after connection recovery creates a healthy owner. Installed-host proof remains open. |
| unique-config-entry | Partial | Duplicate/identity checks exist; cover all supported discovery/manual combinations. |

## Silver

| Rule | State | Evidence or next acceptance step |
| --- | --- | --- |
| action-exceptions | Partial | API maps transport/authentication/status failures; audit every action and response-body failure. |
| config-entry-unloading | Partial | Platform unloading retains integration-wide actions; real HA tests verify successful unload rejects stale runtime data. Complete repeated reload and failure-resource proof. |
| docs-configuration-parameters | Partial | Configuration guide exists; reconcile polling and preferred-monitor settings. |
| docs-installation-parameters | Partial | HTTPS, tokens, pairing, and fingerprint approval are documented; validate instructions in HA. |
| entity-unavailable | Partial | Coordinator and capability availability exist; exercise host, service, and active-window loss/recovery. |
| integration-owner | Partial | Maintainers and issue tracker are declared; verify support and security-reporting paths. |
| log-when-unavailable | Review | Inspect one disconnect/reconnect cycle for useful non-repeating logging. |
| parallel-updates | Partial | Buttons and switches declare one parallel update per platform and entry; coordinator-state platforms declare zero. A real HA multi-button action reproduces overlapping commands before the change and verifies serialization afterward. Integration-wide actions, polling, and camera image requests are outside this semaphore. |
| reauthentication-flow | Partial | Reauth and certificate-change checks have tests; verify actual UI and credential replacement. |
| test-coverage | Gap | 214 tests pass on minimum/current HA. The preceding coverage measurement has statement coverage is 97.4% (1,240/1,273), with 88.6% branch coverage (209/236), including 100% of camera and shared error-translation behavior. Remaining meaningful module and flow paths still need qualification. |

## Gold

| Rule | State | Evidence or next acceptance step |
| --- | --- | --- |
| devices | Partial | Host device metadata exists; verify registry identity on Windows/macOS and upgrades. |
| diagnostics | Partial | Redaction/nonmutation tests pass for current host/service contracts; inspect downloaded artifacts. |
| discovery-update-info | Partial | Discovery trust/identity tests exist; verify safe address changes and recovery. |
| discovery | Partial | Zeroconf flow exists; verify advertised host platforms and unrelated-device rejection. |
| docs-data-update | Review | Explain polling, optional service inventory, preview requests, and state delays. |
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
| icon-translations | Review | Audit custom versus device-class icons and add applicable icon translations. |
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
