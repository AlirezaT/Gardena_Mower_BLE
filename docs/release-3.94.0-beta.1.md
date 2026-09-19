# v3.94.0-beta.1 — start confirmation and P0 firmware parsing

Manifest: `3.94.0-beta.1`. Stable remains `v3.93`.

Validation: 170 automated tests pass, including new accepted-start, lost-link,
uncertain-outcome, cancellation, safety-stop and firmware-parser regressions.
Changed Python files pass lint; manifest/tag version validation passes.

## Changes

- After an ambiguous start result, read fresh state on the existing connection
  before forcing a reconnect. If mowing/leaving or an accepted pending start is
  confirmed, retain the session and do not replay the command.
- Keep at most one reconnect/retry when acceptance cannot be confirmed. Failed
  reconnection now explicitly says the mower may already be mowing, rather than
  presenting only a connection error. No retry occurs without fresh state checks.
- Preserve STOP, safety-PIN and error-state checks. Pending start with no activity
  remains a safety prompt, not proof that mowing started. No safety bypass added.
- Parse full main-application firmware strings as well as bare numeric versions.
  The app uses the suffix after `Main-App-<platform>_`, optionally `release-`;
  it does not use the leading component number. This enables the existing P0
  Frost/ZoneProtect/CorridorCut version gates when firmware is reported that way.
  Boot/software-bundle strings and malformed values remain unknown.

The connection security sequence, 60-second connection timeout, Minimo SpotCut,
error history, blueprint and upstream dependency pin are unchanged. This does
not claim to repair an underlying BLE/proxy/battery fault in issue #10. The
accepted-command/reconnect-error path was reproduced with a simulated mower;
the reporter's current debug log is still needed to establish his exact cause.

## Test

Install this prerelease through HACS and restart HA. No proxy flashing or
blueprint re-import is required. Close the phone app while testing HA.

During a normal, safe mowing session, enable integration debug logging, request
start once, and observe whether the real mower and HA agree. If HA reports an
error, inspect the mower before pressing start again. Check that telemetry
continues updating and test the normal return-to-dock action. Capture a full
log spanning the action and subsequent refresh; redact sensitive information.
For an older P0 mower, include the exact main-application firmware string and
check availability of Frost, ZoneProtect and CorridorCut without changing them.

## Optional manufacturer firmware check

Record the current firmware first (mower Settings > General > About). Gardena
recommends current firmware for reliable operation and includes firmware checks
in its Bluetooth troubleshooting. If the official tool offers an update for the
exact mower, consider it after collecting a baseline beta test. Change one thing
at a time. Follow Gardena's instructions, not another model's firmware package.
If a battery-temperature fault persists, consult Gardena before attempting an
update; a software update is not a substitute for resolving a battery fault.

- [Official software update instructions](https://www.gardena.com/int/c/support/planning-advice/robotic-lawnmowers/maintenance/software-update)
- [Gardena Bluetooth troubleshooting](https://help.gardena.com/hc/de/articles/7991780498204-M%C3%A4hroboter-kann-nicht-mit-Bluetooth-verbunden-werden)

Firmware updating is an optional suggestion, not a prerequisite for this beta
or a confirmed fix for the reported symptoms. No firmware is installed by this
integration, and no bonds are reset.
