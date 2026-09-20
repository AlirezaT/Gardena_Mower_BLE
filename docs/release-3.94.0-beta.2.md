# v3.94.0-beta.2 — parked/start diagnostics

Manifest: `3.94.0-beta.2`. Stable remains `v3.93`.

Validation: 172 automated tests pass, including raw-code validation on both
generations, unsupported/busy responses and diagnostic privacy checks. Changed
Python files pass lint; manifest/tag validation and whitespace checks pass.
No City 500 hardware validation yet.

- Read optional Planner `GetRestrictionReason` (4658/0), as used by the
  decompiled app's parked-status path, on generation 3 and 4 diagnostic polls.
  Debug data includes `restrictionReasonRaw`; no unverified reason labels.
- Unsupported replies disable this optional read for the coordinator session;
  busy replies remain retryable and unavailable/invalid values remain unknown.
- Downloaded diagnostics include an allowlisted cached model/firmware, state,
  restriction and safety-sensor snapshot. No extra commands on download, mower
  identity or PIN export. Cached values are not necessarily current hardware state.
- Debug logs record freshly read start state/activity and each start attempt's
  result. No changes to start sequences, safety checks, SpotCut or connection
  security. Includes beta.1's start-confirmation and firmware-parser improvements.

This is a diagnostic beta for issue #11, not a confirmed start-failure fix.
Upstream pin, blueprint and proxy firmware are unchanged.

## Test

Install through HACS with prereleases enabled and restart Home Assistant. Close
the Gardena app. Enable integration debug logging, wait for a successful poll,
then request Start once when safe. Wait about a minute for further polls and
disable debug logging to download the log. If HA reports an error, check the
physical mower before retrying; it may already have started.

Send the log, downloaded integration diagnostics and the mower display's exact
message, plus whether the mower actually moved. Redact private details from logs.
Do not change firmware, bonds or proxy configuration for this comparison.
