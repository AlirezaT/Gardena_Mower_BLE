# Reconnect protection

The integration still installs the original `alistair23/AutoMower-BLE` package
at the commit pinned in its manifest. `connection.Mower` subclasses that package;
protocol definitions, parsing, device features and mower commands stay upstream.

The pinned upstream version can expose a BLE connection before notification
setup and authentication finish, and a keep-alive task can survive an unexpected
disconnect. This allowed requests to run with a missing client or characteristic.

The integration adapter uses one task-reentrant lock for connection setup,
upstream command and schedule transactions, and disconnect. It reports connected
only after setup succeeds, cancels stale keep-alive tasks before reconnecting,
cleans up partial sessions even when the link has dropped, validates the write
target, and propagates cancellation swallowed by the upstream request handler.
Setup uses Home Assistant's connectable device selection rather than falling back
to an independent local BlueZ lookup when no enabled adapter can reach the mower.

Run the regression tests with the manifest's upstream dependency installed:

```sh
python -m unittest discover -s tests -v
```

These tests exercise races, incomplete authentication, disconnected writes,
timeouts and schedule-lock cleanup without commanding a physical mower. They do
not establish radio coverage or guarantee Bluetooth proxy firmware stability.

## Explicit start recovery (3.08 preview)

An explicit start reads mower state before issuing the upstream manual
override. UNKNOWN_ERROR, DEVICE_BUSY, or a lost BLE response allow at most one
fresh-session retry. State is read back before retrying; an already accepted
start is not replayed. Physical STOP/PIN/error states and pending start with no
activity are surfaced to the user, not treated as a successful start. Permanent
command failures report the response, state and activity instead of a bare
UNKNOWN_ERROR. Setup itself never invokes this recovery or writes mower modes.

Issue #11 remains a candidate fix pending a test on the affected SILENO City;
there was no failure trace with which to prove a hardware-specific cause.

The manual-duration virtual number is stored in config-entry options. Existing
restore data is migrated when available, with a validated three-hour default
otherwise. The value is loaded when constructing the coordinator, so reloads do
not depend on entity restoration order. Half-hour values retain their fraction.

For 3.08-beta.1, tests were run against upstream commit
`4bf4b00959f9ef712b5e1beebd725b0c75c80637`: 36 local tests (connection lifecycle,
duration persistence, start recovery, and blueprint templates) and 24 upstream
protocol tests. HA-facing persistence methods use lightweight collaborators in
the regression suite; this is not a full Home Assistant restart/hardware test.
