# v3.94.0-beta.4 — P0 timed Start aligned with the app

Manifest: `3.94.0-beta.4`. Stable remains `v3.93`.

Validation: 182 automated tests pass, including exact P0 command order/duration,
rejected preparation, ambiguous trigger confirmation, cancellation/lock release
and unchanged delegation for other platforms. Changed Python passes lint;
manifest/tag compatibility and whitespace checks pass.

## Changes

- On P0 mowers, timed Start now sends SetMode(AUTO), SetOverrideMow(duration
  in seconds), then StartTrigger. It no longer sends preliminary ClearOverride.
  This matches the examined Gardena Android 9.2.0 timed-start path; the app uses
  ClearOverride separately when resuming the schedule.
- Keep the entire command sequence serialized and stop if mode/duration is
  rejected. Log command names, results, exception types and elapsed time, without
  authentication or raw packet payloads.
- Preserve upstream's existing StartTrigger state-confirmation timing and
  beta.3's bounded observation without action-level reconnect/replay. Underlying
  transport-error cleanup may still disconnect a failed session.
- Non-P0 timed Start, Minimo SpotCut, park/schedule actions, safety checks,
  blueprint, proxy firmware and pinned upstream dependency are unchanged.

## Evidence and limitations

Issue #11 reports that the official iPhone app's three-hour Start works but HA
can trigger a countdown/reboot. Later, a second HA Start reportedly worked while
the displayed state stayed docked until reload. The latest anonymized excerpt
shows successful polls with GOING_HOME/FORCEDPARK and omits the Start commands
and reload; it does not establish the cause of the stale display.

The command difference is confirmed against the Android app, not an iOS HCI
capture. Removing it is a controlled compatibility test, not proof of a reboot
fix. No speculative polling fix is included. Physical P0 validation is pending.

## Test

Install through HACS prereleases and restart HA. Close the official phone app,
enable integration debug logging before any action and wait for entities to
update. Request one safe three-hour Start from the dock. Note the exact action
time, whether it rebooted or started, and whether HA's state follows the mower.
Check the physical mower before retrying; do not repeatedly trigger a reboot.

If state gets stuck, download integration diagnostics before reloading. Keep
debug logging enabled through the reload and a subsequent poll, then download
the full log. Preserve timestamps, command/state lines and errors; redact private
identifiers rather than shortening/reordering the log. No HCI capture or video
is required for this test.
