# v3.94.0-beta.5 — History/control fairness and polling diagnostics

Manifest: `3.94.0-beta.5`. Stable remains `v3.93`.

## Changes

- Keep beta.4's P0 timed Start unchanged. The #11 owner confirms successful
  departure without reboot/connection loss; all three start replies were OK.
- Release the command lock between history reads instead of holding it for the
  entire up-to-50-entry fetch. Waiting controls can run between reads; individual
  transactions and action sequences remain serialized.
- Preserve the 60-second history budget, count/head rotation checks and cached
  complete snapshot after failure. No partial list is labeled complete.
- Log command name/outcome, local lock-wait and execution duration. History logs
  add the entry index; exception types are logged without private exception text
  or request/response payloads. These timings cover command/command_response;
  beta.4's explicit P0 action logging remains unchanged.
- Log reconnect only after checking that the current session is not ready.

## App evidence and limits

Rechecked retained Android 9.2.0 DEX: ErrorHistoryViewModel initialization reads
the count and caps it at 50; getFirstChunk requests indexes 0–9, getNextChunk
reads indexed messages, and Show More advances by ten. No model branch was found
in that UI path. This does not prove support on every firmware or require new
P0-specific message layouts. The app does not automatically fetch all 50 on
each history screen opening as our cache can on a diagnostic refresh.

The anonymized #11 log has successful polls taking 22–103 seconds and two history
failures, but omits exception details and state/activity values. History lock
contention is a code-confirmed risk, not a proven explanation for every delay.
Full history still runs within a coordinator poll and can delay its completion;
this beta measures the remaining bottlenecks rather than claiming to solve them.
No changes to mowing/parking sequences, schedules, safety checks, blueprint,
proxy firmware, upstream pin or error-history timestamp interpretation.

## Validation

188 automated tests pass, including waiting-control/history interleaving,
history rotation/rejection/cancellation, timing-result/argument preservation,
cancelled lock waits, payload privacy and existing exact P0 Start order.
HA version parsing and tag/manifest match are tested. Hardware timing improvements
still need confirmation on the affected mower.

## Test

Install via HACS prereleases and restart HA. Close the phone app, enable integration
debug logging and leave it running for 10–15 minutes of normal use to include a
history refresh. If safe, try one normal Start followed later by Park, noting
the times and whether HA follows the mower. No repeated reboot tests needed.
Send the full debug log through any delay/failure. Keep state/activity/mode,
command names/results/timings and history indexes intact; redact PINs, addresses,
serial numbers and other identifying details. No HCI capture or video required.
