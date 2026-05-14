"""Support for binary sensor entities."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GardenaConfigEntry
from .entity import GardenaMowerBleDescriptorEntity

DESCRIPTIONS = (
    BinarySensorEntityDescription(
        key="collision",
        name="Collision",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:alert",
    ),
    BinarySensorEntityDescription(
        key="lift",
        name="Lift",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:arrow-up-bold",
    ),
    BinarySensorEntityDescription(
        key="upsideDown",
        name="Upside Down",
        device_class=BinarySensorDeviceClass.PROBLEM,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:rotate-3d-variant",
    ),
    BinarySensorEntityDescription(
        key="inChargingStation",
        name="In Charging Station",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:home-lightning-bolt",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GardenaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Gardena Automower BLE binary sensor entities."""
    coordinator = entry.runtime_data

    async_add_entities(
        GardenaMowerBleBinarySensor(coordinator, description)
        for description in DESCRIPTIONS
        if description.key in coordinator.data
    )


class GardenaMowerBleBinarySensor(GardenaMowerBleDescriptorEntity, BinarySensorEntity):
    """Representation of a Gardena mower binary sensor."""

    entity_description: BinarySensorEntityDescription

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        value = self.coordinator.data.get(self.entity_description.key)
        if value is None:
            return None
        return bool(value)
