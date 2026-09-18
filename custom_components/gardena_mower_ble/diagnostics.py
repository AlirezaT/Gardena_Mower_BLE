"""Privacy-safe connection diagnostics; never export PINs or Bluetooth keys."""

from homeassistant.components.diagnostics import async_redact_data


async def async_get_config_entry_diagnostics(hass, entry):
    """Return only connection metadata, not config-entry data or backend objects."""
    coordinator = getattr(entry, "runtime_data", None)
    mower = getattr(coordinator, "mower", None)
    if mower is None:
        return {"connection": {"outcome": "not_loaded"}}
    return {
        "connection": async_redact_data(
            {**mower.connection_diagnostics, "connected": mower.is_connected()},
            {"source", "source_name"},
        )
    }
