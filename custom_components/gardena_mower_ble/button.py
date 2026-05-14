"""Support for button entities."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GardenaConfigEntry
from .entity import GardenaMowerBleDescriptorEntity

DESCRIPTIONS = (
    ButtonEntityDescription(
        key="diagnostic_refresh",
        name="Diagnostic Refresh",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:refresh",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GardenaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Gardena Automower BLE button entities."""
    coordinator = entry.runtime_data
    async_add_entities(
        GardenaMowerBleDiagnosticRefreshButton(coordinator, description)
        for description in DESCRIPTIONS
    )


class GardenaMowerBleDiagnosticRefreshButton(
    GardenaMowerBleDescriptorEntity, ButtonEntity
):
    """Button that triggers a one-shot mower refresh."""

    entity_description: ButtonEntityDescription

    async def async_press(self) -> None:
        """Request a one-shot coordinator refresh."""
        await self.coordinator.async_request_refresh()
