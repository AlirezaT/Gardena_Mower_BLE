# Checklist closure review — September 12, 2026

This accompanies beta.4, not an all-items-complete claim. The installed integration,
mower settings and recorder data were not changed during release preparation.
The live blueprint now uses the corrected duration-action/accounting path; see
[current presentation review](app-presentation-review.md) for verification and
[statistics repair](statistics-repair.md) for the prepared offline-copy tool.

## Inherited from beta.3

- Unsupported entity migration: hide legacy model-excluded entities, preserve
  IDs/history/user choices; suppress new unsupported diagnostics.
- Separate per-run start duration from the manual preference. Explicit accepted
  start budgets persist in options and are exposed on the mower. Failed starts
  do not update the budget. Blueprint accounting reads that budget, with fallback
  for old versions/other integrations. Blueprint re-import is required for this fix.
- Catalog matrix: 20 explicit type/variant profiles, ten firmware boundary/invalid
  inputs and three brand choices (600 capability combinations). Separate outbound
  tests exercise bounds, sensitivity and command-group pairs on 200 combinations.
  Existing diagnostic, unavailable-read and protocol-serialization tests remain.
- 132 automated tests pass. These are not physical all-model certification.

## App investigation: evidence and limits

Revisited retained app 9.2.0 classes4.dex/classes5.dex and command Java sources.
No proprietary source or raw captures are copied into this repository.

- `HwInfoCommands.GetProductionTimeResponse` returns the raw T_UNIX_TIME long.
  That declaration alone does not establish the factory clock's timezone. Keep
  production time raw until an independently dated factory record or a confirmed
  display conversion resolves it; do not modify the production time to test it.
- `BluetoothMower$getSpecificMessage...emit` transfers the response time directly
  into `MowerError`. `GetErrorUseCase.getTimeStamp` uses that value for a matching
  latest message, otherwise substitutes the phone's current epoch seconds. This
  is not proof that every historical device timestamp uses UTC. A screenshot of
  the current-error banner alone can therefore give misleading confirmation.
- `shared_ui.util.ExtentionsKt.getModelName` is a family-label lookup, not an
  exhaustive variant/capacity table. Keep known upstream names; do not infer a
  model's area/daily allowance from this family label.
- `ErrorDescriptionHelper` has separate title, body and hint paths; the body
  contains 2,651 DEX instructions and the hint 205. The reviewed short error-38
  correction does not establish full manufacturer troubleshooting-text parity.
The beta.4 presentation review supersedes this earlier open mapping status:
reviewed titles and independently worded model-aware guidance are now implemented.

## Required acceptance evidence

Run these only after the new code is released/installed. Do not replay BLE packets.
Do not bypass Frost, ZoneProtect, physical STOP or safety-PIN restrictions.

### Manual preference and automatic run budget

Record the manual value (for example 3 h). During a normally scheduled, supervised
run with a different planned duration, verify the manual value remains unchanged,
the mower attribute records the requested budget, and the app shows the requested
override. After the run, reload/restart and check both saved values. Confirm the
blueprint's early-stop accounting uses the run budget, not the manual preference.

### Calendar while permanently parked

Back up the actual device calendar in the app. With the mower safely docked and
permanently parked, edit a future schedule in HA. Verify read-back, mode remains
HOME/permanent park, and no start/clear-override command or movement occurs.
Restore the original schedule and verify again. Do not run this remotely without
someone at the mower; a safe future schedule is required. Stop if a write becomes
uncertain; inspect the device calendar before any retry.

### Loop completion

Existing capture proves request acceptance but contains no completion event.
No routine regeneration is requested. During a separately agreed, necessary
supervised pairing operation, capture the completion/failure event and compare
the UI result. Never manufacture a failure by changing wiring or safety sensors.
Until captured, label completion handling synthetic/static-tested only.

### Other models

For each available P0, flex and P14 unit, record numeric profile and firmware;
compare read-only controls/diagnostics with its app. Then, only with the owner's
approval, round-trip ordinary settings one at a time and restore them. Real
devices are needed to close physical cross-model validation.

### Orientation statistics

Old raw values require a 0.1 scale factor, not just a unit rename. HA's normal
unit-conversion API cannot convert unitless raw values to degrees automatically.
Retain the database unchanged for now. Before repair, inspect the actual retained
statistics and back up: choose a reviewed, date-aware migration preserving the
old history, or archive it and start a new degree series. Do not erase statistics
or silently rewrite old readings just to clear the warning. This item remains open.

## What still prevents closing the whole checklist

Literal app UI/localisation parity and unverified marketing capacities are not
claimed. Absolute factory/event clock semantics, applying the orientation-history
repair, live new-code acceptance and the physical tests above remain open.
Beta.4 uses manifest `3.92.0-beta.4` and tag `v3.92.0-beta.4`.
No existing release/tag is modified.
