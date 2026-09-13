# Orientation statistics: non-destructive repair workflow

`tools/migrate_orientation_statistics.py` is a standalone, standard-library
tool. It defaults to a read-only report and NEVER updates its source database.
With `--output` it creates a consistent, separately named SQLite snapshot and
repairs only explicitly selected statistics in that copy. It does not install
the copy into Home Assistant or rewrite original state history.

## What is corrected

Old pitch/roll statistics contain tenths of a degree. The migration multiplies
mean/min/max/state/sum by 0.1 for buckets proven entirely old, preserves NULLs,
leaves newer degree buckets unchanged, and sets the selected series' unit to °.
A marker prevents reapplying the conversion to an already migrated copy.
Other sensor histories are not modified. SQLite integrity is checked afterwards.

Metadata already labelled ° is not evidence that old measurements were scaled.
The tool accepts raw unitless or °-labelled recorder series, but requires the
operator to establish the historical boundary independently. It rejects unknown
units/sources, missing IDs, overlapping boundaries and mixed/uncertain buckets.
If an output snapshot was created before a failure, it is retained unchanged;
the error is not success and the copy must not be installed as a repaired database.

## Verified local evidence, September 13

The retained state history changes from unitless raw -4/-6 to -0.4/-0.6 degrees
on September 12 at 20:47:50 UTC. The 20:00 hourly buckets and every retained
short-term bucket up to 20:45 still contain raw -4/-6; there are no 20:50/20:55
short-term rows. New statistics from 21:00 UTC use degrees. This is why a 21:00
statistics boundary is supported here; do NOT infer it merely from installation time.

Dry-run result per orientation series: 2,250 old hourly buckets and 1,355 old
short-term buckets; zero ambiguous buckets. Newer counts depend on when checked.
The actual source database was not modified. This evidence applies only to this
installation, not other users or future resets/imports of their recorder database.

## Dry run

Use exact statistic IDs verified in entity management. For the verified local
case, pass `--raw-before 2026-09-12T21:00:00Z` and
`--degrees-from 2026-09-12T21:00:00Z`. Example with placeholder IDs:

```sh
python tools/migrate_orientation_statistics.py /path/to/recorder.db \
  --statistic-id sensor.example_orientation_pitch \
  --statistic-id sensor.example_orientation_roll \
  --raw-before 2026-09-12T21:00:00Z \
  --degrees-from 2026-09-12T21:00:00Z
```

## Applying a reviewed repair

Arrange a Home Assistant maintenance window and take a verified full backup.
Stop HA cleanly before creating the final migration copy, so replacing the
database later cannot discard intervening history. Re-run the dry run against
that final stopped database. Add `--output /new/path/recorder-repaired.db` to
create a new copy; never reuse the source path or overwrite an existing backup.
Compare row counts and selected before/after values, inspect the migration report
and integrity result, and retain the original database as rollback material.
Only then should an administrator install the repaired copy with HA stopped,
handling SQLite WAL/SHM files through the supported backup/restore workflow.
Do not replace a live database or reuse a stale snapshot taken hours earlier.

Restart HA and verify these statistics plus unrelated histories. No automatic
database replacement or restart is included in the integration or this tool.
