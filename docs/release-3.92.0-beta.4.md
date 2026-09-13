# v3.92.0-beta.4 — app-aware diagnostics and corrected blueprint

Manifest `3.92.0-beta.4` matches GitHub/HACS tag `v3.92.0-beta.4`.
Testing prerelease; stable remains `v3.91`.

## Changes since beta.3

- Correct the blueprint's invalid `has_service` template helper. Detection now
  uses integration membership and the presence of the mower's run-budget attribute.
  The condition was verified in running Home Assistant, not just mocked tests.
- Keep automatic-run duration separate from Manual Mowing Duration, including
  run accounting and legacy-integration fallback inherited from beta.3.
- Add the reviewed 97-code app title catalog and independently worded human
  troubleshooting guidance, with generation/guide branches and unknown-code fallback.
  Guidance is exposed as attributes; it never runs a recovery command or bypasses
  safety checks. Literal app UI/localisation parity is not claimed.
- Add verified family-name fallbacks while preserving known upstream variant names.
  P14 Gardena names require confirmed brand; unknown capacity is never invented.
- Add `app_date` and `app_time_24h` message attributes matching the app's distinct
  local-date and UTC-time formatting paths. Raw time is retained, with an explicit
  warning that absolute event-time interpretation is still unverified.
- Include a tested orientation-statistics dry-run/offline-copy repair tool. It
  never writes the source database, refuses ambiguous buckets and prevents double
  conversion. It does not automatically repair recorder history.
- Update README, checklist, evidence and repair documentation.

All beta.3 changes are included, including unsupported-feature hiding. The tested
Minimo SpotCut start/stop commands remain unchanged. No mowing-demand/area/growth
calculation, upstream dependency or proxy firmware change is included.

## Installation

1. Back up HA. Select `v3.92.0-beta.4` in HACS and restart Home Assistant.
2. Import the [corrected beta.4 blueprint](https://raw.githubusercontent.com/AlirezaT/Gardena_Mower_BLE/v3.92.0-beta.4/blueprints/automation/gardena_smart_mowing.yaml)
   into the existing blueprint, preserve your inputs and reload automations.
   Do not use the beta.3 or main-branch blueprint URL for this prerelease.
3. Check model visibility, diagnostics and the saved manual duration first.
   During a normally planned supervised run, verify its budget in the app and
   `last_start_duration_hours`; Manual Mowing Duration should not be overwritten.

The owner's live blueprint has already received the corrected action/accounting
path and a confirmed reload; publication does not install the new integration.
HACS does not update blueprints automatically for other installations.

## Verification and remaining limits

139 automated tests pass, plus scoped Ruff, compilation and version checks.
Live read-only template evaluation confirms the corrected new-action branch.
Fake-transport tests do not constitute physical all-model validation.

Original `alistair23/AutoMower-BLE` remains pinned to
`4bf4b00959f9ef712b5e1beebd725b0c75c80637`, not a fork or PR branch.
Physical loop-completion, parked-calendar and other-model tests remain open.
Production time stays raw because its factory timezone is unverified.
See [acceptance evidence](https://github.com/AlirezaT/Gardena_Mower_BLE/blob/v3.92.0-beta.4/docs/app-presentation-review.md)
and [recorder repair precautions](https://github.com/AlirezaT/Gardena_Mower_BLE/blob/v3.92.0-beta.4/docs/statistics-repair.md).
Do not relabel raw angle history as degrees or replace a running recorder database.
The full checklist is not closed.

## Rollback

Choose beta.3, beta.2 or stable v3.91 in HACS and restart HA. Keep the corrected
beta.4 blueprint: it supports beta.3's per-run action and falls back for older
integrations, where automatic runs again write the manual-duration number.
Previously integration-hidden entities may remain hidden after rollback; entity
management can reveal them. No mower settings or recorder history are reverted.
