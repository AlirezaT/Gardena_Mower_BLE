# Eco Mode / Frost Sensor correction — v3.09-beta.1

Testing prerelease. No mower settings were changed during automated validation;
physical app/HA comparison is still required.

The app's preserved 9.2.0 DEX constructors identify these commands:

| Setting | Read | Write | Boolean |
| --- | --- | --- | --- |
| Eco Mode | 4692/6 | 4692/5 | Direct, no inversion |
| Frost Sensor, new module | 5370/1 | 5370/2 | Direct |
| Frost Sensor, other module | 5412/1 | 5412/2 | Direct |

The installed upstream pin has the wrong labels. Until upstream publishes a
corrected package, `connection.Mower.get_protocol()` overlays just these command
definitions in its own instance. It does not modify upstream files or other
integrations. This additional local override is explicit and should be removed
once a tested upstream release contains the correct definitions.

Both the existing legacy frost read and PR #161's proposed legacy write at
4476/6 and 4476/5 are excluded: the app identifies these as lift-sensor reads.

Frost selection uses read-only capability checks: try 5370/1, then 5412/1 only
after INVALID_GROUP, INVALID_ID or NOT_AVAILABLE. A transient, authentication or
permission failure does not cause a fallback. Invalid payloads are not treated as
enabled. A valid read selects its matching setter; no write is allowed without
a confirmed setter. This differs from the app's firmware-version selection and
still needs validation on affected physical models.

HA entity keys are retained. The Eco switch now calls SetEcoModeEnabled directly;
Frost uses the matching confirmed module. Polling reads each actual setting,
not the other setting or its inverse. No automatic migration writes are sent:
after installation HA will display what the mower actually reports, which may
differ from the previously mislabeled UI state.

Tests cover packet IDs and payload bytes, read-only selection and failure cases,
instance-local overrides, both switch setters and rejected writes. Existing
connection, duration and blueprint regressions must also continue passing.

Before installing, review the changes and arrange a supervised
app/HA comparison while docked. Pause command automations and release one BLE
client before connecting the other. Record actual settings in the app first,
change one setting at a time, confirm app readback, and restore desired values.
Do not infer physical success from mocked tests. The unexplained report of both
app switches remaining enabled still requires that controlled validation.
