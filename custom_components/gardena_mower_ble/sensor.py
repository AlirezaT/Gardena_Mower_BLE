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

TIME_SENSORS = (
    "totalRunningTime",
    "totalCuttingTime",
    "totalChargingTime",
    "totalSearchingTime",
    "cuttingBladeUsageTime",
)

DESCRIPTIONS = (
    SensorEntityDescription(
        key="battery_level",
        name="Battery Level",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.BATTERY,
        entity_category=EntityCategory.DIAGNOSTIC,
        native_unit_of_measurement=PERCENTAGE,
    ),

    SensorEntityDescription(
        key="activity",
        name="Activity",
        icon="mdi:robot-mower",
    ),

    SensorEntityDescription(
        key="state",
        name="State",
        icon="mdi:state-machine",
    ),

    SensorEntityDescription(
        key="next_start_time",
        name="Next Start Time",
        device_class=SensorDeviceClass.TIMESTAMP,
        icon="mdi:clock-start",
    ),

    SensorEntityDescription(
        key="RemainingChargingTime",
        name="Remaining Charging Time",
        native_unit_of_measurement="min",
        icon="mdi:battery-clock",
    ),

    SensorEntityDescription(
        key="errorCode",
        name="Error Code",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:alert-circle",
    ),

    SensorEntityDescription(
        key="NumberOfMessages",
        name="Number Of Messages",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:message",
    ),

    SensorEntityDescription(
        key="operatorstate",
        name="Operator State",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:account",
    ),

    # Statistics

    SensorEntityDescription(
        key="totalRunningTime",
        name="Total Running Time",
        native_unit_of_measurement="h",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:timer-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),

    SensorEntityDescription(
        key="totalCuttingTime",
        name="Total Cutting Time",
        native_unit_of_measurement="h",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:content-cut",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),

    SensorEntityDescription(
        key="totalChargingTime",
        name="Total Charging Time",
        native_unit_of_measurement="h",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:battery-charging",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),

    SensorEntityDescription(
        key="totalSearchingTime",
        name="Total Searching Time",
        native_unit_of_measurement="h",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:magnify",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),

    SensorEntityDescription(
        key="cuttingBladeUsageTime",
        name="Cutting Blade Usage Time",
        native_unit_of_measurement="h",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:knife",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),

    SensorEntityDescription(
        key="numberOfCollisions",
        name="Number Of Collisions",
        state_class=SensorStateClass.TOTAL_INCREASING,
        icon="mdi:alert",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),

    SensorEntityDescription(
        key="numberOfChargingCycles",
        name="Number Of Charging Cycles",
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


class GardenaMowerBleSensor(
    GardenaMowerBleDescriptorEntity,
    SensorEntity,
):
    """Representation of a sensor."""

    entity_description: SensorEntityDescription

    @property
    def native_value(self) -> str | int | float:
        """Return the previously fetched value."""

        value = self.coordinator.data[self.entity_description.key]

        # Convert enums nicely
        if hasattr(value, "name"):
            return value.name.lower()

        # Convert minutes to hours
        if self.entity_description.key in TIME_SENSORS:
            return round(value / 60, 1)

        return value