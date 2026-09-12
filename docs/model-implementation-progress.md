# Cross-model implementation — v3.92.0-beta.2

This extends `v3.92.0-beta.1` in the owner-approved beta.2 prerelease, with the
limitations below explicitly retained. It does not claim physical validation on
other models. The manifest is `3.92.0-beta.2`, tag `v3.92.0-beta.2`. Historical
audit findings and beta.1 release notes describe their original snapshots.

## Implemented since beta.1

- Accepted P14 identities are restricted to the app catalog's type/variant
  pairs: 34/{1,2,4}, 35/{1,2,3,7,8,9}, 36/{1}, 37/{1,2,3}. Evidence:
  `MowerModelKt.mowerModel` catalog entries plus
  `DefaultMowerRepository.getMowerPlatform/getMowerGeneration`. Unknown pairs
  remain unknown; the repository's default case alone is not sufficient.
  These profiles enable five-point and five-level controls, the P14 distance
  bounds, radar availability checks and garage exclusion. P14 brand-specific
  guide choices require explicit Gardena/Flymo brand confirmation in integration
  options. This follows the app's application-brand branch without guessing brand
  from numeric type. Other platforms retain their detected guide arrangements.
- Starting-point enabling follows the app's
  `SetStartingPointEnabledUseCase`: both generation-specific helpers repeat the
  enabled write; disabling additionally clears the point's proportion between
  the two enabled writes. Commands stop on failure and read back the result.
  This intentionally changes point-disable behavior, not SpotCut behavior.
- Calendar replacement validates G3/G4 capacity (14/15), G3 two entries per
  weekday, field ranges and exact minute representation. G3 last-entry deletion
  is rejected rather than inventing an unverified placeholder schedule.
  Failed reads cannot become an empty replacement calendar. Writes are serialized,
  compare the previously read schedule, check every reply and verify read-back.
  A partial failure, cancellation or mismatched read-back blocks further writes
  until the user checks the mower calendar in the app and reloads the integration.
  No automatic rollback, mode change, override clearing or start command is sent.
  This is a protocol safeguard, not a physical permanent-park test.
- AddTask uses the app's 15-byte layout for confirmed generations, without the
  upstream extra padding. Minimo capture evidence supports this layout; other
  generations have static app evidence, not physical capture validation.
- G3 diagnostics use Comboard and legacy signal-quality reads. G4 uses battery,
  collision, lift and orientation commands and averages front/rear loop strength
  (sensor selectors 0/1 from `ILoopSystemSensor`). Collision 4166/8 decodes two
  booleans; lift 4476/6 decodes one. Missing data stays unknown. The app's 999999
  battery/orientation sentinel is not exposed as a measurement. Pitch/roll display
  uses degrees at one tenth of the raw value. Unverified guide channels are omitted.
- Six individual statistics reads are independent of optional aggregate blade
  statistics. Unsupported commands are cached for the connection's coordinator;
  transient failures and malformed responses remain retryable.
- Pause checks the command result before reporting success. Dock/pause connection
  failures now raise errors instead of silently returning.

## Further implementation after the initial 92-test checkpoint

- Point distance maximums now match EditDistanceScreenKt: P0 300 m, P005 100 m,
  P14/P005GA 500 m; minimum 1 m. Both HA bounds and outbound values are checked.
- Permanent park selects the G3/G4 app sequence and checks each result. Resume
  failures are no longer silently accepted. Minimo SpotCut start/stop delegates
  to the original tested upstream methods; other models use verified generation
  sequences, with positive runtime availability required for P14/flex.
- SpotCut restore no longer restarts an expired duration or turns scheduled mowing
  into a manual allowance. Mower-clock comparison plus a monotonic deadline avoids
  extending the allowance because of a host timezone/DST change. Missing timing
  does not authorize another mowing run. This is an intentional restore improvement.
- Next-start DST gaps/folds stay unknown rather than choosing an arbitrary instant.
- Loop pairing awaits validated success/failure events (4692/2 or 4692/1), with
  a 90-second completion timeout matching the app. The transport now separates
  events from responses, reassembles fragments and retains coalesced frames.
  Capture reassembly and keep-alive regression checks pass; physical completion
  event confirmation remains outstanding.
- SensorControl, garage, radar and distance reads now retry transient failures
  independently. Invalid Boolean bytes remain unknown rather than becoming true.

Current automated verification: 123 passing tests and scoped lint checks.
The retained capture's 3,409 linked frames passed 27,272 fragmentation/coalescing
checks. This includes 1,703 requests, 1,703 replies and three other packet types;
no pairing-completion event was present. Synthetic event checks and app constructor
evidence therefore remain distinct from physical pairing-event validation.

## Presentation and extra-diagnostic policy

The app does not establish availability for every extra HA hardware/software
diagnostic. These remain optional read-only diagnostics, accepted only when a
device supplies a usable response; lack of evidence is not a guessed capability.
Production timestamps are now explicitly raw, not falsely labelled UTC. Message
timestamps remain raw attributes and log entries identify the unverified clock.
Next-start timestamps have separately verified local-wall-clock handling.

Missing upstream marketing names fall back to a verified platform/type/variant,
without inventing a lawn capacity. Error 38 uses the P14-specific short label.
Other short error labels retain numeric fallback; model-specific troubleshooting
instructions remain in the manufacturer app rather than being copied into HA.
These are explicit conservative presentation choices, not full app UI parity.

Blueprint review: rainfall, irrigation, soil moisture, area and effective capacity
are already inputs. BLE platform identity does not establish a daily allowance or
the exact variant's throughput. No automatic demand/calibration change is made.
Only a source comment documents that separation; no re-import is necessary.

## Preserved and still outstanding

The owner's tested Minimo SpotCut underlying start-stop sequence is unchanged. The
original pinned upstream library, installed integration, mower settings, existing
release tags and unrelated proxy firmware files are unchanged by this work.

Exact marketing-name coverage, complete manufacturer troubleshooting text and
production/message clock interpretation are not claimed. They use the explicit
fallbacks above. Physical other-model tests and pairing-event observation remain
unperformed. Daily mowing limits are not inferred from a shared platform identity.

See [the complete checklist](next-version-checklist.md) and
[the original model audit](model-dependency-audit.md). Automated tests use transport
fakes and protocol encoding checks; they are not an end-to-end HA or mower test.
