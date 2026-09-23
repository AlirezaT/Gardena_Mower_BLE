# v3.94.0-beta.8 — Safe parking with an empty schedule

Manifest: `3.94.0-beta.8`. Stable remains `v3.93`.

## Fix

Return Home with **Until next schedule** selected now falls back to **Until
further notice** when a successful mower read confirms zero onboard tasks.
Previously beta.7 rejected that request with NOT_AVAILABLE.

The fallback uses the existing generation-specific indefinite-parking sequence
and fresh parking confirmation. A failed or malformed schedule read still stops
the command; it is never treated as an empty schedule. With tasks present,
scheduled parking remains unchanged. The saved dropdown preference is preserved.
Adding a schedule later does not release an indefinite hold: explicitly use Start
or Resume schedule when ready. Resume may start mowing immediately.

Includes beta.7's parking preferences and second-precision calendar recovery.
No dependency, blueprint or proxy firmware changes. This targeted fix does not
claim to resolve the separate unconfirmed Start attempts or timed-Dock timeout
seen in the latest log. The owner confirmed that 16:32 was an onboard schedule.

## Validation and test

214 automated tests pass, including the empty-schedule fallback across recognized
model profiles, generation-specific command order, and rejection of malformed
counts and failed reads. Changed-code lint and whitespace checks pass.

Install beta.8 through HACS and restart Home Assistant. No proxy flash is needed.
When safe and with an empty onboard schedule, select Until next schedule and
press Return Home. Verify the mower returns and remains parked indefinitely.
Hardware confirmation is still needed; if a command reports uncertainty, inspect
the mower before retrying.
