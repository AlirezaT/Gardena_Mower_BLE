# App presentation implementation review — September 13

Included in beta.4, continuing after beta.3. No new integration code is installed by
this review. The live blueprint received the beta.3 action and accounting changes,
plus the runtime capability-check correction below, and was reloaded; its other
logic and the user's automation inputs were preserved. The previous blueprint
is backed up alongside the installed file with suffix `.pre-beta3-20260912`.

## Live blueprint correction and verification

The published beta.3 blueprint used `has_service`, which is not a Home Assistant
template helper. A direct read-only template evaluation caught this despite the
earlier mocked test passing. The new condition checks integration membership and
the presence (not value) of the mower's `last_start_duration_hours` attribute,
introduced alongside the per-run action. Older integrations retain the legacy path.
The regression test no longer invents a `has_service` helper.

The corrected condition evaluated True in running HA. Automations were reloaded
with zero active runs of the mowing automation; it remains enabled, the mower
remains docked and Manual Mowing Duration remains 3 h. No start, calendar write,
loop-generation or safety-setting command was sent. The new runtime check is
already applied locally, but is NOT present in the immutable published beta.3 tag.

Current automated verification: **139 tests pass**, scoped Ruff and compilation
checks pass. Tests still do not replace physical mower acceptance.

## Error descriptions and help

Retained app 9.2.0 DEX evidence: `ErrorDescriptionHelper.getErrorBannerTitle`,
`getBody`, `getHint`, its Kotlin platform switch mapping, and English resources.
The reviewed branches contain 97 explicit title codes, 87 body comparison values
and 46 hint comparison values. A bounded offline path walker selected each code
for P0/G3, P005/G4, flex/G4, and one-/two-guide P14/G4. Coroutine repository reads
were represented by the chosen profile; no app or mower command was executed.
Unknown branches are not classified as supported mower capabilities.

`error_help.py` implements the reviewed titles and independently worded guidance,
not copied app code, UI widgets or an exact translation of every app paragraph.
Long help is exposed as attributes rather than exceeding HA's state-length limit.
The guidance does not send commands, disable protections, change wiring or reset
pairing. Physical repair instructions defer to the model manual, particularly
slope limits, blade/battery service, PIN recovery and electrical work.

Verified presentation differences:

- Codes 51/52 have numbered guide labels only with a confirmed two-guide profile.
  Unknown P14 brand stays generic. An error label does not create a third-guide control.
- Error 2 includes the G3 Security-menu loop-setup route; generation 4 uses the app.
- Acknowledgement hints differ between G3 acknowledgement and G4 physical STOP.
  Error 12 has no such G3 hint.
- Synthetic app statuses 1000001/1000002/1000003 receive local PIN/safety-stop
  guidance, without substituting a guessed factory PIN or sending a start.
- The existing P14 error-38 short-label correction remains.
- Informational messages and unknown codes do not become recovery commands.

## Model names

`shared_ui.util.ExtentionsKt.getModelName` supplies family labels, not an exact
variant/area catalog. Type 14 maps to city/life, 18 to life, 29 to minimo and 43
to flex. Its packed-switch maps 34/36 to pro and 35/37 to max. The P14 Gardena
labels are used only after brand confirmation; Flymo/unknown stay conservative.
Known upstream variant names are preserved. Numeric type/variant remains in
fallback labels, and no square-metre rating or daily allowance is invented.

## Message dates versus absolute time

`BluetoothMower.getSpecificMessage` transfers the device time unchanged into
`MowerError`. `ErrorHistoryViewModel.getNextChunk` transfers it to the history
item. `ErrorHistoryScreenKt.ErrorItem` calls `ExtensionsKt.getDateString` and
`getTimeString`: both multiply by 1000, but the date formatter keeps the phone's
default timezone while the time formatter explicitly selects UTC.

The integration now exposes `app_date` (ISO date in HA's configured timezone)
and `app_time_24h` (UTC-formatted raw seconds), retaining raw `time` and an explicit
semantics warning. The phone and HA zones must match for matching date display.
This implements those display paths without falsely claiming a validated absolute
event timestamp, particularly around midnight or DST. Invalid/sentinel values
do not acquire fabricated dates. The current-error banner may substitute phone
time when its code does not match the latest stored message; it is not calibration evidence.

## Production time and validation limits

The production-time response is a raw T_UNIX_TIME long. No verified app display
or factory timezone was established. It stays an explicitly raw diagnostic.
Software cannot determine missing factory semantics or physically validate another
mower model. Exact translated UI/text parity, unverified marketing capacities and
absolute factory/event clock interpretation are not claimed by these additions.
