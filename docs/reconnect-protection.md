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
