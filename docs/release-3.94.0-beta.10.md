# v3.94.0-beta.10 — P0 departure observation and action tracing

Manifest: `3.94.0-beta.10`. Stable remains `v3.93`.

## Changes

- P0 manual Start sends the unchanged AUTO → SetOverrideMow → StartTrigger
  sequence once. The service bypasses the upstream two-second read-back probe
  and uses one state/activity observer, waiting five seconds before its first
  sample and between completed samples. The existing 15-second observation
  deadline remains; slow requests can leave fewer samples. Both OK and ambiguous
  replies are checked for departure on this P0 service path.
- Charging and pending state alone are not proof of departure. P0 success needs
  IN_OPERATION with GOING_OUT or MOWING; HA retains that observed activity rather
  than injecting MOWING. Unconfirmed outcomes still report uncertainty, not a
  firmware-reboot diagnosis. Failed Start requests schedule a normal refresh.
- The command lock covers each status pair, not the waiting periods. Keep-alive
  and explicit Pause/Dock remain eligible. Beta.9's background traffic priority
  remains active. Observation stops if the connection session changes; it never
  reconnects or replays Start. Underlying transport timeout/cancellation cleanup
  may still disconnect a failed session.
- Before P0 Start, read mode, override action/duration, raw restriction reason
  and remaining charging time. Then check fresh safety state/activity. Rejected
  optional diagnostic values are logged as unavailable, not inferred. A transport
  failure while collecting this snapshot aborts before any movement write.
- Start/Dock/Pause get local action counters; new connection attempts get local
  session counters. Command logs include response_source and wire_result, including
  the locked command path used by P0 actions. A received frame's result byte is
  distinguished from no response, timeout and cancellation. This is provenance,
  not additional frame validation. No raw packets, PINs or payload dictionaries
  are added by this tracing. Existing logs still need normal identifier redaction.

The optional `confirm_trigger` Python argument preserves previous P0 confirmation
for non-service callers such as restoration paths. Minimo and other non-P0
Start behavior, all movement-command sequences, parking policies, safety gates,
SpotCut, schedules, upstream pin, blueprint and proxy firmware are unchanged.

## Evidence and limits

The retained Gardena Android 9.2.0 app's dashboard invokes startMowerForDuration
directly. That path has no extra parking-release step or P0-specific wait.
Generation 3 permanent parking omits ClearOverride; our parking order matches.
GetMowerStatusUseCase's status flow waits 5000 ms between cycles and represents
CHARGING separately using remaining charging time. It does not establish that
all app traffic pauses during a countdown or that the iPhone app is identical.

Our previous service could run the upstream confirmation probe and immediately
start a second observer. Removing that duplication is a controlled experiment,
not proof the reads caused issue #11's reported reboot. Beta.4 demonstrated one
successful departure but did not capture its later Start's outcome. The history
does not establish a beta.5 regression. The full first/second-start state comparison
and physical City result are still required.

## Validation

243 automated tests pass against the pinned upstream dependency. Changed-code
lint, whitespace checks and HA version parsing pass with GARDENA_RELEASE_TAG set
to v3.94.0-beta.10. Tests cover exact P0 write order, delayed single observation,
charging-only uncertainty, OK versus ambiguous replies, stopped/safety states,
loss/change of session, cancellation, transport failures, background yielding,
heartbeat access, response provenance, action correlation and unchanged Minimo.
Automated results do not substitute for hardware testing.

## Maintainer Minimo test first

1. Install beta.10 through HACS and restart HA. Close the official app and enable
   integration debug logging before normal use. No re-pair or proxy flash needed.
2. When safe, try Start → Pause → Return Home. Let it physically dock before one
   later Start. Verify entity status follows the mower and parking stays correct.
   Minimo does not use the new P0 observer; this checks shared tracing/regressions.
3. Keep logging for a few minutes afterward and download the original debug log.
   Preserve command names, timestamps, action/session counters, response_source,
   wire_result, state/activity and P0 snapshot fields when present. Redact private
   identifiers rather than summarizing or removing command lines.

Do not repeatedly trigger a reboot or retry an uncertain movement command without
checking the mower. If it reboots or reports a physical fault, stop the test.
No issue #11 comment/test request has been posted for this release. Once Minimo
passes, compare a supervised complete repeated cycle on City with an equivalent
official-app cycle while HA is disabled; do not run both clients together.
