# Gardena Mower BLE v3.91 — restore ZoneProtect

Fixes the missing ZoneProtect control introduced in v3.90.

- Adds a dedicated ZoneProtect switch, separate from Anti-collision Radar.
- Uses the Minimo app-capture-confirmed read 6050/4 and on/off write 6050/3.
- Reads availability separately from enabled state, rejects unconfirmed
  availability and refreshes the state with settings after writes.
- Adds regression tests for decoding, availability, on/off requests and failures.

Manifest version: `3.91`. GitHub/HACS tag: `v3.91`.
Install through HACS and restart Home Assistant. Update any dashboard/automation
that used the old radar entity for ZoneProtect to use the new ZoneProtect entity.
No mower settings are changed automatically. No blueprint or proxy flash needed.
SpotCut, calendars and the pinned original upstream dependency are unchanged.
Known limitations and the full cross-model follow-up from 3.90 remain documented
in the README and `docs/next-version-checklist.md`.
