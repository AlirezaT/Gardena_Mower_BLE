# v3.94.0-beta.9 — Action confirmation priority and rediscovery grace

Manifest: `3.94.0-beta.9`. Stable remains `v3.93`.

## Changes

- Start and Dock reserve traffic priority through connection preparation, command
  execution and confirmation. Coordinator polls (including settings/history) and
  calendar read requests yield at command-lock boundaries until the action ends.
  The wire lock is not held across the entire observation window: keep-alive and
  explicit user controls remain eligible. A background request already on the
  wire is not cancelled; it can still delay an action until it finishes or times
  out. Success, errors and cancellation all release the priority reservation.
- Optional static-information reads that fail or return unusable values wait
  five minutes before retrying. Successful values remain cached; explicit
  unsupported responses retain the existing skip behavior. UNKNOWN_ERROR is not
  treated as proof of unsupported hardware. Transport timeouts still propagate;
  this change does not swallow missing replies or claim that the link is healthy.
- Reconnect allows up to ten seconds for HA to rediscover a connectable mower
  before reporting a visibility failure. This is before any movement command,
  not an automatic replay of Start or Dock. Existing handshake limits remain.

The City log showed a battery-read timeout consuming Start's confirmation window
and a separate hardware-serial read timeout before a failed connection lookup.
These are software responsiveness/recovery improvements, not proof that either
read caused a mower reboot.

## Unchanged and still under investigation

Start/Dock wire sequences, STOP/PIN checks, parking preferences, Minimo SpotCut,
schedule contents, upstream dependencies, blueprint and proxy firmware are
unchanged. The separate City direct-Dock failure while GOING_OUT is not claimed
fixed. The inspected Android app sends no implicit Pause in that parking path.

## Validation and first test

225 automated tests pass. New tests cover queued and in-flight background reads,
command confirmation with competing polling, heartbeat access, nested action
windows, cancellation cleanup, delayed/missing advertisements, static-read
backoff and successful caching. Changed-code lint and whitespace checks pass.
Physical mower validation is still needed.

Install beta.9 through HACS and restart HA. This beta is for the maintainer's
Minimo check first; no new test request has been posted to issue #11.

1. Close the phone mower app and enable integration debug logging.
2. When safe, press Start once from an indefinite hold; it is not necessary to
   turn the hold switch off first. Check both physical departure and HA status.
3. Test Pause, then Return Home. Confirm indefinite parking remains active and
   the calendar/settings resume updating afterward.
4. Leave logging on for a few minutes after the sequence and save the full log.
   Do not deliberately disrupt Bluetooth or repeatedly press Start to reproduce
   a timeout. If a result is uncertain, inspect the mower before retrying.

No proxy compilation/flashing or blueprint update is needed.
