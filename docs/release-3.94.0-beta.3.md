# v3.94.0-beta.3 — observe Start without forced reconnection

Manifest: `3.94.0-beta.3`. Stable remains `v3.93`.

## Change

After an ambiguous Start result (UNKNOWN_ERROR, DEVICE_BUSY or a lost reply),
observe fresh state on the existing connection for up to 15 seconds, checking
approximately every two seconds. Never force a recovery disconnect or replay
Start from this action. If the connection is lost, report the uncertain outcome
and leave reconnection to ordinary coordinator polling.

IN_OPERATION/CHARGING alone is not success: the mower may still be preparing
to leave, or need charging. Confirm departure/mowing or the existing accepted
pending-start state. Physical STOP, safety PIN, fatal/error and unknown-state
checks remain. Pending start with no activity remains a safety prompt.
Cancellation propagates. Explicit unsuccessful replies remain failures.

No changes to the initial connection/authentication sequence, upstream dependency,
actual mowing command sequence, SpotCut, blueprint or proxy firmware. The prior
beta's raw restriction diagnostics and firmware parsing are retained.

## Evidence and limits

Issue #11's beta.2 log shows RESTRICTED/PARKED before Start, UNKNOWN_ERROR,
then IN_OPERATION/CHARGING at 10:01:15.073 and forced recovery at 10:01:15.074.
The reporter observed a countdown followed by a reboot. This establishes an
unhelpful overlap, not proof that the integration caused a firmware crash.

Rechecked Gardena Android 9.2.0 classes5.dex:
BluetoothMower.startMowerForDuration and its nested flow emit methods use
SetMode(AUTO), SetOverrideMow and StartTrigger. The final flow catches Exception
and prints it, with no explicit disconnect/replay in that duration-start path.
The 15-second observation window is our conservative policy, not a timing copied
from the app. This is not a complete claim about the app's transport-layer retries.

176 automated tests pass. Regressions cover charging-to-departure, charging-only
uncertainty, busy responses, lost links/reads, bounded observation, cancellation,
and no command replay or forced disconnect. Changed Python passes lint and the
release tag matches the HA-compatible manifest version. City hardware validation
is still needed; this release does not claim a confirmed reboot fix.

## Comparison test (no video needed)

1. Disable the HA integration temporarily. From the dock, try one safe Start
   with the official Gardena app. Report in text whether it starts normally or
   actually reboots (display restarts/PIN prompt), rather than merely losing BLE.
   If it reboots here too, stop repeated attempts and report that result first.
2. If the app works, install this beta through HACS prereleases and restart HA.
   Close the app, enable the integration and debug logging, wait for updated
   entities, then request Start once from the dock. Wait a minute and send the
   debug log, approximate Start time and whether the mower rebooted or departed.
   Inspect the mower before any retry, even if HA reports an error.
3. If only HA still fails and an Android phone is available, capture one successful
   official-app docked Start with HA disabled: enable Bluetooth HCI snoop logging
   in Developer options, restart Bluetooth, connect with the app and note the
   action time/timezone. Take an Android bug report, then disable HCI logging.
   Availability/extraction varies by phone; tell us the phone/Android version if
   the capture is missing. No root or factory reset is requested.

Do not post raw HCI captures or full phone bug reports publicly: they can contain
PIN/authentication traffic, device identities and unrelated private information.
Arrange private sharing of the relevant capture first.

Android references: [Bluetooth capture](https://source.android.com/docs/core/connect/bluetooth/verifying_debugging)
and [bug reports](https://developer.android.com/studio/debug/bug-report).
