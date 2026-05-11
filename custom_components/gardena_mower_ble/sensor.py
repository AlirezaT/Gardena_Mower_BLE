"""Support for sensor entities."""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GardenaConfigEntry
from .entity import GardenaMowerBleDescriptorEntity

DESCRIPTIONS = (
    SensorEntityDescription(
        key="battery_level",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.BATTERY,
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=PERCENTAGE,
    ),

    SensorEntityDescription(
        key="activity",
        icon="mdi:robot-mower",
    ),

    SensorEntityDescription(
        key="state",
        icon="mdi:state-machine",
    ),

    SensorEntityDescription(
        key="next_start_time",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),

    SensorEntityDescription(
        key="RemainingChargingTime",
        native_unit_of_measurement="min",
        icon="mdi:battery-clock",
    ),

    SensorEntityDescription(
        key="errorCode",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:alert-circle",
    ),

    SensorEntityDescription(
        key="NumberOfMessages",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:message",
    ),

    SensorEntityDescription(
        key="operatorstate",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),

        SensorEntityDescription(
        key="totalRunningTime",
        native_unit_of_measurement="h",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:timer-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),

    SensorEntityDescription(
        key="totalCuttingTime",
        native_unit_of_measurement="h",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:content-cut",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),

    SensorEntityDescription(
        key="totalChargingTime",
        native_unit_of_measurement="h",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:battery-charging",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),

    SensorEntityDescription(
        key="totalSearchingTime",
        native_unit_of_measurement="h",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:magnify",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),

    SensorEntityDescription(
        key="cuttingBladeUsageTime",
        native_unit_of_measurement="h",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:knife",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),

    SensorEntityDescription(
        key="numberOfCollisions",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:alert",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),

    SensorEntityDescription(
        key="numberOfChargingCycles",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:battery-sync",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GardenaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Gardena Automower Ble sensor based on a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        GardenaMowerBleSensor(coordinator, description)
        for description in DESCRIPTIONS
        if description.key in coordinator.data
    )


class GardenaMowerBleSensor(GardenaMowerBleDescriptorEntity, SensorEntity):
    """Representation of a sensor."""

    entity_description: SensorEntityDescription

    @property
    def native_value(self) -> str | int:
        """Return the previously fetched value."""
        return self.coordinator.data[self.entity_description.key]
