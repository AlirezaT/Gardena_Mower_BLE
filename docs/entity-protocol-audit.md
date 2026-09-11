# Entity protocol audit — final 3.90 release gate

## September 12 release-scope decision

The owner requested a Minimo-scoped stable 3.90 first and the complete
cross-model implementation in a later version. The original broad release gate
below is retained as historical audit evidence, not a claim that all findings
were resolved. The 3.90 corrections are documented in the README; SensorControl
is restricted to the Minimo's three choices and its two distance bounds are
corrected. The owner has tested SpotCut and explicitly requested preserving its
sequence. Calendar and SpotCut restore findings remain known inherited
limitations, not verified fixes. See `next-version-checklist.md` for the complete
follow-up scope. This release is not all-model or exhaustive end-to-end validation.

## September 11 capture follow-up

The owner's subsequent snoop capture and nine screenshots were analyzed offline.
Detailed private evidence is in `Gardena BLE dev/BLE snoop logs/sep-11/analysis.md`;
do not publish the raw capture. All 3,406 decoded HCP request/response frames pass
CRC and length checks, with 1,703 matched request/response pairs.

This evidence refines the earlier static audit below:

- This mower's SensorControl UI offers **Low=1, Medium=2, High=3**. Writes and
  later reads confirm these values. The local five-option draft is too broad
  for proven app parity: values 0/4 exist in the shared enum but were neither
  offered nor tested here. Do not present them as confirmed supported options.
- ZoneProtect 6050/3,4, Garage 4692/3,4, Eco 4692/5,6 and Frost 5370/1,2 are
  confirmed by accepted app commands and screenshot correlation. ZoneProtect
  and Garage also have direct changed-value read-back.
- The primary loop command 4692/2 is accepted. Radar command 5356/3 returns
  INVALID_ID three times; radar support is **not** confirmed on this mower.
- Starting-point 1's combined layout, 17 m distance, 68% share and CorridorCut
  byte match screenshots. Reversing raw 1000 matches the displayed 1.0 m.
- Two successful calendar writes have 15-byte payloads, with read-back; the
  extra write padding is absent. Task read responses contain four trailing
  zero bytes, which must not be confused with required write bytes.
- The mower remains AUTO / RESTRICTED / PARKED with override NONE throughout.
  It was **not permanently parked**, so permanent-park preservation remains
  untested. Failed-read handling and SpotCut restore risks also remain open.

No integration code, installed configuration, version or release was changed
during this follow-up analysis. The original audit below records the state of
the draft at the time it was written; this addendum supersedes its claim that
all five sensitivity choices should necessarily be exposed on this mower.

Original broad-audit status: **NOT cleared for an all-findings-resolved release.** Reviewed against the retained GARDENA
Bluetooth App 9.2.0, starting from integration commit `7115113` and its pinned
upstream automower-ble dependency. Confirmed fixes below are local, not released
or installed. The requested final numbering is manifest `3.90`, Git tag `v3.90`.
The existing beta version is deliberately unchanged until a release is ready.

## Evidence and limits

The Java decompilation is incomplete. Command constructors and relevant app
methods were also inspected in the preserved APK's `classes4.dex` and
`classes5.dex`. Source root: sibling directory `GARDENA Bluetooth App 9.2.0`.
Command classes are under
`com.gardena.libraries.bluetooth_mower.bluetooth_mower.mowerconnection.commands`;
the app's `device.BluetoothMower` methods identify which feature uses a command.
`ProtocolTypes.java` supplies the explicitly named enum values.

IDs below are decimal `major/minor`. “Wire match” means the app has the same
command identity and corresponding field layout. It does **not** establish that
every firmware supports it, that all presentation units are correct, or that a
physical setting has been round-trip tested. No commands were sent to the mower
during this audit. Only Eco/Frost have the user's current app-comparison result.
No APK or proprietary app implementation is added to the repository.

Inventory at audit start: 50 sensors, 8 binary sensors, 9 numbers, 4 selectors,
13 switches, 3 buttons, 1 lawn-mower entity and 1 calendar: **89 entity definitions**.
Some are conditional and will not exist on every mower. All appear below,
including the invalid Supported Accessories sensor removed by the local fix.

## Confirmed defects and local corrections

1. **Radar actually controlled ZoneProtect.** `GetAntiCollisionRadar` used
   `6050/4`; its setter used `6050/3`. The app calls these
   `MobileLoopCommands.GetAllSettings` and `SetEnabled` from
   `getZoneProtectSettings` / `setZoneProtectStatus`. Actual radar uses
   `ObstacleAvoidanceCommands`: read `5356/7`, write `5356/3`. The read layout is
   **available, enabled, useAtBoundary**, all booleans, in that order. Corrected
   locally without changing ZoneProtect settings or replaying previous writes.
2. **Generate Loop Signal had an unrelated, dangerous fallback.** Its primary
   `4692/2` is ChargingStation `InitiateNewPairing`, but fallback `5356/3` with
   zero is the obstacle-avoidance **disable** command. Removed the fallback and
   its alias. Unsupported pairing now returns an error instead of changing radar.
3. **Supported Accessories was collision status.** `4166/8` is
   `CollisionCommands.GetSensorStatus`, response `front:bool, rear:bool`, not an
   accessory bitmask. Removed that sensor and the invented bitmask derivation.
   Garage support now comes only from the actual garage-setting read.
   ZoneProtect support uses the `available` byte of `MobileLoop 6050/4`, read-only;
   it is neither the enabled value nor a collision bit. No speculative legacy
   fallback or new ZoneProtect control is introduced.
4. **SensorControl sensitivity labels were wrong.** App
   `IAutotimerSensitivity` is `0 very low, 1 low, 2 medium, 3 high, 4 very high`.
   The integration previously displayed/sent `0 low, 1 medium, 2 high`.
   Corrected all five labels/values. Existing mower values are not rewritten;
   automations selecting a named option will now send its correct app value.

Eco/Frost corrections from beta2 remain intact: Eco `4692/6` read, `4692/5`
write; Frost `5370/1,2`, with read-selected `5412/1,2` fallback only for explicit
unsupported results. No inversion and no lift-sensor-group fallback.

## Remaining release gates / findings

- **Calendar write payload:** app `CalendarCommands.AddTaskRequest` (`4690/7`)
  ends after seven weekday booleans. Upstream also sends `unknown:uint16 = 0`.
  This is a confirmed payload difference, not yet proof that a given firmware
  rejects it. Do not silently remove it across all models without resolving the
  legacy compatibility question and testing schedule read-back.
- **Calendar read failure:** upstream `get_tasks()` returns `[]` both for an
  empty calendar and failed count/task reads. HA create/update then replaces the
  full task list. A failed read could therefore discard existing schedules.
  This needs explicit failure propagation before destructive replacement.
- **Calendar edits can unpark:** upstream `set_tasks()` resumes scheduling after
  writing nonempty tasks if the mower was permanently parked. This is existing
  behavior, not a command-ID error. A calendar edit should not silently imply
  permission to start mowing; resolve and regression-test the desired behavior.
- **SpotCut restore can extend mowing:** `_restore_duration_hours()` reuses the
  original duration when the previous override has expired. Also, restoring a
  previously scheduled mowing activity currently creates a manual override.
  These are integration behavior issues, separate from the app's SpotCut IDs.
  Restoration should not create extra mowing time; needs targeted tests/fix.
- **Action confirmation:** lawn-mower pause/dock and some SpotCut/park restore
  paths do not consistently propagate every command/reconnect failure before
  optimistic state changes. Static command matching is not action validation.
- **Read diagnostics:** several optional pollers disable themselves after any
  failure rather than only unsupported results. Full unit/display parity,
  timestamp handling across DST, error text/model-name completeness, and the
  legacy-vs-new diagnostics selection still need completion as noted below.

These gates are deliberately not hidden behind passing unit tests. Do not
describe this audit as complete end-to-end validation or publish final `3.90`
while the remaining write-behavior issues are unresolved.

## Sensors — each definition

| Entity key | App command / field and integration interpretation | Result |
|---|---|---|
| battery_level | Battery 4106/20, uint8; percent | Wire match |
| activity | MowerApp 4586/3; enum 0–6 | Wire and enum match |
| state | MowerApp 4586/2; enum 0–8 | Wire and enum match |
| mode | MowerApp 4586/1; AUTO=0, MANUAL=1, HOME=2, DEMO=3 | Matches shared values; upstream POI=4 absent from this app enum |
| next_start_time | Planner 4658/1, tUnixTime; library converts mower local-clock epoch | Wire match; timezone/DST and sentinel semantics still require validation |
| RemainingChargingTime | Battery 4106/22, uint32; exposed seconds | Wire match; displayed time-unit parity not fully traced |
| batteryVoltage | Battery 4106/1, uint16; exposed mV | App voltage use case divides by 1000 for volts; equivalent scale. Indexed battery-generation variant exists at same ID; no blind fallback |
| batteryCurrent | Battery 4106/8, sint16; exposed mA | Wire match; signed value retained; generation-specific app paths exist |
| batteryTemperature | Battery 4106/9, sint16; exposed Celsius | Wire match; app use case passes integer through; full display calibration not proven |
| errorCode | MowerApp 4586/6, uint32 | Wire match |
| errorDescription | Local ErrorCodes lookup of errorCode; unknown values kept numeric | No independent command; exhaustive app error-text parity pending |
| NumberOfMessages | Message 4730/0, uint32 | Wire match |
| operatorstate | Operator 4664/3, bool (logged in) | Wire match; not physical operator presence |
| spotCutting | SpotCutting 4710/9, uint8 | Enum matches app: 0 not active, 1 idle, 2 pending start, 3 running |
| StartingPointChargingStationProportion | Local 100 minus enabled starting-point shares | Derived, not a separate read; enabled/share accounting needs behavior coverage |
| last_message | Message 4730/1, index 0; time uint32, code uint32, severity uint8 | Layout matches; ordering and exhaustive text lookup not fully validated |
| modelName | DeviceInformation 4698/9, device type + variant uint8; local name lookup | Wire match; full model-name table parity pending |
| mowerName | DeviceInformation 4698/3, UTF-16 name | Wire match; decoder handles UTF-16LE and null termination |
| serialNumber | DeviceInformation 4698/10, uint32 | Wire match |
| hardwareSerialNumber | System hardware 4758/4, ASCII | Wire match |
| hardwareRevision | System hardware 4758/5, uint16 | Wire match |
| productionTime | System hardware 4758/1, timestamp | Wire match; epoch/timezone display semantics not independently proven |
| nodeIprId | System hardware 4758/2, ASCII | Wire match |
| husqvarnaId | System hardware 4758/3, ASCII | Wire match |
| bootSoftwareVersion | Software version 4720/0, ASCII | Wire match |
| applicationSoftwareVersion | Software version 4720/1, ASCII | Wire match |
| subSoftwareVersion | Software version 4720/2, ASCII | Wire match |
| softwarePackageVersion | DeviceInformation 4698/22, ASCII | Wire match |
| pitch | Comboard 20/4, pitch sint16 | Wire match; exposed raw without angle unit |
| roll | Comboard 20/4, roll sint16 | Wire match; exposed raw without angle unit |
| mowerTemperature | Comboard 20/4, mowerTemperature sint16 | Wire match; Celsius scale needs independent display verification |
| orientationPitch | Orientation 4958/0, sint16 | Wire match; raw, not silently rescaled to degrees |
| orientationRoll | Orientation 4958/1, sint16 | Wire match; raw, not silently rescaled to degrees |
| signalQuality | Legacy diagnostics 20/21, quality uint8 | Layout match; legacy polling is skipped when app loop values are present; may be absent/stale |
| loopSignalStrength | LoopSignals 4462/14, selector 0, uint8 | Layout match; HA percent label and selector meaning need full app display trace |
| a0Signal | LoopSignals 4462/13, selector 0, first sint16; legacy 20/21 fallback | Wire layout matches; physical scale not asserted |
| fSignal | 4462/13 F sint16; legacy 20/21 F | Wire layout matches; physical scale not asserted |
| nSignal | 4462/13 N sint16; legacy 20/21 N | Wire layout matches; physical scale not asserted |
| guide1Signal | 4462/13 G1 sint16; legacy 20/21 G1 | Wire layout matches; physical scale not asserted |
| guide2Signal | 4462/13 G2 sint16; legacy 20/21 G2 | Wire layout matches; physical scale not asserted |
| guide3Signal | 4462/13 G3 sint16; legacy 20/21 G3 | Wire layout matches; physical scale not asserted |
| messageFromChargingStation | Legacy 20/21, uint16 | Layout match; raw code; same conditional polling limitation as signalQuality |
| supportedAccessories | Former 4166/8 uint16 accessory bitmask | **Wrong: collision front/rear booleans. Removed locally** |
| totalRunningTime | Statistics 4726/0 field 1, uint32; seconds | Layout match; full time-unit UI trace pending |
| totalCuttingTime | Statistics 4726/0 field 2, uint32; seconds | Layout match; full time-unit UI trace pending |
| totalChargingTime | Statistics 4726/0 field 3, uint32; seconds | Layout match; full time-unit UI trace pending |
| totalSearchingTime | Statistics 4726/0 field 4, uint32; seconds | Layout match; full time-unit UI trace pending |
| cuttingBladeUsageTime | Statistics 4726/0 field 7, uint32; divides by 3600 for hours | Layout match; conversion assumes seconds; counter can be reset |
| numberOfCollisions | Statistics 4726/0 field 5, uint32 | Wire match; count, not collision Boolean |
| numberOfChargingCycles | Statistics 4726/0 field 6, uint32 | Wire match; not Battery 4106/10 uint16 |

## Binary sensors — each definition

| Entity key | Command / derivation | Result |
|---|---|---|
| collision | Comboard 20/4 collision uint8 | Layout match; integration coerces nonzero to true, full byte semantics not proven |
| lift | Comboard 20/4 lift uint8 | Layout match; same nonzero coercion caveat |
| upsideDown | Comboard 20/4 upsideDown uint8 | Layout match; same nonzero coercion caveat |
| inChargingStation | Legacy 20/21 uint8 | Layout match; conditional legacy polling can leave this absent/stale |
| FrostSensorEnabled | Same read as Frost switch | Corrected in beta2; user confirmed app comparison |
| garageSupported | Successful Garage read 4692/4 | Removed collision-bit contribution locally; means command supported, not garage physically detected |
| zoneProtectSupported | MobileLoop 6050/4 available bool | **Corrected locally**, no collision bitmask; unknown stays unknown |
| AntiCollisionRadarAvailable | ObstacleAvoidance 5356/7 first bool | **Corrected locally**, distinct from ZoneProtect |

## Numbers — each definition

| Entity key | Read → write; units / range | Result |
|---|---|---|
| ManualMowingDuration | Local saved preference, 0.5–24 h in 0.5 h steps; later used by Planner override 4658/3 | Not a mower setting write when number changes; seconds conversion in start path |
| DrivePastWire | 4712/0 → 4712/1 distance uint16; cm ×10 on write | Wire and app divide/multiply-by-10 scaling match; integration range 0–35 cm not validated for all models |
| ReversingDistance | 4716/0 → 4716/1 distance uint16; cm ×10 on write | Wire and app scaling match; integration range 60–250 cm not validated for all models |
| StartingPoint1Distance | 4706/21 ID=1 → 4706/11 ID=1 distance uint16; 1–600 m | Wire match; model-specific limits and display scale need final verification |
| StartingPoint2Distance | 4706/21 ID=2 → 4706/11 ID=2 distance uint16; 1–600 m | Wire match; same model-limit caveat |
| StartingPoint3Distance | 4706/21 ID=3 → 4706/11 ID=3 distance uint16; 1–600 m | Wire match; same model-limit caveat |
| StartingPoint1Proportion | 4706/21 ID=1 → 4706/13 ID=1 proportion uint8; 0–100% | Wire match; aggregate validation includes disabled points, unlike derived station share |
| StartingPoint2Proportion | 4706/21 ID=2 → 4706/13 ID=2 proportion uint8; 0–100% | Wire match; same aggregate validation caveat |
| StartingPoint3Proportion | 4706/21 ID=3 → 4706/13 ID=3 proportion uint8; 0–100% | Wire match; same aggregate validation caveat |

## Selectors — each definition

| Entity key | Read → write / enum | Result |
|---|---|---|
| SensorControlSensitivity | Autotimer 4460/6 → 4460/7 sensitivity uint8 | **Five-value labels corrected locally**; no automatic setting rewrite |
| StartingPoint1Wire | 4706/21 ID=1 → 4706/9 ID=1 wire uint8 | Exposed 0 right, 1 left, 2/3/4 guide1/2/3 match app enum; unsupported guides not model-filtered |
| StartingPoint2Wire | 4706/21 ID=2 → 4706/9 ID=2 wire uint8 | Same enum match and model-filter limitation |
| StartingPoint3Wire | 4706/21 ID=3 → 4706/9 ID=3 wire uint8 | Same enum match; app enum CS=5 deliberately not offered as a guide option |

## Switches — each definition

| Entity key | Read → write / behavior | Result |
|---|---|---|
| spotCutting | Status 4710/9; prepare 4710/7; start 14/20; stop 14/24 | Command identities match app variants; **restore-duration/override behavior unresolved**, see gates |
| permanentPark | Mode 4586/1 and Planner 4658/2 override; HOME=2 vs AUTO=0/clear override | Shared IDs/enums match; command-result propagation needs coverage |
| SensorControlEnabled | Autotimer 4460/4 → 4460/5 bool | Wire match, direct Boolean |
| FrostSensorEnabled | 5370/1 → 5370/2 or supported 5412/1 → 5412/2 bool | Corrected in beta2, independent of Eco; user-confirmed app comparison |
| GarageEnabled | ChargingStation 4692/4 → 4692/3 bool; app MowerHouseInstalled | Wire match, direct Boolean; labeled Avoid Garage |
| AntiCollisionRadarEnabled | ObstacleAvoidance 5356/7 enabled → 5356/3 bool | **Corrected locally**; old 6050 commands controlled ZoneProtect |
| EcoMode | ChargingStation 4692/6 → 4692/5 bool | Corrected in beta2, direct Boolean; user-confirmed app comparison |
| StartingPoint1Enabled | 4706/21 ID=1 → 4706/7 ID=1 enabled bool | Wire match |
| StartingPoint2Enabled | 4706/21 ID=2 → 4706/7 ID=2 enabled bool | Wire match |
| StartingPoint3Enabled | 4706/21 ID=3 → 4706/7 ID=3 enabled bool | Wire match |
| StartingPoint1CorridorCut | 4706/21 ID=1 → 4706/27 ID=1 corridorCut bool | Wire match; model availability not established by ID alone |
| StartingPoint2CorridorCut | 4706/21 ID=2 → 4706/27 ID=2 corridorCut bool | Wire match; same model-availability caveat |
| StartingPoint3CorridorCut | 4706/21 ID=3 → 4706/27 ID=3 corridorCut bool | Wire match; same model-availability caveat |

## Buttons, mower and calendar — each definition

| Entity | Communication / semantics | Result |
|---|---|---|
| Diagnostic Refresh | Local coordinator requests diagnostic reads; no dedicated opcode | Does not intentionally change settings |
| Generate Loop Signal | ChargingStation InitiateNewPairing 4692/2, no arguments | Primary matches; **removed unrelated obstacle-disable fallback locally**; requires hardware pairing validation |
| Reset Cutting Blade Usage Time | Statistics 4726/8, no arguments | Wire match; intentionally resets blade counter only |
| Lawn mower | Battery/State/Activity; start uses AUTO + Planner 4658/3 duration seconds + start trigger; pause 4586/5; dock uses Planner 4658/5 | Shared IDs/enums match; optimistic state and failure handling gates remain |
| Schedule calendar | Calendar count 4690/4, get 5, add 7, delete all 9, transaction begin 10 / commit 11; start/duration seconds and Monday–Sunday flags | **Extra write bytes, failed-read ambiguity and automatic unpark remain release gates**. App time-picker explicitly converts hours/minutes to seconds |

## Verification and next steps

The local regression suite passes 57 tests, including six new tests covering
radar wire IDs and field order, separate ZoneProtect decoding/polling, removal of
unsafe aliases, the loop button's no-fallback behavior, and five sensitivity
labels. These use upstream serialization and lightweight HA collaborators,
not a full running-HA/hardware integration test.

Next: resolve the remaining schedule/action behavior and semantic checks above;
add targeted regression tests; compare affected supported settings in the app
without touching safety sensors, resetting pairing or starting mowing as a
test. Check HA's version parser and exact tag/manifest equality on the final
artifact. Only then create **v3.90 / manifest 3.90**. Do not move existing tags.
