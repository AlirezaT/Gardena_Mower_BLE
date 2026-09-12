# v3.92.0-beta.2 — cross-model testing prerelease

Manifest: `3.92.0-beta.2`. GitHub/HACS tag: `v3.92.0-beta.2`.
Stable remains `v3.91`. This beta is approved for testing with the limitations
below; it is not a claim that every model has been physically validated.

## Changes since beta.1

- Verified P14 type/variant profiles and an explicit Gardena/Flymo brand option
  for P14 guide choices. Unknown identities remain conservative.
- App-derived starting-point distance limits: P0 1–300 m, Minimo/P005 1–100 m,
  flex/P14 1–500 m. Point disabling now clears its mowing share, with checked
  repeated writes and read-back, matching the app.
- Generation-specific diagnostics and checked park, pause, resume and SpotCut
  actions. Optional reads retry transient failures; unavailable values stay unknown.
- Preserve Minimo's tested underlying SpotCut start/stop sequence. Restore logic
  no longer grants a fresh mowing allowance after an expired manual override.
- Safer calendar writes: model-specific capacities, conflict detection, checked
  transactions and read-back. No start/mode/override commands during calendar edits.
  An uncertain write blocks retries until app verification and integration reload.
- Loop generation waits for validated completion/failure events, with fragmented
  frame handling, keep-alives and a clear timeout instead of assumed success.
- Conservative DST handling for next-start time; production/message timestamps
  remain raw where clock semantics are unverified. P14-specific error 38 label.
- README, all 89 entity review rows and the implementation checklist updated.
  Blueprint change is a source comment only: no mowing-demand calculation change
  and no blueprint re-import required.

## Dependency and verification

Still uses the original `alistair23/AutoMower-BLE`, pinned to tested commit
`4bf4b00959f9ef712b5e1beebd725b0c75c80637`, not a fork or PR branch.

123 automated tests pass, plus scoped Ruff, compilation and diff checks.
The private Minimo capture passed 27,272 fragmentation/coalescing checks over
3,409 linked frames. No raw capture or device credentials are included.
These checks use protocol fixtures/fake transport, not full HA/mower end-to-end tests.

## Known limitations

- Other-model physical tests, calendar editing while permanently parked and
  physical loop-completion event confirmation remain outstanding. The capture
  contains no pairing-completion event; that path has synthetic/static evidence.
- Exact marketing names, full model-specific app troubleshooting text and
  production/message clock interpretation remain incomplete, with explicit fallbacks.
- P14 guide choices require brand confirmation in integration options. A shared
  platform identity does not establish lawn capacity or daily mowing allowance.
- G3 last-calendar-entry deletion is rejected; no guessed placeholder is written.

## Testing and rollback

1. Back up Home Assistant, and record the mower's calendar/settings in the app.
2. Enable prereleases in HACS, select `v3.92.0-beta.2`, and restart Home Assistant.
3. Start with read-only checks: model profile, entities, diagnostics and calendar.
   On P14, confirm the brand before using guide selection.
4. Test settings one at a time with app read-back. Disabling a starting point
   intentionally clears its share. Test movement only with the mower supervised
   in a safe area. Do not regenerate the loop merely as a routine upgrade check.
5. If a calendar write is uncertain, inspect/correct it in the app before reloading
   the integration and retrying. Do not assume an error rolled the changes back.

To roll back, select `v3.92.0-beta.1` or stable `v3.91` in HACS and restart HA.
Rollback changes integration code, not mower settings; verify those in the app.
Publishing this release does not install it or change proxy firmware.
