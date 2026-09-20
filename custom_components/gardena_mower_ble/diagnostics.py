"""Privacy-safe connection diagnostics; never export PINs or Bluetooth keys."""

from homeassistant.components.diagnostics import async_redact_data


async def async_get_config_entry_diagnostics(hass, entry):
    """Return allowlisted metadata, never config-entry data or backend objects."""
    coordinator = getattr(entry, "runtime_data", None)
    mower = getattr(coordinator, "mower", None)
    if mower is None:
        return {"connection": {"outcome": "not_loaded"}}
    return {
        # Cached poll values, not additional commands or a fresh hardware read.
        "mower_status_cached": {
            key: (getattr(coordinator, "data", None) or {}).get(key)
            for key in (
                "modelPlatform", "modelGeneration", "applicationSoftwareVersion",
                "state", "activity", "mode", "restrictionReasonRaw", "lift",
                "collision", "inChargingStation", "errorCode",
                "override", "next_start_time", "permanentPark", "operatorstate",
            )
        },
        "connection": async_redact_data(
            {**mower.connection_diagnostics, "connected": mower.is_connected()},
            {"source", "source_name"},
        )
    }
