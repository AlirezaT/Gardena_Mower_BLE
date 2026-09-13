# Complete follow-up after Minimo stable 3.90

## Current prerelease v3.92.0-beta.4 — September 13

- [x] Apply the released beta.3 duration action/accounting to the live blueprint,
  preserve inputs, back up the previous file, check configuration and reload automations.
- [x] Fix beta.3's invalid `has_service` template helper; verify the corrected
  attribute-presence condition in running HA and reload with no active mowing run.
- [x] Implement the reviewed 97-code app title catalog and independently worded
  help, including generation/guide branches and explicit unknown-code fallback.
- [x] Implement verified family-name fallback while preserving upstream variant names.
- [x] Trace message-history date/time formatters and expose their distinct app display
  fields without inventing an absolute event time; retain raw production time.
- [x] Implement and test source-preserving orientation-statistics migration tooling;
  verify a local cutoff with zero ambiguous buckets in the read-only dry run.
- [ ] Perform a stopped-HA recorder migration/restore in an agreed maintenance window.
- [ ] Physically validate automatic-run accounting, parked calendar edits, loop
  completion events and other-model behavior. No movement test was run remotely.

See [presentation evidence](app-presentation-review.md) and
[statistics repair](statistics-repair.md). These changes are included in beta.4;
literal UI/localisation parity and unverified factory-clock semantics are not claimed.
Current suite: **139 tests pass**, with scoped lint/compilation checks.

## Previous prerelease v3.92.0-beta.3

See [closure review and acceptance procedures](checklist-acceptance.md).
- [x] Hide legacy model-excluded entities without deleting history or user choices.
- [x] Separate automatic-run duration from the manual preference; preserve the
  accepted budget across restart and use it in blueprint run accounting.
- [x] Add catalog/firmware/brand capability matrix and separate outbound checks.
- [ ] Resolve historical raw pitch/roll statistics without a false unit relabel.
- [ ] Install and physically validate the new duration/visibility changes.

Beta.3 suite: **132 tests**. These additions are included in beta.3, not beta.2;
the duration fix requires an integration update and blueprint re-import.
No physical completion checks have been silently promoted to passing.

## Cross-model prerelease v3.92.0-beta.2

Release decision, 2026-09-12: owner approved **v3.92.0-beta.2 with the remaining
limitations explicitly documented**. This is not completion of every roadmap item.
Checked items below mean implemented with the stated evidence, not physically
tested on every mower. See release-3.92.0-beta.2.md for testing and limitations.

See [implementation progress](model-implementation-progress.md) for the retained,
tested changes and exact evidence. P14 catalog identities, point enable
side effects, generation-selected diagnostics, individual statistics and calendar
safeguards are now implemented in beta.2. The beta.1 section below
is historical. Unchecked broad items remain open until their full scope, including
unresolved model rules and physical-test limitations, has been reviewed.

## First implementation: v3.92.0-beta.1

The first beta implements numeric identity for the verified P0/P005/P005GA types,
model-specific sensitivity/distance/guide choices, three/five point entities and
share calculation, G3 individual point reads, firmware-selected Frost/ZoneProtect/
CorridorCut, accessory gates and stale-entity write guards. Minimo SpotCut is
unchanged. HA-valid manifest/tag notation is `3.92.0-beta.1` / `v3.92.0-beta.1`.

P14 IDs are not yet verified and are NOT inferred from a default case. G3 point
enable controls are withheld pending their full app side effects. Diagnostics,
actions and calendar work remain outstanding. This beta is not completion of
the original request for every item; all unchecked items below remain tracked.

Owner decision, 2026-09-12: release the Minimo corrections first, then implement
**all** audited model dependencies in a separate version. No version number has
yet been assigned to that follow-up. Final 3.90 naming is manifest `3.90`, tag
`v3.90`. Never silently change the owner's requested version format.

## Evidence and implementation principles

The [model audit](model-dependency-audit.md) contains the exact branches, command
IDs, firmware boundaries and all 89 original entity rows. The
[entity audit](entity-protocol-audit.md) retains wire-layout and behavior findings.
Read both before implementing; this checklist is an index, not a replacement.
Raw APKs, snoop logs, screenshots and device identifiers must remain private.

- [x] Centralize capabilities using verified device type, variant, generation,
  firmware and runtime availability. Keep unknown identity conservative.
- [x] Identify P0 (city/life; related ROB S/EasiLife), P005 (Minimo/EasiLife Go),
  P005GA (flex), P14 (pro/max). Confirm accepted P14 IDs rather than classifying
  every unknown type, or arbitrary Husqvarna model, as P14. Accepted P14 pairs:
  34/{1,2,4}, 35/{1,2,3,7,8,9}, 36/{1}, 37/{1,2,3}; this does not resolve brand rules.
- [x] Distinguish app UI visibility, proven protocol support and physical tests
  in the audit and implementation-progress document.
  A missing app diagnostic is not proof that the hardware cannot provide it.

## Model-dependent controls — implement all

- [x] SensorControl rules: P0/P005 values 1/2/3; P005GA/P14 values 0/1/2/3/4.
  P14 activation is restricted to the verified catalog pairs above.
  Preserve the wire meanings; do not renumber by UI index.
- [x] Starting points: 3 versus 5; expose points 4/5 where supported and include
  every enabled point in the charging-station remainder calculation.
- [x] Starting-point reads: G3 individual fields versus G4 combined layouts.
- [x] Starting-point enable side effects: verified G3/G4 repeated enabled writes,
  clear proportion on disable, stop on failure and verify read-back.
- [x] Starting-point distance editor and write guards: P0 1–300 m, P005 1–100 m,
  P005GA/P14 1–500 m, traced through EditDistanceScreenKt's platform branches.
- [x] Guide/boundary choices: single guide, flex two-guide arrangement, Gardena
  P14 boundary plus two guides and Flymo P14 boundary plus one guide. P14 requires
  explicit brand confirmation in integration options; unknown stays disabled.
- [x] Drive Past Wire range rules: P0 20–40, P005/P005GA 20–35, P14 25–40 cm.
- [x] Station starting distance: P0 20–300, others 60–300 cm; preserve mm scaling.
- [x] Garage visibility: absent from P14 app capability, present on others.
- [x] Radar: P14 plus availability; never confuse it with ZoneProtect.
- [x] Frost firmware group selection: P0 boundary 20.28; preserve read/write
  pairing. App help text uses 3°C for P14, 5°C otherwise, not a writable threshold.
- [x] ZoneProtect and CorridorCut: P0 main-version-prefix boundary 41; validate
  version parsing, short/malformed versions and unknown behavior. Never probe writes.
- [x] McCulloch Frost UI exclusion; other brand rules remain under their entries.

## Diagnostics, actions and calendars

- [x] G3/G4 battery voltage/current/temperature behavior; never expose the app's
  999999 sentinel as a real measurement.
- [x] G3 Comboard versus G4 collision/lift/orientation commands and unit scaling.
- [x] G3 legacy versus G4 modern loop reads; G4 averages front/rear strength.
- [x] P14 second-guide diagnostics follow the confirmed brand/guide profile;
  unconfirmed P14 profiles do not expose a guessed second or third guide.
- [x] Individual statistics reads independent of optional aggregate blade data;
  unavailable aggregate data does not suppress the six individual statistics.
- [x] Review all remaining hardware/software/error/message entities: see the
  [89-row implementation review](entity-implementation-review.md). Extra diagnostics
  without app availability evidence remain optional runtime reads, not inferred
  capabilities. No reset/write is used to probe support.
- [x] Retry transient/malformed diagnostic reads; cache genuinely unsupported
  commands separately instead of permanently disabling on any failure.
- [x] Next-start timestamps use the target date's timezone offset; nonexistent
  or ambiguous DST wall times and sentinels stay unknown, with regression tests.
- [x] P14-specific short error 38 label and verified platform/type/variant fallback
  where upstream has no marketing name. Production/message timestamps explicitly
  remain raw; no unverified UTC claim is made.
- [ ] Full manufacturer troubleshooting-text and marketing-name parity; exact
  production/message clock interpretation. Conservative fallbacks are implemented,
  but this is not completion of these original broad checklist items.
- [x] Pause command-result checking and dock/pause connection-failure propagation.
- [x] Permanent park: G3 HOME/start, G4 HOME/clear override/start; each reply
  checked. Dock resume and schedule-resume failures now propagate too.
  Post-beta.4: ambiguous park trigger replies require fresh HOME/state/activity
  confirmation; see [reply fix evidence](permanent-park-reply-fix.md).
  Owner reported Minimo controls working on September 13; the 18:23–18:25
  Start/Park test had no new control errors and SpotCut stayed off. Other-model
  physical confirmation remains pending. Stable 3.92 promotes beta.5 unchanged.
- [x] SpotCut G3 uses pause/AUTO/300-second override/14-20/start and 14-24 stop;
  other G4 uses pause/AUTO/4710-7/start and 4710-8 abort. Minimo/P005 retains the
  tested upstream sequence. P14/flex require positive 4710-0 availability.
  G3 IDLE/ACTIVE status is normalized separately from the G4 four-state enum.
  **Preserve the owner's tested Minimo sequence unless an evidenced improvement
  justifies a change; do not add a pause merely to copy the app workflow.**
- [x] SpotCut restore: expired manual override must not create extra mowing time;
  restoring scheduled activity must not invent a manual override. Test separately
  from the working start/stop sequence. Remaining duration is captured using
  mower-clock timestamps and then monotonic elapsed time, not host timezone.
  Unknown timing grants no new mowing allowance. Scheduled activity restores
  the planner, not a manual override; redundant park-resume command removed.
- [x] Calendar G3/G4 capacities (14/15), G3 two-per-day and conservative rejection
  of last-entry deletion. No unverified G3 placeholder schedule is fabricated.
- [x] Calendar failed reads must not become empty calendars before replacement.
- [x] Calendar edits send no mode/override/start commands; validate replies,
  partial failures, cancellation, concurrent edits and read-back. An uncertain
  write blocks retries pending app verification and integration reload.
- [ ] Physically validate calendar edits while permanently parked; fake-transport
  tests establish command behavior, not end-to-end mower state preservation.
- [x] Use the 15-byte app AddTask layout for confirmed generations, with tests;
  Minimo snoop evidence and other-generation static evidence are distinguished.
- [x] Loop generation: retain 4692/2; wait for success/failure events 4692/2,1.
  Validate channel and checksums; handle fragmented/coalesced frames, timeout,
  disconnect and cancellation. Unconfirmed completion raises an error, not success.
- [x] Validate frame reassembly against 3,409 captured linked frames (27,272 checks).
  Keep-alives continue during the pairing wait, with a regression test. No actual
  completion event is present in the capture; physical event confirmation is open.

## Verification and release

- [x] Automated catalog/firmware-boundary matrix, unknown identities and unavailable
  reads, with decoder and outbound-command coverage kept separate. Physical
  platform/firmware certification remains under the next item, not implied here.
- [ ] Physical tests only on available models, with explicit user coordination;
  do not remotely start a mower simply to validate a command.
- [x] Update README and document draft scope/remaining work. No blueprint code
  changed and these changes do not require a blueprint re-import.
- [x] Review blueprint separation: demand uses configured area/effective capacity
  plus rain/irrigation inputs. Do not infer daily allowances from shared BLE platform
  identity. Functional demand/calibration settings are unchanged; source comment added.
- [x] Retain the original upstream library pin with narrow integration adapters.
- [x] Recheck upstream main: still 4bf4b00959f9ef712b5e1beebd725b0c75c80637;
  tested immutable dependency unchanged. No unpinned automatic updates.
- [x] Validate HA's version parser, exact planned tag/manifest agreement and release
  archive: `v3.92.0-beta.2` / `3.92.0-beta.2`; no raw captures, APKs or firmware.
- [x] Review all 89 audit rows; see entity-implementation-review.md. This does not
  turn runtime-only support evidence into physical all-model validation.

Latest local verification: 123 automated tests pass, scoped Ruff checks pass,
and `git diff --check` passes. Minimo's underlying start/stop command sequence
remains delegated to upstream; the restore logic has intentionally changed.
The installed integration and upstream dependency pin are unchanged; the release
manifest is `3.92.0-beta.2`, matching tag `v3.92.0-beta.2`. These
checks do not close the unchecked implementation or physical-validation items.
