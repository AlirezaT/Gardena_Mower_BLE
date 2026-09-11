# v3.92.0-beta.1 — model-dependent settings, first beta

Manifest `3.92.0-beta.1`; tag `v3.92.0-beta.1`. Stable remains v3.91.

- Identify verified P0/P005/P005GA families by numeric device type and variant.
- Filter SensorControl choices, drive/station distance limits and guide options.
- Support 3/5 starting points, including flex points 4/5 and complete station-share
  calculation. Partial reads do not produce a misleading remaining share.
- Use individual G3 starting-point reads and G4 combined reads with CorridorCut
  read separately from its firmware-selected command.
- Select P0 Frost, ZoneProtect and CorridorCut commands by validated main firmware;
  disable uncertain settings rather than guessing or probing with writes.
- Gate Garage/radar/Frost availability, preserve the dedicated ZoneProtect switch,
  and reject invalid model settings even through stale HA entities.
- Add platform, generation and starting-point-count diagnostic entities.

Minimo SpotCut, calendars, blueprint and upstream dependency are unchanged.
This is the first settings-layer beta, NOT completion of all cross-model work.
P14 IDs remain unverified; unknown devices do not get a P14 profile. G3
starting-point enable controls are withheld until their extra workflow is
implemented. Full diagnostic/action/calendar parity and existing restore/calendar
limitations remain on the [checklist](https://github.com/AlirezaT/Gardena_Mower_BLE/blob/v3.92.0-beta.1/docs/next-version-checklist.md).

Enable prereleases in HACS, select this tag and restart HA. Verify Model Platform,
Model Generation and Supported Starting Points first. On Minimo expect P005,
generation 4, three points and Low/Medium/High. Compare settings while docked;
disconnect HA before using the app. No automatic setting migration, firmware
flash or blueprint re-import. Roll back to v3.91 and restart if needed; rollback
does not undo settings you manually changed. No live mower movement tests were run.
