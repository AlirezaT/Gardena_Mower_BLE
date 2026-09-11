"""App-verified setting mappings until corrected definitions ship upstream."""

from automower_ble.protocol import ResponseResult


def corrected_protocol(protocol):
    """Return an instance-local copy; never patch the installed upstream package."""
    result = dict(protocol)
    for label, major in (
        ("EcoMode", 4692),
        ("FrostSensor", 5370),
        ("FrostSensorV1", 5412),
    ):
        read, write = (6, 5) if label == "EcoMode" else (1, 2)
        result[f"Get{label}Enabled"] = {
            "major": major,
            "minor": read,
            "responseType": "bool",
        }
        result[f"Set{label}Enabled"] = {
            "major": major,
            "minor": write,
            "requestType": {"enabled": "bool"},
        }
    # ObstacleAvoidance is radar; MobileLoop is ZoneProtect, not radar.
    result["GetAntiCollisionRadar"] = {
        "major": 5356,
        "minor": 7,
        "responseType": {
            "available": "bool",
            "enabled": "bool",
            "useAtBoundary": "bool",
        },
    }
    result["SetAntiCollisionRadarEnabled"] = {
        "major": 5356,
        "minor": 3,
        "requestType": {"enabled": "bool"},
    }
    result["GetZoneProtectSettings"] = {
        "major": 6050,
        "minor": 4,
        "responseType": {"enabled": "uint8", "available": "bool"},
    }
    result["SetZoneProtectEnabled"] = {
        "major": 6050,
        "minor": 3,
        "requestType": {"enabled": "bool"},
    }
    # Remove aliases that target unrelated settings or diagnostics.
    for name in (
        "GetFrostSensorEnabledLegacy",
        "SetFrostSensorEnabledLegacy",
        "GetChargingStationLoopSignalGeneration",
        "SetChargingStationLoopSignalGeneration",
        "GenerateLoopSignalLegacy",  # Actually disables obstacle avoidance.
        "GetSupportedAccessories",  # Actually front/rear collision status.
    ):
        result.pop(name, None)
    return result


UNSUPPORTED = {
    ResponseResult.INVALID_GROUP,
    ResponseResult.INVALID_ID,
    ResponseResult.NOT_AVAILABLE,
}


def setting_bool(value):
    """Upstream decodes protocol bool as an integer byte; reject other data."""
    if type(value) in (bool, int) and value in (0, 1):
        return bool(value)
    return None


async def read_frost_setting(mower):
    """Select a supported module using reads only; never probe by writing."""
    for suffix in ("FrostSensor", "FrostSensorV1"):
        result, value = await mower.command_response(
            f"Get{suffix}Enabled",
            warn_on_error=False,
        )
        if result is ResponseResult.OK:
            enabled = setting_bool(value)
            if enabled is not None:
                return result, enabled, f"Set{suffix}Enabled"
            return ResponseResult.UNKNOWN_ERROR, None, None
        if result not in UNSUPPORTED:
            return result, None, None
    return result, None, None
