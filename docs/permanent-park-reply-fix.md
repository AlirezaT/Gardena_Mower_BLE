# Permanent park reply handling (after beta.4)

The September 13 Minimo logs show StartTrigger returning UNKNOWN_ERROR while
subsequent telemetry reports HOME / RESTRICTED / PARKED. Beta.4 incorrectly
treated the ambiguous reply as definitive failure, without checking the outcome.

Rechecked against the supplied GARDENA Bluetooth 9.2.0 app DEX:

- `ParkMowerPermanentlyUseCase.execute`: passes false for generation 3 and true
  otherwise to `BluetoothMower.parkPermanently`.
- `BluetoothMower.parkPermanently`: false sends HOME + StartTrigger; true sends
  HOME + ClearOverride + StartTrigger. No Minimo-specific exception here.
- Request constructors confirm SetMode = 4586/0 (uint8), ClearOverride = 4658/6,
  StartTrigger = 4586/4. The upstream wire definitions match.

Therefore retain these sequences for recognized G3/P0 and G4/P005 (Minimo),
P005GA and P14 identities. Unknown generations remain unavailable.
The correction is reply handling, not removing the app's StartTrigger.

Only after successful preceding writes and an UNKNOWN_ERROR trigger reply,
wait two seconds and read GetMode, GetState and GetActivity under the action
lock. Require successful fresh replies reporting HOME, IN_OPERATION or
RESTRICTED, and GOING_HOME, PARKED or CHARGING. Otherwise preserve the error.
No command is retried, no cached values prove success, and other errors are
not suppressed. This is an integration safeguard analogous to the pinned
upstream's mowing-trigger readback, not a claim that the app uses this check.

Tests cover all recognized device types, successful and rejected readbacks,
failed preceding writes and preservation of Minimo's tested SpotCut sequence.
Hardware confirmation of this fix remains pending; no commands were sent to
the mower during development. Packaged in v3.92.0-beta.5; publication does not
install the fix in Home Assistant.
