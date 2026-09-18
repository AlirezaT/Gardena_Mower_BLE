# v3.93.0-beta.2 — connection recovery diagnostics

Manifest version: `3.93.0-beta.2`. Stable remains `v3.92`.

- Bound each complete upstream connection attempt, including either pairing call,
  to 60 seconds. Existing disconnect cleanup has its own 10-second timeout.
  HA may retry later; this is not a limit on the entire retry lifecycle.
- Give useful setup/reconnect guidance for access/notification refusal and
  connection timeouts. These failures are not proof of an incorrect operator PIN.
  Explicit upstream INVALID_PIN responses retain their existing meaning.
- Preserve external cancellation and clean partial sessions after a failed attempt.
- Record the actual client backend and proxy/scanner identity when available,
  rather than assuming the discovery candidate is the connected proxy. An unknown
  source remains unknown; a previous attempt's source is not reused.
- Add downloadable connection diagnostics without config data, PINs, keys or
  raw backend objects. Source identifiers/names are redacted in the download.
- Retain beta.1's error-history sensor attributes and action.

No bonds are erased, no firmware is changed, and no connection-security step is
removed. The original AutoMower-BLE dependency remains pinned to `4bf4b009`.
The Gardena app and integration use separate Bluetooth clients/bonds: an app
connection does not establish that the HA proxy is authorized. This beta improves
bounded recovery and diagnosis; it is not a demonstrated firmware/bond repair.

## Install and test

Enable beta versions in HACS, install `v3.93.0-beta.2`, then restart Home Assistant.
No blueprint or proxy firmware update is needed. Close the phone's Gardena app
before testing. Confirm the normal mower entities become available and error
history still loads. No movement command is needed to test connection setup.

For proxy identification, enable debug logging for the integration, reproduce a
connection attempt, then disable debug logging. Search for `Mower connection
diagnostics`: it includes the selected source/name when the backend exposes them.
Review logs for personal information before sharing; upstream debug logs can
include protocol traffic. Connection diagnostics can also be downloaded from the
integration's menu, with source identities redacted.

A timeout identifies an unfinished connection, not its exact phase. Pairing-mode
recovery may still be needed if the mower refuses the proxy's bond. Backend fields
are best-effort diagnostics only and never drive connection or authentication.
Other mower models and proxy firmware combinations still need hardware testing.
