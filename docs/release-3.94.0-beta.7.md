# v3.94.0-beta.7 — Explicit parking preferences and calendar recovery

Manifest: `3.94.0-beta.7`. Stable remains `v3.93`.

## Changes

- Return Home/Dock defaults to indefinite parking, even with onboard schedules.
  Previously, it selected until-next-schedule parking when tasks existed.
- New configuration entities: **Return Home behavior** (until further notice,
  for a duration, or until next schedule) and **Parking duration** (0.5–24 hours
  in half-hour steps, default 3 hours). Preferences persist locally and do not
  send movement commands when changed. The mower card's existing Dock action
  uses these preferences; configure them on the HA device page.
- Dock preserves an existing indefinite hold, regardless of the selected policy.
  Explicit Start or Resume schedule is needed to leave that hold; Resume may
  start mowing immediately when permitted by the planner.
- Calendar reads, display and edits preserve whole-second schedule times instead
  of rejecting non-minute values. Failed reads keep the entity registered but
  unavailable until recovery; editing cannot mistake a failed read for an empty
  schedule. Unchanged entries retain their exact seconds during edits.
- Calendar attributes include raw schedule seconds. Debug logs include the raw
  next-start timestamp alongside its existing decoded value. The reported
  16:32:35 endpoint still needs investigation; no speculative clock correction
  or automatic schedule rewrite is included.

Generation-specific parking sequences, command safety checks and fresh parking
confirmation remain in place. Start and SpotCut wire sequences are unchanged;
fallback parking during manual SpotCut-stop restoration now defaults to
indefinite parking too. The upstream dependency pin, blueprint and proxy firmware
are unchanged. Initial Bluetooth pairing retries are not claimed fixed.

## Validation and testing

213 automated tests pass, including parking order, existing-hold protection,
timed parking, preference persistence, calendar recovery and exact-second
read/edit preservation. Changed-code lint and whitespace checks pass.
Physical mower validation is still required.

Install beta.7 through HACS and restart Home Assistant. No proxy flash is needed.
Check that the calendar returns and compare its times with the official app
before editing. Confirm the new Return Home behavior defaults to Until further
notice. When safe, test Dock and verify it returns and stays parked. Changing
the dropdown alone must not move the mower. Keep debug logging enabled and share
the calendar's raw_schedules attribute and next-start logs if 16:32:35 persists.
If a command reports an uncertain result, inspect the mower before retrying.
