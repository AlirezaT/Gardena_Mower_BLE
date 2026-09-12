"""Hide legacy unsupported entities without deleting IDs, history or user choices."""

from homeassistant.helpers import entity_registry as er


def reconcile_model_visibility(hass, entry):
    """Reconcile this mower's registry entries after successful platform setup."""
    coordinator = entry.runtime_data
    capabilities = coordinator.capabilities
    if capabilities.platform == "unknown":
        return
    registry = er.async_get(hass)
    prefix = f"{coordinator.address}_{coordinator.channel_id}_"
    for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
        if entity.platform != "gardena_mower_ble" or not entity.unique_id.startswith(prefix):
            continue
        excluded = capabilities.entity_is_model_excluded(entity.unique_id[len(prefix):])
        if excluded and entity.hidden_by is None:
            registry.async_update_entity(entity.entity_id, hidden_by=er.RegistryEntryHider.INTEGRATION)
        elif not excluded and entity.hidden_by == er.RegistryEntryHider.INTEGRATION:
            registry.async_update_entity(entity.entity_id, hidden_by=None)
