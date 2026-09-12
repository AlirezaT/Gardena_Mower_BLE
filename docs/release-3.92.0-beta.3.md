# v3.92.0-beta.3 — feature visibility and independent run duration

Manifest `3.92.0-beta.3` matches GitHub/HACS tag `v3.92.0-beta.3`.
This is a testing prerelease; stable remains `v3.91`.

## Changes since beta.2

- Hide retained model-excluded entities without deleting IDs/history or changing
  user-hidden/disabled choices. Omit unsupported radar/garage diagnostics on new
  setups. Unknown model identity and transient BLE failures do not hide features.
- Minimo/P0: hide radar, starting points 4–5 and guide 2–3 signals. Flex: hide
  radar and guide 3. P14: hide garage and guide 3; Flymo P14 also guide 2.
  Type 22 additionally excludes Frost. Minimo keeps ZoneProtect, Frost,
  Avoid Garage, SpotCut and normal collision detection (separate from radar).
- Add `gardena_mower_ble.start_mowing_for`, targeting a mower entity with
  `duration_hours` in half-hour steps from 0.5 to 24. It does not overwrite the
  saved Manual Mowing Duration. Ordinary Start continues using that preference.
- Persist the accepted run budget as mower attribute `last_start_duration_hours`.
  Failed starts do not update it. Blueprint run accounting uses the accepted
  budget instead of the manual preference; legacy integrations retain fallback.
- Extend regression coverage and update README, checklist and acceptance procedures.
  The full checklist is not closed.

## Install and update the blueprint

1. Back up Home Assistant and the current automation/blueprint.
2. Enable prereleases in HACS, select `v3.92.0-beta.3`, and restart Home Assistant.
3. Re-import this exact tagged blueprint, preserving your existing automation inputs,
   and reload automations:
   [beta.3 Gardena Smart Mowing blueprint](https://raw.githubusercontent.com/AlirezaT/Gardena_Mower_BLE/v3.92.0-beta.3/blueprints/automation/gardena_smart_mowing.yaml).
   The main-branch URL may contain an older blueprint. HACS integration updates
   do not update imported blueprints automatically.
4. Verify model visibility and the saved manual duration without starting the mower.
   During the next normally scheduled, supervised run, compare its requested budget
   with the mower attribute and app; the manual preference should stay unchanged.

The duration fix requires BOTH integration and blueprint updates. Keeping the old
blueprint will continue overwriting the manual number. No growth-rate/area/daily
allowance calculation or tested Minimo SpotCut command sequence is changed here.
Hidden legacy entries remain visible in entity management; history is retained.

## Verification and known limitations

132 automated tests pass, including 600 catalog/firmware/brand capability cases
and 200 separate outbound-profile cases, plus lint and compilation checks.
Tests use fixtures/fake transport, not full HA or physical all-model certification.
Original `alistair23/AutoMower-BLE` dependency remains pinned to
`4bf4b00959f9ef712b5e1beebd725b0c75c80637`; no fork or PR branch is substituted.

Still open: full manufacturer troubleshooting/variant-name parity, exact
production/message clock interpretation, physical loop-completion and parked-calendar
validation, other-model hardware tests and new-code live acceptance.
Pitch/roll history repair is also open: old samples are raw tenths of a degree;
merely relabelling them as degrees would be incorrect. Recorder data is untouched.
See [acceptance procedures](https://github.com/AlirezaT/Gardena_Mower_BLE/blob/v3.92.0-beta.3/docs/checklist-acceptance.md).

## Rollback

Select beta.2 (`v3.92.0-beta.2`) or stable `v3.91` in HACS and restart HA.
The new blueprint falls back to the legacy start path when the new action is absent,
which again changes the manual duration. Restore your backed-up blueprint if desired.
Integration-hidden legacy registry entries may stay hidden after rollback; reveal
them manually in entity management if needed. No mower settings/history are reverted.
Publishing this release does not install it, restart HA or modify proxy firmware.
