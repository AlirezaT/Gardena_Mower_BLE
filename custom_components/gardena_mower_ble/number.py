"""Support for number entities."""

from __future__ import annotations

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import EntityCategory, UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GardenaConfigEntry
from .const import LOGGER
from .entity import GardenaMowerBleDescriptorEntity

DRIVE_PAST_WIRE_SCALE = 10

DESCRIPTIONS = (
    NumberEntityDescription(
        key="DrivePastWire",
        name="Drive Past Wire",
        icon="mdi:map-marker-distance",
        native_min_value=0,
        native_max_value=35,
        native_step=1,
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GardenaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Gardena Automower BLE number entities."""
    coordinator = entry.runtime_data

    async_add_entities(
        GardenaMowerBleNumber(coordinator, description)
        for description in DESCRIPTIONS
        if description.key in coordinator.data
    )


class GardenaMowerBleNumber(GardenaMowerBleDescriptorEntity, NumberEntity):
    """Representation of a Gardena mower number entity."""

    entity_description: NumberEntityDescription

    @property
    def native_value(self) -> float | None:
        """Return the number value."""
        value = self.coordinator.data.get(self.entity_description.key)
        if value is None:
            return None

        return int(value) / DRIVE_PAST_WIRE_SCALE

    async def async_set_native_value(self, value: float) -> None:
        """Set the number value."""
        LOGGER.debug("Setting DrivePastWire to %s cm", value)
        await self.coordinator.mower.command(
            "SetDrivePastWire",
            distance=round(value * DRIVE_PAST_WIRE_SCALE),
        )
        await self.coordinator.async_request_refresh()
