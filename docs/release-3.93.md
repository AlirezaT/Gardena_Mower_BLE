# v3.93 — robot error history and connection diagnostics

Stable release promoted from `v3.93.0-beta.2`, with no runtime code changes.
Release tag: `v3.93`. Manifest version: `3.93`.

## Changes since v3.92

- Robot-stored error/message history is available as attributes on the existing
  Error Code and Error Description sensors. Their current states are unchanged.
  Entries include reason, severity, raw time and app-style date/time fields.
- The diagnostic refresh reads up to 50 entries when the count/head changes and
  marks cached history stale after failed reads. The `get_error_history` action
  returns paginated history. See [usage and dashboard example](error-history.md).
- Each complete connection attempt, including pairing, is limited to 60 seconds,
  followed by existing disconnect cleanup (with its own 10-second timeout).
  Home Assistant may retry later; this does not limit the whole retry lifecycle.
- Setup/reconnect errors provide clearer Bluetooth access and pairing guidance.
  A timeout or notification refusal is not itself proof of an incorrect PIN.
- Debug logs identify the actual selected Bluetooth backend/proxy when available.
  Downloadable diagnostics redact source identities and exclude PINs and keys.

Pairing, encryption, operator authentication, mower controls and the blueprint are
unchanged from the tested beta. No bonds are erased and no firmware is changed.
The original AutoMower-BLE dependency remains pinned to upstream commit `4bf4b009`.

## Validation and limits

All 161 automated tests pass, including connection timeout, cancellation cleanup,
source diagnostics, history reads and Home Assistant version-format validation.
September 18 Minimo logs show three successful connections: one through
`light-kitchen` and two through `ble-proxy`, taking approximately 7.5–8.1 seconds
each. All report operator login, successful polling and three stored history
entries. No connection/encryption errors appear in that test window.

The earlier intermittent bonding failure was not reproduced. This is not a claim
that its root cause is repaired, or that timeout recovery has been hardware-tested.
Logs do not distinguish fresh bonds from reuse of existing bonds. Other models
and proxy combinations still need hardware validation. Error-history absolute
timestamp interpretation still needs comparison with the app.

## Installation

Install `v3.93` through HACS and restart Home Assistant. No blueprint re-import,
proxy firmware update or forced re-pairing is required. Close the Gardena phone
app when checking HA connectivity. The optional history dashboard example is not
installed automatically.
