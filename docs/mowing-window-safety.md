# Mowing window and onboard schedules

The smart blueprint's estimated schedule is not the robot's onboard calendar.
An onboard task can start the robot independently, including after a daily
operating restriction ends. HA recording a mowing start does not mean it sent
the Start command.

When the blueprint is the scheduler:

1. Record/back up existing onboard tasks, then remove conflicting tasks with
   the mower calendar or `gardena_mower_ble.clear_schedule` (specify the mower's
   config entry when necessary). The blueprint does not delete tasks itself.
2. Select this mower's **Park Until Further Notice** switch in the blueprint's
   **Park until further notice switch** input.
3. Keep **Park outside allowed mowing hours** enabled. This also stops manual
   starts outside the window and on excluded weekdays. The end is now a mowing
   cutoff, not merely the latest permitted start time.

The guard runs before weather fetching and before start-event bookkeeping,
on normal triggers, HA startup, and every minute. It holds even a docked mower
outside allowed hours and does not repeatedly command an already enabled hold.
It bypasses the Return Home preference by enabling the permanent-park switch.
It never turns that switch off to resume the internal schedule; the planner's
next eligible explicit timed Start releases the hold. Without a configured
switch, the generic fallback docks a mowing mower; its integration must be
configured to park indefinitely for equivalent protection.

Response checks now wait for the requested state rather than always sleeping
for the full configured timeout. Runs remain queued to preserve accounting;
an outstanding command/response timeout can still delay guard execution.
Window variables are refreshed when a queued run executes and again before
Start. Deliberate fixed-time overnight windows remain supported. Equal window
boundaries or reversed sun-relative boundaries are closed, not interpreted as
permission to mow through the night.

This is not a hardware interlock: HA must run and BLE commands must succeed.
Removing conflicting onboard tasks is important even with the guard enabled.
For manual mowing outside the window, deliberately disable the enforcement
input first. The guard does not implement a separate wet-weather policy change.

## Regression coverage

`python3 -m unittest discover -s tests -p 'test_mowing_*.py' -v`

Tests render the actual YAML templates and exercise guard choices for midnight
starts, docked holds, excluded days, boundary times, optional/generic behavior,
unavailable entities, fixed overnight windows, solar-window inversion, startup
triggers and fresh pre-start checks.
