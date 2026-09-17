# v3.93.0-beta.1 — Robot error history

- Adds up to 50 robot-stored messages as attributes on the existing Error Code
  and Error Description entities, without changing their current states.
- Entries include code, reason, severity, raw timestamp and available app-style
  date/time. The latest stored message is separate from the current error.
- Checks the history head/count during five-minute diagnostics; fetches the list
  when changed and keeps the last complete list marked stale after read failures.
- Adds the read-only `gardena_mower_ble.get_error_history` action with pagination.
- Includes an optional dashboard list example in [error-history.md](error-history.md).

Install through HACS with beta versions enabled, then restart Home Assistant.
Allow the first diagnostic refresh to complete. Check the error entity's
`error_history` and `error_history_status` attributes, then compare entries with
the Gardena app. Close the app before expecting HA to reconnect to the mower.
No blueprint changes or automatic dashboard changes are included.

Manifest `3.93.0-beta.1` matches tag `v3.93.0-beta.1`. Based on stable v3.92;
upstream dependency pins, mower control sequences and schedules are unchanged.
154 automated tests pass, including history failure/cache and unchanged-state
regressions. This is not a fresh physical history verification: absolute timestamp
semantics remain unverified, and the list follows device index order. The 50-entry
limit follows the app display, not a claim about the robot's total retention.
