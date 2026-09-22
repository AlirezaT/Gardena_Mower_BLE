# v3.94.0-beta.6 — Configure parking before resuming a paused mower

Manifest: `3.94.0-beta.6`. Stable remains `v3.93`.

## Fix

Issue #11's beta.5 log shows Pause succeeding, then Dock sending StartTrigger
while the three-hour mowing override is still active. Only afterward does it
send the parking override; the next poll reports MOWING with FORCEDPARK.

Dock now sends SetMode(AUTO), SetOverrideParkUntilNextStart, then StartTrigger
as one serialized command sequence. It never sends a preliminary resume and
does not replay the trigger. Rejected preparation stops the sequence. Fresh
STOP/PIN/error state blocks the command; an unknown model or malformed schedule
count cannot select a speculative parking path.

After an OK or UNKNOWN_ERROR trigger reply, Dock observes fresh mode, override,
state and activity for up to 15 seconds. Scheduled parking requires AUTO plus
FORCEDPARK and returning/parked/charging activity in an operational/restricted
state. Explicit trigger rejections remain failures. Unconfirmed outcomes report
uncertainty rather than silently claiming success. Each sample is serialized;
the lock is released between samples so other controls can proceed. There is no
action-level reconnect/replay; underlying transport cleanup can still disconnect
a failed or timed-out session.

The HA Dock action no longer injects optimistic GOING_HOME; the normal refresh
publishes actual mower readings, including after uncertain/failed attempts.

## City versus Minimo

The retained app's ParkMowerHomeUntilNextScheduledUseCase and
BluetoothMower.parkUntilNextSchedule have no P0/P005 branch: the scheduled park
sequence is shared. The fix therefore applies to recognized G3/G4 models,
including P0 City and P005 Minimo. Older firmware or a different starting state
may explain differing symptoms, but that is not established by this log.

Permanent parking is different: G3 uses HOME then StartTrigger; G4 uses HOME,
ClearOverride, then StartTrigger. Those sequences and the no-calendar fallback
are retained. The standalone permanent-park control, working timed Start,
Minimo SpotCut, schedules, blueprint, proxy firmware and upstream pin are unchanged.
Other existing callers of mower_park (including SpotCut restoration) use the
corrected parking method too; the SpotCut start/stop sequences are unchanged.

## Validation and test

205 automated tests pass, including exact parking order across all recognized
type families, three-hour Start/Pause/Dock, no-calendar G3/G4 paths, rejected
preparation, safety states, delayed/failed/ambiguous read-back, cancellation,
poll serialization and unchanged Start/SpotCut regressions. Tag/manifest
compatibility, changed-code lint and whitespace checks pass. Hardware confirmation
of the corrected Dock behavior is still needed on City and Minimo.

Install beta.6 in HACS and restart HA; no re-pair or proxy flash is needed. Close
the phone app and enable integration debug logging. When safe, try one normal
Start, Pause, then Dock; note times and whether it returns without resuming
mowing. Do not repeatedly press Dock if the result is uncertain: inspect the
mower first. Share the full log through the next polls, retaining state/activity,
override action, command results/timings and Dock read-back lines. Redact private
identifiers. A short normal-use log does not validate the separate history issue;
keep logging for 10–15 minutes if also investigating history refresh delays.
