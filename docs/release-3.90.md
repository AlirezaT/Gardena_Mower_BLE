# Gardena Mower BLE v3.90 — Minimo settings corrections

Stable release scoped to the tested SILENO minimo. Manifest: `3.90`.
GitHub/HACS tag: `v3.90`.

- Correct Eco and Frost mappings from the app-tested beta.
- Correct SensorControl to Low=1, Medium=2, High=3, matching the Minimo app.
- Match Minimo distance limits: Drive Past Wire 20–35 cm and charging-station
  starting distance 60–300 cm.
- Separate radar from ZoneProtect; remove the collision-status value incorrectly
  exposed as Supported Accessories.
- Remove the unrelated radar-disable fallback from loop-signal generation.
- Preserve the owner's tested SpotCut sequence and existing restore behavior.
- Retain the same original AutoMower-BLE upstream commit; no dependency upgrade.
- Record the full model/firmware/entity audit and next-version implementation list.

Install `v3.90` through HACS and restart Home Assistant. No blueprint re-import
or proxy firmware flash is needed when upgrading from 3.08/the Eco-Frost beta.
No settings are rewritten automatically; review SensorControl automations since
named levels now send their correct app values. An obsolete Supported Accessories
entity may remain unavailable in the entity registry.

Known inherited limitations: calendar failed-read/replace behavior, automatic
schedule resumption when editing while permanently parked, and SpotCut restore
edge cases remain unchanged. Avoid calendar edits on an unreliable connection
or while relying on permanent parking; use the official app instead. See
[the follow-up checklist](https://github.com/AlirezaT/Gardena_Mower_BLE/blob/v3.90/docs/next-version-checklist.md).
This release does not claim complete cross-model or end-to-end validation.
