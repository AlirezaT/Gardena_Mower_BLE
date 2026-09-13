# v3.92 — model-aware controls and confirmed permanent parking

GitHub/HACS tag `v3.92`; Home Assistant manifest version `3.92`.
Promotes beta.5 without runtime code changes or dependency changes.

## Changes since stable 3.91

- App-reviewed model/firmware capability rules, settings and diagnostics;
  unsupported features hidden for the identified mower, including Minimo radar.
- Separate automatic-run budgets from the saved manual mowing duration, with
  the corrected blueprint action detection and run accounting.
- Model-dependent action and calendar safeguards, including permanent-park
  outcome confirmation after ambiguous StartTrigger replies.
- Reviewed app error titles, model-aware guidance, family-name fallbacks and
  explicit message-date/time attributes.
- Optional offline-copy orientation-statistics repair tool; never modifies the
  live database automatically.

The owner's tested Minimo SpotCut sequence is preserved. The original
AutoMower-BLE dependency remains pinned to commit
`4bf4b00959f9ef712b5e1beebd725b0c75c80637`, not a local fork or PR branch.
No proxy firmware changes are included.

## Verification and limits

141 automated tests pass, with scoped lint and whitespace checks. Installed
beta.5 files matched the repository before promotion. The owner reported the
Minimo test working; September 13, 18:23–18:25 local HA history shows Start/Park
transitions, SpotCut staying off and error code zero, with no new control errors
in the available logs. HA subsequently confirmed docked/parked at 18:26:24.
Earlier ambiguous-start and recovered BLE-timeout logs
remain recorded; their cause is not proven to be phone caching or overlapping
commands. This is not a guarantee against future BLE interruptions.

Physical cross-model, parked-calendar and loop-completion validation remain
open. Full manufacturer presentation/time interpretation parity is not claimed.
See [remaining checklist](next-version-checklist.md),
[parking evidence](permanent-park-reply-fix.md) and
[statistics precautions](statistics-repair.md).

## Installation

Select `v3.92` in HACS and restart Home Assistant. Publication does not install
or restart HA. If using the corrected beta.4/beta.5 blueprint, no blueprint
update is required. When upgrading from 3.91 or earlier, import the
[3.92 blueprint](https://raw.githubusercontent.com/AlirezaT/Gardena_Mower_BLE/v3.92/blueprints/automation/gardena_smart_mowing.yaml),
preserve inputs and reload automations.

Rollback: select `v3.91` in HACS and restart HA. Keep the corrected blueprint;
its legacy fallback supports older integrations. Rollback does not undo mower
settings or recorder history changes.
