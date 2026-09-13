# v3.92.0-beta.5 — permanent-park confirmation

Manifest `3.92.0-beta.5` matches GitHub/HACS tag `v3.92.0-beta.5`.
Testing prerelease; stable remains `v3.91`.

## Changes since beta.4

- Fix false Park Until Further Notice failures when StartTrigger returns
  UNKNOWN_ERROR even though the mower has accepted parking.
- After that ambiguous reply only, wait two seconds and require successful
  fresh readings of HOME, an operating/restricted state and a returning-home,
  parked or charging activity. Unconfirmed outcomes and other errors still fail.
- Preserve the app-verified G3 HOME/start and G4 HOME/clear-override/start
  sequences, checked against the supplied GARDENA Bluetooth 9.2.0 app.
- Add regression coverage across recognized model types and update the checklist.

Minimo SpotCut, upstream dependency, blueprint, settings and proxy firmware are
unchanged. All beta.4 functionality is included. See
[implementation evidence](permanent-park-reply-fix.md).

## Installation and testing

Select `v3.92.0-beta.5` in HACS and restart Home Assistant. If already using the
corrected beta.4 blueprint, no blueprint import or automation reload is needed.
Publication does not install or restart anything automatically.

When safe and supervised, test Park Until Further Notice and confirm the mower
returns/stays parked, HOME is reported and no false service error appears.
Keep permanent park enabled if you want it to remain parked.

141 automated tests pass, plus scoped lint and whitespace checks. Tests use fake
transport; physical confirmation on Minimo and other models remains pending.
No commands were sent to the mower during development. The wider model checklist
is not closed.

## Rollback

Select beta.4 or stable `v3.91` in HACS and restart Home Assistant. Beta.4 has
the known false parking-error behavior. Keep the corrected beta.4 blueprint.
Rollback does not change mower settings or recorder history.
