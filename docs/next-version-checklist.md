# Complete follow-up after Minimo stable 3.90

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
- [ ] Cover P0 (city/life; related ROB S/EasiLife), P005 (Minimo/EasiLife Go),
  P005GA (flex), P14 (pro/max). Confirm accepted P14 IDs rather than classifying
  every unknown type, or arbitrary Husqvarna model, as P14.
- [ ] Distinguish app UI visibility, proven protocol support and physical tests.
  A missing app diagnostic is not proof that the hardware cannot provide it.

## Model-dependent controls — implement all

- [x] SensorControl rules: P0/P005 values 1/2/3; P005GA/P14 values 0/1/2/3/4.
  P14 activation remains blocked on identity verification.
  Preserve the wire meanings; do not renumber by UI index.
- [x] Starting points: 3 versus 5; expose points 4/5 where supported and include
  every enabled point in the charging-station remainder calculation.
- [ ] Starting-point reads/writes: G3 individual fields versus combined layouts;
  implement G3 enable side effects and complete distance-editor validation.
- [ ] Guide/boundary choices: single guide, flex two-guide arrangement, Gardena
  P14 two-guide arrangement and distinct Flymo P14 rules. No universal enum list.
- [x] Drive Past Wire range rules: P0 20–40, P005/P005GA 20–35, P14 25–40 cm.
- [x] Station starting distance: P0 20–300, others 60–300 cm; preserve mm scaling.
- [ ] Garage visibility: absent from P14 app capability, present on others.
- [ ] Radar: P14 plus availability; never confuse it with ZoneProtect.
- [ ] Frost firmware group selection: P0 boundary 20.28; preserve read/write
  pairing. App help text uses 3°C for P14, 5°C otherwise, not a writable threshold.
- [x] ZoneProtect and CorridorCut: P0 main-version-prefix boundary 41; validate
  version parsing, short/malformed versions and unknown behavior. Never probe writes.
- [x] McCulloch Frost UI exclusion; other brand rules remain under their entries.

## Diagnostics, actions and calendars

- [ ] G3/G4 battery voltage/current/temperature behavior; never expose the app's
  999999 sentinel as a real measurement.
- [ ] G3 Comboard versus G4 collision/lift/orientation commands and unit scaling.
- [ ] G3/G4 loop strength/components; G4 app averages front/rear strength.
- [ ] Individual versus aggregate statistics layouts and runtime support.
- [ ] Audit every remaining hardware/software/error/message entity against its
  model, generation and available evidence; unresolved rows stay explicitly open.
- [ ] Error text/model-name completeness, timestamp/DST handling and retryable
  diagnostic errors versus genuinely unsupported commands.
- [ ] Permanent-park action differences and confirmed failure propagation.
- [ ] SpotCut G3/G4 command/status differences and conflicting capability helpers.
  **Preserve the owner's tested Minimo sequence unless an evidenced improvement
  justifies a change; do not add a pause merely to copy the app workflow.**
- [ ] SpotCut restore: expired manual override must not create extra mowing time;
  restoring scheduled activity must not invent a manual override. Test separately
  from the working start/stop sequence and explain proposed behavior changes.
- [ ] Calendar G3/G4 capacities (14/15), G3 two-per-day and last-entry handling.
- [ ] Calendar failed reads must not become empty calendars before replacement.
- [ ] Calendar edits should preserve permanent parking; validate command results,
  partial transaction failures, concurrency and read-back before claiming safety.
- [ ] Resolve 15-byte app AddTask versus upstream padding by model, with tests.
- [ ] Loop generation: retain 4692/2; distinguish accepted command from completed
  pairing using success/failure events. Do not restore the unrelated fallback.

## Verification and release

- [ ] Test each platform/firmware boundary, unknown identities and unavailable
  features. Keep decoder and outbound-command regression coverage separate.
- [ ] Physical tests only on available models, with explicit user coordination;
  do not remotely start a mower simply to validate a command.
- [ ] Update README and blueprint documentation if capability changes affect it.
  Review daily operating limits separately; capacity variants need not share them.
- [ ] Retain the original upstream library with narrow integration adapters where
  needed; reassess upstream status explicitly, not via unpinned automatic updates.
- [ ] Validate HA's version parser, exact tag/manifest agreement and release archive.
- [ ] Review all 89 audit rows before marking cross-model work complete.
