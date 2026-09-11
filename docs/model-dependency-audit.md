# Model-dependency audit — all mower entity definitions

## Follow-up after Minimo stable 3.90

The September 12 decision is to release the Minimo settings corrections first,
then implement every model-dependent finding below in a separate version.
`next-version-checklist.md` tracks that work. References below to the "current
draft" describe the audited pre-3.90 snapshot; 3.90 corrects the Minimo sensitivity
choices and distance bounds but does not implement the cross-model capability map.
The owner's tested SpotCut sequence is deliberately retained in 3.90.

App resource names identify P0 as SILENO city/life, P005 as SILENO minimo,
P005GA as SILENO flex, and P14 as SILENO pro/max. Do not infer numeric P14 device
IDs from the repository's default branch; establish accepted identities first.

## Scope and result

Read-only static review of retained GARDENA Bluetooth App 9.2.0, against the
integration draft based on commit 7115113. The Java output is incomplete, so
classes4.dex and classes5.dex were inspected directly, indexing 25,859 methods
under the app's mower feature and Bluetooth-mower library. Existing September 11
snoop evidence was used as a cross-check for the owner's mower, not as proof
about other models.

Every one of the original **89 entity definitions** is listed individually below:
50 sensors, 8 binary sensors, 9 numbers, 4 selects, 13 switches, 3 buttons,
1 mower and 1 calendar. This includes the invalid accessory sensor removed from
the local draft. Five-point platforms reveal missing point 4/5 entities outside
that original inventory.

**Result: the current draft does not reproduce the app's cross-model behavior.**
There are confirmed differences in available controls, bounds, point counts,
firmware-specific command selection, diagnostics and action sequences.

“Shared read” means no model branch was found in the identified app read path;
it is not an all-firmware support guarantee. “Support not established” means
command definitions alone were insufficient to resolve the model-availability
question. Those rows are deliberately not marked universally compatible.
This is an entity-by-entity static review, not physical validation of every model.
No integration code, installed settings, mower state, Git tag or release changed
during this audit.

## A. Platform and generation identity

Source: `DefaultMowerRepository.getMowerPlatform/getMowerGeneration`.

| Numeric device type | App platform | App generation |
|---|---|---|
| 14, 18, 22, 25 | P0 | 3 |
| 29, 30 | P005 | 4 |
| 43 | P005GA | 4 |
| Other types reaching the repository | P14 default | 4 default |

These defaults operate within the app's accepted-device context. Do not classify
an arbitrary unknown device as fully capable P14 merely because it misses the
first cases. A capability layer must preserve unknown identity, distinguish
model type from variant, and avoid marketing-name string matching.

## B. Confirmed capability and range rules

| Feature | P0 | P005 | P005GA | P14 |
|---|---|---|---|---|
| SensorControl choices | Low=1, Medium=2, High=3 | Same three | Very low=0 through Very high=4 | Same five |
| Starting-point count | 3 | 3 | 5 | 5 |
| Drive Past Wire | 20–40 cm | 20–35 cm | 20–35 cm | 25–40 cm |
| Charging-station starting distance | 20–300 cm | 60–300 cm | 60–300 cm | 60–300 cm |
| Garage UI capability | Yes | Yes | Yes | No |
| Radar platform capability | No | No | No | Yes, plus device availability |

Sources: `SensorControlViewModel.getSensitivityLevels`,
`GetNumberOfStartingPoints.invoke`,
`GetDrivePastWireMinMaxUseCase.execute`,
`GetDrivePastWireCapabilities`,
`GetCSStartingPointMinValueUseCase.execute`,
`GetReversingDistanceCapabilities`,
`charging_station.State.Update` (300 cm default maximum),
`GetGarageSettingAvailableUseCase.execute`, `GetACRCapability.execute`.

The integration currently uses 0–35 cm for Drive Past Wire, 60–250 cm for the
charging-station distance, three starting points and a universal wire-option
list. These are not the app's rules. The local five-level sensitivity correction
also needs platform filtering.

Frost help text is platform-specific too:
`ChargingToggleHelper.Companion.setTextForMode` describes 3°C for P14 and 5°C
for other platforms. This is app explanatory text, not permission to change a
hardware safety threshold, and does not imply our Frost Boolean has another
encoding.

## C. Starting points and guide arrangement

Sources: `GetStartingPointsUseCase`, `HasTwoGuideWireUseCase`,
`SetStartingPointEnabledUseCase`, related editor view models.

- P0 uses individual enabled/proportion/distance reads in
  `getStartingPointsG3`, not the same combined-settings path as P005.
- P005 uses `getStartingPointsOBP`, iterating three points with combined settings
  and a separate CorridorCut read.
- P005GA/P14 use `getStartingPointsP14`, iterating five.
- `HasTwoGuideWireUseCase` returns:
  - P005GA: `SupportsTwoGuidesWithoutBoundary`.
  - P14 + Gardena brand: `SupportsTwoGuidesWithBoundary`.
  - P14 + Flymo brand: `SupportsBoundaryGuide`.
  - Otherwise: `SupportsOnlyGuide`.
- The protocol's right/left/guide1/guide2/guide3 enum is not a declaration that
  every mower physically offers all five choices.
- Point enable writes have additional generation-3 workflow logic. Adding a
  combined read fallback alone does not establish full app behavior.
- Station mowing share must include every enabled supported point. Reading
  only three points on a five-point mower can give the wrong remaining share.
- No model-specific change to the underlying distance/proportion wire scale was
  found. Complete model-specific distance-editor validation and the extra G3
  enable side effects remain implementation-level follow-up, not guessed rules.

## D. Firmware-selected settings

Sources: `MowerVersionRegexKt`, corresponding Get/Set use cases, and the
request constructors selected by `BluetoothMower`.

| Feature | P0 selection in app | Other known platforms |
|---|---|---|
| Frost | Main version above 20.28: 5370; at/below 20.28: 5412 | 5370 |
| ZoneProtect | First two main-version digits below 41: 6050; 41 or above: 5926 | 6050 |
| CorridorCut | First two main-version digits below 41: read/write 4706/26,27; 41 or above: 4706/24,25 | 4706/26,27 |

These are the observed app helper branches, not assumptions that larger command
numbers mean newer firmware. Both Frost groups use read 1/write 2; both
ZoneProtect groups use all-settings read 4/write 3. ZoneProtect all-settings
contains enabled uint8 then available bool.

The app parses fixed portions of the main-version string. It has special
short-string handling in some helpers, not a uniformly robust version parser.
Do not blindly reproduce malformed-version behavior in HA. A safe implementation
needs validated version input, a conservative unknown case, and tests for boundary
versions. Unsupported read results can provide additional evidence, but writes
must never be used to probe a candidate command group.

The local draft correctly separates Eco/Frost and radar/ZoneProtect, but the
ZoneProtect reader currently covers only 6050. CorridorCut currently covers only
26/27. Frost's read-selected fallback is not identical to the app's version gate,
especially if firmware accepts more than one group.

## E. Diagnostics: generation and presentation differences

Sources: `GetBatteryVoltageUseCase`, `GetBatteryCurrentUseCase`,
`GetBatteryTemperatureUseCase`, `GetCollisionSensorStatusUseCase`,
`GetLiftSensorStatusUseCase`, `GetPitchAngleUseCase`, `GetRollAngleUseCase`,
`GetLoopSignalStrengthUseCase`, `GetLoopSignalsUseCase`.

- Battery voltage: P0 returns null in the reviewed UI use case. Other platforms
  read the battery value and divide by 1000 for volts.
- Battery current/temperature: generation 4 reads the device; other generations
  return the app's internal 999999 sentinel. That is not a measurement and
  must not be copied into HA as one. Separate G3 battery commands exist in the
  library, but their existence does not mean these UI paths use them.
- Collision/lift: G3 uses Comboard 20/4; G4 uses Collision 4166/8 and
  LiftSensor 4476/6. Correctly combining the separate modern collision fields
  needs explicit semantics, not an accessory bitmask.
- Pitch/roll: G3 Comboard fields versus G4 Orientation 4958/0,1. The app
  display path divides values by 10. Our separate raw sensors should either
  remain explicitly raw or adopt verified units/scaling.
- Loop strength: G3 legacy signal-quality read 20/21; G4 averages front-center
  and rear-center 4462/14 reads. Our selector-0-only value is not necessarily
  the app's combined indication.
- Loop signal components: G3 legacy 20/21 versus G4 front-center 4462/13.
  Guide count/arrangement remains a separate capability question.
- App statistics use individual reads (4726/1–6). Our aggregate read 4726/0
  must have its own capability/error handling; matching individual commands
  does not validate every aggregate layout on every mower.

Several extra HA diagnostics have command definitions but no fully traced app
availability rule. They remain explicitly unresolved in the table.

## F. Mower actions and SpotCut

Sources: `ParkMowerPermanentlyUseCase`, `StartSpotCutUseCase`,
`StopSpotCutUseCase`, `GetMowerStatusUseCase.getMowingFromAction`,
`BluetoothMower.parkPermanently/startSpotCut/startSpotCutG3/stopSpotCut/stopSpotCutG3`
including their nested flow handlers.

- Permanent park on G3: HOME + start trigger.
- Permanent park on other generations: HOME + clear override + start trigger.
  The Boolean passed by the use case selects whether clear override is included.
- SpotCut status: G3 uses DrivingSettings 4/13; non-G3 uses SpotCutting 4710/9.
- SpotCut stop: G3 uses MowerApp 14/24; non-G3 uses SpotCutting abort 4710/8.
  The integration's current stop path uses 14/24, so it does not match the
  app's non-G3 path even though the command may be accepted by some firmware.
- The start workflows differ too: both pause/set AUTO, but the G3 nested path
  includes a Planner mowing override and StartSpotCutting command; non-G3 uses
  SpotCutting start-trigger followed by the MowerApp start trigger.
- Dashboard visibility calls `SpotCutCapabilityUseCase`: it allows P0/P005,
  excludes P14/P005GA in that context. A different
  `MowerCapabilities.hasSpotCutCapability → GetSpotCutAvailable` path selects
  P14. These are different app consumers; do not mistake one helper for a
  universal visibility rule.

None of these findings authorizes an automatic movement test. Existing restore
logic that can extend mowing after SpotCut remains a separate release issue.

## G. Calendar

Sources: `GetSchedulingCapabilities`, `GetScheduleUseCase`,
`SetScheduleUseCase`, `DeleteSessionUseCase`, `ScheduleOverviewViewModel`.

| Generation | Maximum schedules | Per-day capability return | Delete last schedule |
|---|---:|---:|---|
| 3 | 14 | 2 | Not directly allowed |
| 4 | 15 | 0 sentinel | Allowed |

Do not interpret the zero capability value as “no schedules allowed.” Its
consumer has separate scheduling logic. The deletion use case has G3-specific
replacement handling, so a universal delete-all operation is not app parity.

The same Calendar command family is used in the reviewed paths. The owner's
G4 capture proves successful 15-byte AddTask writes; it does not validate all G3
write behavior. Failed reads masquerading as an empty calendar, partial-write
recovery and unintended unparking remain independent problems to fix.
The previous capture did not test a permanently parked mower.

## H. Loop generation

`LoopSignalViewModel → BluetoothMower.newLoopSignal` uses ChargingStation
4692/2, with no model-specific alternative generation opcode found in that path.
The app also registers pairing-success and pairing-failure events. Therefore
command acceptance and finished pairing are different states. The owner's capture
already confirms accepted 4692/2; no new loop-generation test is requested.
Platform-specific help screens do not imply a different command.
The removed obstacle-avoidance fallback must remain removed.

## Individual entity inventory

References A–H point to the evidence and rules above. Entries saying
“not established” are unresolved availability checks, not positive compatibility
claims.

| Platform | Entity key | Classification | Finding / consequence |
|---|---|---|---|
| sensor | battery_level | Shared read | Battery 4106/20; BluetoothMower.getBatteryLevel has no model branch found. Capability on every firmware is not established. |
| sensor | activity | Shared raw; derived UI varies | MowerApp 4586/3 enum unchanged; GetMowerStatusUseCase derives richer statuses using generation/platform and SpotCut. |
| sensor | state | Shared raw; derived UI varies | MowerApp 4586/2; app status and safety-PIN handling include generation branches; do not copy UI state derivation from one model. |
| sensor | mode | Shared raw; actions vary | MowerApp 4586/1 enum shared; permanent-park sequence differs by generation (F). |
| sensor | next_start_time | Shared read; derived behavior | Planner 4658/1 shared; app next-start/status interpretation combines schedule/restrictions. No model-specific wire encoding found; DST is a separate unresolved issue. |
| sensor | RemainingChargingTime | Shared read | Battery 4106/22 via getRemainingChargingTime; no model branch found in that read, not a guarantee of all-model support. |
| sensor | batteryVoltage | Platform-dependent availability | GetBatteryVoltageUseCase returns null for P0; otherwise reads 4106/1 and divides by 1000 for volts (E). |
| sensor | batteryCurrent | Generation-dependent availability | GetBatteryCurrentUseCase reads 4106/8 only for generation 4; otherwise returns internal sentinel 999999 (E). Do not display sentinel as a measurement. |
| sensor | batteryTemperature | Generation-dependent availability | GetBatteryTemperatureUseCase reads 4106/9 only for generation 4; otherwise returns internal sentinel 999999 (E). |
| sensor | errorCode | Shared raw; interpretation varies | MowerApp 4586/6 read shared; app GetErrorUseCase and ErrorDescriptionHelper have generation/platform handling. |
| sensor | errorDescription | Platform/generation-dependent presentation | ErrorDescriptionHelper.getBody/getHint branch by model platform/generation. Our generic enum text is not full app-specific advice. |
| sensor | NumberOfMessages | Shared read | Messages 4730/0 via getNumberOfMessages; no model-specific command branch found. |
| sensor | operatorstate | Shared protocol diagnostic | Operator 4664/3 logged-in Boolean, not physical presence; app login/safety-PIN workflows are platform-dependent. No alternate Boolean encoding established. |
| sensor | spotCutting | Generation-dependent | App reads DrivingSettings 4/13 on generation 3, SpotCutting 4710/9 otherwise. Different enum semantics; do not use one status map blindly (F). |
| sensor | StartingPointChargingStationProportion | Platform-dependent derivation | Must account for all 3 or 5 active points, not only first three; app G3 read strategy also differs (C). |
| sensor | last_message | Shared read; presentation varies | 4730/1 message layout shared; generic description must not claim the app's platform-specific troubleshooting text. |
| sensor | modelName | Model-dependent lookup | Device model type/variant 4698/9 is the identity source. Use numeric identity for capabilities; never infer from a translated/unknown modelName string (A). |
| sensor | mowerName | Shared read; model-dependent editing limits | 4698/3 name read is shared. GetNameMaxLengthUseCase branches by generation/platform, but this integration entity is read-only. |
| sensor | serialNumber | Shared read | 4698/10 via getSerialNumber; no model-specific read branch found. |
| sensor | hardwareSerialNumber | Support not established | 4758/4 command exists; no complete user-facing app capability/availability path established for this integration diagnostic. |
| sensor | hardwareRevision | Support not established | 4758/5 command exists; no complete app model-availability rule established. |
| sensor | productionTime | Support not established | 4758/1 command exists; no complete app model-availability rule or display-time interpretation established. |
| sensor | nodeIprId | Support not established | 4758/2 command exists; not evidence that this diagnostic is universally supported. |
| sensor | husqvarnaId | Support not established | 4758/3 command exists; not evidence that this diagnostic is universally supported. |
| sensor | bootSoftwareVersion | Support not established | 4720/0 command exists; no complete app feature/availability gate traced for this extra diagnostic. |
| sensor | applicationSoftwareVersion | Shared read; platform-specific interpretation | 4720/1 via getMainAppVersion; parsed with platform-specific firmware rules for Frost/ZoneProtect/CorridorCut (D). |
| sensor | subSoftwareVersion | Support not established | 4720/2 command exists; no complete app feature/availability gate traced for this extra diagnostic. |
| sensor | softwarePackageVersion | Shared read | 4698/22 via GetSWPackageUseCase/getSWPackage; app handles absent result; do not equate missing value with unsupported model. |
| sensor | pitch | Generation-dependent source | App generation 3 reads Comboard 20/4; generation 4 reads Orientation 4958/0. HA raw pitch is only the Comboard field (E). |
| sensor | roll | Generation-dependent source | App generation 3 reads Comboard 20/4; generation 4 reads Orientation 4958/1. HA raw roll is only the Comboard field (E). |
| sensor | mowerTemperature | Support not established | Extra Comboard 20/4 field. App's battery temperature is a different diagnostic; universal mower-temperature availability not established. |
| sensor | orientationPitch | Generation-dependent source/display | App generation 4 uses 4958/0; app pitch display divides raw by 10. Our sensor exposes raw unscaled data without degrees (E). |
| sensor | orientationRoll | Generation-dependent source/display | App generation 4 uses 4958/1; app roll display divides raw by 10. Our sensor exposes raw unscaled data without degrees (E). |
| sensor | signalQuality | Generation-dependent source | App generation 3 uses RealTimeData 20/21; generation 4 uses LoopSystem 4462/14 (E). |
| sensor | loopSignalStrength | Generation-dependent source/aggregation | App generation 4 averages front-center and rear-center 4462/14 reads; ours reads selector 0 only. G3 uses legacy signal quality (E). |
| sensor | a0Signal | Generation-dependent source | GetLoopSignalsUseCase uses legacy 20/21 on G3, front-center 4462/13 otherwise; raw signal, not a percentage (E). |
| sensor | fSignal | Generation-dependent source | Same legacy/new loop path as a0Signal; F field (E). |
| sensor | nSignal | Generation-dependent source | Same legacy/new loop path as a0Signal; N field (E). |
| sensor | guide1Signal | Generation-dependent source/capability | Same legacy/new loop path; physical guide arrangement is platform/brand-dependent (C/E). |
| sensor | guide2Signal | Generation-dependent source/capability | Shared raw field does not imply a second guide exists; HasTwoGuideWireUseCase filters arrangement (C/E). |
| sensor | guide3Signal | Generation-dependent source/capability | Protocol field exists, but reviewed Gardena platform rules do not establish a third usable guide. Do not infer hardware capability (C/E). |
| sensor | messageFromChargingStation | Legacy diagnostic; support uncertain | Legacy 20/21 field; no model-general app presentation path found. Conditional legacy polling can leave it absent/stale. |
| sensor | supportedAccessories | Invalid entity, removed in draft | 4166/8 is collision front/rear status, not a capability mask. No model justifies the old interpretation. |
| sensor | totalRunningTime | Shared read; aggregate support uncertain | App GetTotalRunningTimeUseCase → 4726/1 without model branch; integration uses aggregate 4726/0. Aggregate support cannot be inferred from individual-read support. |
| sensor | totalCuttingTime | Shared read; aggregate support uncertain | App GetTotalCuttingTimeUseCase → 4726/2; integration aggregate 4726/0 requires its own support handling. |
| sensor | totalChargingTime | Shared read; aggregate support uncertain | App GetTotalChargingTimeUseCase → 4726/3; integration aggregate 4726/0 requires its own support handling. |
| sensor | totalSearchingTime | Shared read; aggregate support uncertain | App GetTotalSearchingTimeUseCase → 4726/4; integration aggregate 4726/0 requires its own support handling. |
| sensor | cuttingBladeUsageTime | Support not established | 4726/0 field and 4726/7 command exist; no complete app model-gated blade-counter UI path established. Keep reset semantics separate. |
| sensor | numberOfCollisions | Shared read; aggregate support uncertain | App getTotalCollisions → 4726/5; integration aggregate 4726/0. Not the live collision Boolean. |
| sensor | numberOfChargingCycles | Shared read; aggregate support uncertain | App getBatteryCharges → 4726/6; integration aggregate 4726/0. Different from battery-specific uint16 cycle command. |
| binary_sensor | collision | Generation-dependent | G3 Comboard 20/4; G4 Collision 4166/8 front/rear fields. Our single Comboard Boolean is not the app's universal source (E). |
| binary_sensor | lift | Generation-dependent | G3 Comboard 20/4; G4 LiftSensor 4476/6. Our single Comboard source is not universal (E). |
| binary_sensor | upsideDown | Legacy diagnostic; support uncertain | Comboard 20/4 field; no equivalent complete app cross-model entity gate established. |
| binary_sensor | inChargingStation | Legacy diagnostic; support uncertain | 20/21 field; app charging/activity status is not proof of this field's availability on every model. |
| binary_sensor | FrostSensorEnabled | Platform/firmware-dependent | 5370 versus 5412 selected from platform/main firmware; same direct Boolean. Both binary sensor and switch inherit this rule (D). |
| binary_sensor | garageSupported | Platform-dependent | App GetGarageSettingAvailableUseCase allows P0/P005/P005GA, not P14. Successful read and physical garage presence are different concepts (B). |
| binary_sensor | zoneProtectSupported | Platform/firmware-dependent | App uses 6050 or legacy 5926 plus returned availability; current draft only handles 6050 (D). |
| binary_sensor | AntiCollisionRadarAvailable | Platform plus capability-dependent | GetACRCapability selects P14; ObstacleAvoidance settings also provide available. ZoneProtect availability must never substitute (B). |
| number | ManualMowingDuration | Local preference | No mower write when number changes. Later explicit start converts hours to override duration; generation-dependent start/park policy is separate (F). |
| number | DrivePastWire | Platform-dependent range | P0 20–40 cm; P005/P005GA 20–35 cm; P14 25–40 cm. Current fixed 0–35 cm disagrees (B). |
| number | ReversingDistance | Platform-dependent range | P0 20–300 cm; other known platforms 60–300 cm. Current fixed 60–250 cm disagrees (B). |
| number | StartingPoint1Distance | Platform-dependent point set/read path | ID 1: app uses three points on P0/P005, five on P005GA/P14; P0 individual reads, others combined reads. No alternate distance scaling found; complete editor limits unresolved (C). |
| number | StartingPoint2Distance | Platform-dependent point set/read path | ID 2: app uses three points on P0/P005, five on P005GA/P14; P0 individual reads, others combined reads. No alternate distance scaling found; complete editor limits unresolved (C). |
| number | StartingPoint3Distance | Platform-dependent point set/read path | ID 3: app uses three points on P0/P005, five on P005GA/P14; P0 individual reads, others combined reads. No alternate distance scaling found; complete editor limits unresolved (C). |
| number | StartingPoint1Proportion | Platform-dependent point set/validation | ID 1: same point-count/read-path rule; percentage uint8 unchanged. Aggregate share must include all supported points (C). |
| number | StartingPoint2Proportion | Platform-dependent point set/validation | ID 2: same point-count/read-path rule; percentage uint8 unchanged. Aggregate share must include all supported points (C). |
| number | StartingPoint3Proportion | Platform-dependent point set/validation | ID 3: same point-count/read-path rule; percentage uint8 unchanged. Aggregate share must include all supported points (C). |
| select | SensorControlSensitivity | Platform-dependent choices | P0/P005: 1/2/3; P005GA/P14: 0/1/2/3/4. Keep labels fixed and filter choices (B). |
| select | StartingPoint1Wire | Platform/brand-dependent choices | ID 1: HasTwoGuideWireUseCase chooses guide/boundary arrangement. Current universal right/left/guide1/2/3 list is not app parity (C). |
| select | StartingPoint2Wire | Platform/brand-dependent choices | ID 2: HasTwoGuideWireUseCase chooses guide/boundary arrangement. Current universal right/left/guide1/2/3 list is not app parity (C). |
| select | StartingPoint3Wire | Platform/brand-dependent choices | ID 3: HasTwoGuideWireUseCase chooses guide/boundary arrangement. Current universal right/left/guide1/2/3 list is not app parity (C). |
| switch | spotCutting | Generation/platform-dependent | Dashboard capability differs by platform; G3/G4 start, status and stop paths differ. Current stop 14/24 is the G3 path; app non-G3 uses 4710/8 (F). |
| switch | permanentPark | Generation-dependent sequence | App sends HOME + start trigger for G3, HOME + clear override + start trigger otherwise (F). |
| switch | SensorControlEnabled | Shared Boolean path | Get/SetSensorControlUseCase use Autotimer 4460/4,5 directly. No model-dependent Boolean mapping found; sensitivity choice filtering is separate. |
| switch | FrostSensorEnabled | Platform/firmware-dependent | 5370 versus 5412 selected from platform/main firmware; same direct Boolean. Both binary sensor and switch inherit this rule (D). |
| switch | GarageEnabled | Platform-dependent availability | App garage setting excluded for P14; direct bool read/write 4692/4,3 on allowed platforms (B). |
| switch | AntiCollisionRadarEnabled | Platform plus capability-dependent | App P14 capability, availability Boolean, then 5356/3 write. Current draft fixes identity but lacks complete app platform gate (B). |
| switch | EcoMode | Shared Boolean path | ChargingStation 4692/6,5; no model-dependent inversion/opcode found in reviewed app path. |
| switch | StartingPoint1Enabled | Platform/generation-dependent | ID 1: point count/read path varies; SetStartingPointEnabledUseCase has extra G3 behavior. Do not assume one isolated write reproduces the whole app workflow (C). |
| switch | StartingPoint2Enabled | Platform/generation-dependent | ID 2: point count/read path varies; SetStartingPointEnabledUseCase has extra G3 behavior. Do not assume one isolated write reproduces the whole app workflow (C). |
| switch | StartingPoint3Enabled | Platform/generation-dependent | ID 3: point count/read path varies; SetStartingPointEnabledUseCase has extra G3 behavior. Do not assume one isolated write reproduces the whole app workflow (C). |
| switch | StartingPoint1CorridorCut | Platform/firmware-dependent | ID 1: 4706/26,27 versus 4706/24,25; also constrained by chosen wire/point and capability. Current single command pair is incomplete (C/D). |
| switch | StartingPoint2CorridorCut | Platform/firmware-dependent | ID 2: 4706/26,27 versus 4706/24,25; also constrained by chosen wire/point and capability. Current single command pair is incomplete (C/D). |
| switch | StartingPoint3CorridorCut | Platform/firmware-dependent | ID 3: 4706/26,27 versus 4706/24,25; also constrained by chosen wire/point and capability. Current single command pair is incomplete (C/D). |
| button | diagnostic_refresh | Local action; dependent downstream reads | No dedicated model opcode; must refresh only the correct supported diagnostics for the model (E). |
| button | generate_loop_signal | Shared command; completion protocol matters | BluetoothMower.newLoopSignal uses 4692/2 for reviewed app paths, then pairing-success/failure events. No alternative model-specific generation command found (H). |
| button | reset_cutting_blade_usage_time | Support not established | 4726/8 is a real reset command, but full app model-specific availability path is not established. Do not probe support by resetting. |
| lawn_mower | Mower | Shared raw reads; generation-dependent actions | Pause/start base IDs shared, but permanent-park/SpotCut and derived status workflows differ. Don't generalize the Minimo sequence (F). |
| calendar | Schedule | Generation-dependent limits/last deletion | App G3: 14 slots, two/day, last schedule cannot simply be deleted. G4: 15 slots, per-day limit sentinel 0, last deletion allowed. Shared Calendar command family; write safety remains separate (G). |

## Implementation follow-up, not performed by this review

1. Centralize verified numeric identity → platform/generation → capability rules;
   represent unknown identity explicitly.
2. Filter sensitivity/wire choices and use platform-specific numeric bounds.
3. Support the app's point count/read strategy and firmware-specific setting pairs.
4. Select diagnostic sources and preserve unknown/unavailable separately from false.
5. Correct generation-specific SpotCut/park behavior with tests that never actuate
   hardware; fix the independent calendar/restore safety problems.
6. Add fixtures for every confirmed branch and firmware boundary, then obtain
   representative hardware/app read-back on additional supported platforms.
   No amount of testing on a Minimo proves another model's hardware behavior.

This report completes the requested per-entity classification pass, but does not
resolve every row marked “support not established” or certify every firmware.
The original broad release was held at the time of the audit. See the September
12 scope decision at the top: Minimo-only corrections ship as manifest 3.90,
tag v3.90, while this cross-model work remains outstanding.
