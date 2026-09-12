# Entity implementation review

All 89 entries from the original audit are accounted for below. This is a code-policy review,
not physical verification of every model. The original audit remains the wire/evidence
reference. Optional extra diagnostics have runtime support, not invented app capability
rules. Full manufacturer troubleshooting text and unknown marketing capacities are not
ported; conservative fallbacks are documented in model-implementation-progress.md.

| Platform | Original entity key | Current implementation policy |
|---|---|---|
| sensor | battery_level | Shared read; missing/failed data is not a universal-support claim. |
| sensor | activity | Shared read; missing/failed data is not a universal-support claim. |
| sensor | state | Shared read; missing/failed data is not a universal-support claim. |
| sensor | mode | Shared read; missing/failed data is not a universal-support claim. |
| sensor | next_start_time | Local-wall-clock timestamp with DST gap/fold/sentinel rejection. |
| sensor | RemainingChargingTime | Shared read; missing/failed data is not a universal-support claim. |
| sensor | batteryVoltage | Generation-selected source; unknown/sentinel handling; guide channels filtered. |
| sensor | batteryCurrent | Generation-selected source; unknown/sentinel handling; guide channels filtered. |
| sensor | batteryTemperature | Generation-selected source; unknown/sentinel handling; guide channels filtered. |
| sensor | errorCode | Shared read; missing/failed data is not a universal-support claim. |
| sensor | errorDescription | P14 error 38 override; generic short labels/numeric fallback, app troubleshooting retained. |
| sensor | NumberOfMessages | Shared read; missing/failed data is not a universal-support claim. |
| sensor | operatorstate | Shared read; missing/failed data is not a universal-support claim. |
| sensor | spotCutting | G3/G4 status and action adapters; P005 sequence retained; P14/flex availability gate. |
| sensor | StartingPointChargingStationProportion | Supported point count, generation-selected reads, validated writes/share accounting. |
| sensor | last_message | Short label and raw fields; timestamp clock explicitly unverified. |
| sensor | modelName | Upstream name or verified platform/type/variant fallback; no invented capacity. |
| sensor | mowerName | Shared read; missing/failed data is not a universal-support claim. |
| sensor | serialNumber | Shared read; missing/failed data is not a universal-support claim. |
| sensor | hardwareSerialNumber | Optional read-only diagnostic; runtime support only. No model capability invented. |
| sensor | hardwareRevision | Optional read-only diagnostic; runtime support only. No model capability invented. |
| sensor | productionTime | Optional raw timestamp; no unverified UTC conversion. |
| sensor | nodeIprId | Optional read-only diagnostic; runtime support only. No model capability invented. |
| sensor | husqvarnaId | Optional read-only diagnostic; runtime support only. No model capability invented. |
| sensor | bootSoftwareVersion | Optional read-only diagnostic; runtime support only. No model capability invented. |
| sensor | applicationSoftwareVersion | Shared read; missing/failed data is not a universal-support claim. |
| sensor | subSoftwareVersion | Optional read-only diagnostic; runtime support only. No model capability invented. |
| sensor | softwarePackageVersion | Shared read; missing/failed data is not a universal-support claim. |
| sensor | pitch | Generation-selected source; unknown/sentinel handling; guide channels filtered. |
| sensor | roll | Generation-selected source; unknown/sentinel handling; guide channels filtered. |
| sensor | mowerTemperature | Optional read-only diagnostic; runtime support only. No model capability invented. |
| sensor | orientationPitch | Generation-selected source; unknown/sentinel handling; guide channels filtered. |
| sensor | orientationRoll | Generation-selected source; unknown/sentinel handling; guide channels filtered. |
| sensor | signalQuality | Generation-selected source; unknown/sentinel handling; guide channels filtered. |
| sensor | loopSignalStrength | Generation-selected source; unknown/sentinel handling; guide channels filtered. |
| sensor | a0Signal | Generation-selected source; unknown/sentinel handling; guide channels filtered. |
| sensor | fSignal | Generation-selected source; unknown/sentinel handling; guide channels filtered. |
| sensor | nSignal | Generation-selected source; unknown/sentinel handling; guide channels filtered. |
| sensor | guide1Signal | Generation-selected source; unknown/sentinel handling; guide channels filtered. |
| sensor | guide2Signal | Generation-selected source; unknown/sentinel handling; guide channels filtered. |
| sensor | guide3Signal | Generation-selected source; unknown/sentinel handling; guide channels filtered. |
| sensor | messageFromChargingStation | Optional read-only diagnostic; runtime support only. No model capability invented. |
| sensor | supportedAccessories | Removed: incorrect alias of collision status. |
| sensor | totalRunningTime | Independent app statistics reads; optional aggregate failure cannot suppress these. |
| sensor | totalCuttingTime | Independent app statistics reads; optional aggregate failure cannot suppress these. |
| sensor | totalChargingTime | Independent app statistics reads; optional aggregate failure cannot suppress these. |
| sensor | totalSearchingTime | Independent app statistics reads; optional aggregate failure cannot suppress these. |
| sensor | cuttingBladeUsageTime | Optional read-only diagnostic; runtime support only. No model capability invented. |
| sensor | numberOfCollisions | Independent app statistics reads; optional aggregate failure cannot suppress these. |
| sensor | numberOfChargingCycles | Independent app statistics reads; optional aggregate failure cannot suppress these. |
| binary_sensor | collision | Generation-selected source; unknown/sentinel handling; guide channels filtered. |
| binary_sensor | lift | Generation-selected source; unknown/sentinel handling; guide channels filtered. |
| binary_sensor | upsideDown | Optional read-only diagnostic; runtime support only. No model capability invented. |
| binary_sensor | inChargingStation | Optional read-only diagnostic; runtime support only. No model capability invented. |
| binary_sensor | FrostSensorEnabled | App firmware-selected command family and strict Boolean/availability handling. |
| binary_sensor | garageSupported | Platform plus runtime availability; radar and ZoneProtect remain separate. |
| binary_sensor | zoneProtectSupported | App firmware-selected command family and strict Boolean/availability handling. |
| binary_sensor | AntiCollisionRadarAvailable | Platform plus runtime availability; radar and ZoneProtect remain separate. |
| number | ManualMowingDuration | Model-filtered choices/bounds and stale-entity outbound guards. |
| number | DrivePastWire | Model-filtered choices/bounds and stale-entity outbound guards. |
| number | ReversingDistance | Model-filtered choices/bounds and stale-entity outbound guards. |
| number | StartingPoint1Distance | Supported point count, generation-selected reads, validated writes/share accounting. |
| number | StartingPoint2Distance | Supported point count, generation-selected reads, validated writes/share accounting. |
| number | StartingPoint3Distance | Supported point count, generation-selected reads, validated writes/share accounting. |
| number | StartingPoint1Proportion | Supported point count, generation-selected reads, validated writes/share accounting. |
| number | StartingPoint2Proportion | Supported point count, generation-selected reads, validated writes/share accounting. |
| number | StartingPoint3Proportion | Supported point count, generation-selected reads, validated writes/share accounting. |
| select | SensorControlSensitivity | Model-filtered choices/bounds and stale-entity outbound guards. |
| select | StartingPoint1Wire | Supported point count, generation-selected reads, validated writes/share accounting. |
| select | StartingPoint2Wire | Supported point count, generation-selected reads, validated writes/share accounting. |
| select | StartingPoint3Wire | Supported point count, generation-selected reads, validated writes/share accounting. |
| switch | spotCutting | G3/G4 status and action adapters; P005 sequence retained; P14/flex availability gate. |
| switch | permanentPark | Result-checked actions; permanent-park sequence selected by generation. |
| switch | SensorControlEnabled | Shared Boolean mapping or model/firmware-gated setting; actions checked separately. |
| switch | FrostSensorEnabled | App firmware-selected command family and strict Boolean/availability handling. |
| switch | GarageEnabled | Platform plus runtime availability; radar and ZoneProtect remain separate. |
| switch | AntiCollisionRadarEnabled | Platform plus runtime availability; radar and ZoneProtect remain separate. |
| switch | EcoMode | Shared Boolean mapping or model/firmware-gated setting; actions checked separately. |
| switch | StartingPoint1Enabled | Supported point count, generation-selected reads, validated writes/share accounting. |
| switch | StartingPoint2Enabled | Supported point count, generation-selected reads, validated writes/share accounting. |
| switch | StartingPoint3Enabled | Supported point count, generation-selected reads, validated writes/share accounting. |
| switch | StartingPoint1CorridorCut | Supported point count, generation-selected reads, validated writes/share accounting. |
| switch | StartingPoint2CorridorCut | Supported point count, generation-selected reads, validated writes/share accounting. |
| switch | StartingPoint3CorridorCut | Supported point count, generation-selected reads, validated writes/share accounting. |
| button | diagnostic_refresh | Read-only refresh of model-selected/optional diagnostics. |
| button | generate_loop_signal | 4692/2 only; validated completion event, timeout and keep-alive handling. |
| button | reset_cutting_blade_usage_time | Explicit user-requested reset only; no write probing; result-checked 4726/8. |
| lawn_mower | Mower | Result-checked actions; permanent-park sequence selected by generation. |
| calendar | Schedule | Generation limits; strict reads, serialized writes, reply checks and read-back. |
