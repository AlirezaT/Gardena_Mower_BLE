"""Support for sensor entities."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfTime, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GardenaConfigEntry
from .entity import GardenaMowerBleDescriptorEntity

# Optional: add this to const.py later if you want nicer error names
ERROR_CODE_DESCRIPTIONS = {
    0: "No error",
    10: "Unknown mower message",
}

SPOT_CUTTING_STATES = {
    0: "not_active",
    1: "idle",
    2: "pending_start",
    3: "running",
}

DESCRIPTIONS = (
    SensorEntityDescription(
        key="battery_level",
        name="Battery Level",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.BATTERY,
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
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:battery-clock",
    ),
    SensorEntityDescription(
        key="errorCode",
        name="Error Code",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:alert-circle",
    ),
    SensorEntityDescription(
        key="errorDescription",
        name="Error Description",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:alert-decagram",
    ),
    SensorEntityDescription(
        key="NumberOfMessages",
        name="Number Of Messages",
        state_class=SensorStateClass.TOTAL,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:message",
    ),
    SensorEntityDescription(
        key="operatorstate",
        name="Operator State",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:account",
    ),
    SensorEntityDescription(
        key="spotCutting",
        name="Spot Cutting",
        icon="mdi:content-cut",
    ),

    # Statistics
    SensorEntityDescription(
        key="totalRunningTime",
        name="Total Running Time",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:timer-outline",
    ),
    SensorEntityDescription(
        key="totalCuttingTime",
        name="Total Cutting Time",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:content-cut",
    ),
    SensorEntityDescription(
        key="totalChargingTime",
        name="Total Charging Time",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:battery-charging",
    ),
    SensorEntityDescription(
        key="totalSearchingTime",
        name="Total Searching Time",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:magnify",
    ),
    SensorEntityDescription(
        key="cuttingBladeUsageTime",
        name="Cutting Blade Usage Time",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:knife",
    ),
    SensorEntityDescription(
        key="numberOfCollisions",
        name="Number Of Collisions",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:alert",
    ),
    SensorEntityDescription(
        key="numberOfChargingCycles",
        name="Number Of Charging Cycles",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:battery-sync",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GardenaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Gardena Automower BLE sensors."""
    coordinator = entry.runtime_data

    async_add_entities(
        GardenaMowerBleSensor(coordinator, description)
        for description in DESCRIPTIONS
        if description.key in coordinator.data
        or description.key == "errorDescription"
    )


class GardenaMowerBleSensor(GardenaMowerBleDescriptorEntity, SensorEntity):
    """Representation of a Gardena mower sensor."""

    entity_description: SensorEntityDescription

    @property
    def native_value(self) -> str | int | float | None:
        """Return the sensor value."""
        key = self.entity_description.key

        if key == "errorDescription":
            error_code = self.coordinator.data.get("errorCode")
            if error_code is None:
                return None
            return ERROR_CODE_DESCRIPTIONS.get(
                error_code,
                f"Unknown error ({error_code})",
            )

        value = self.coordinator.data.get(key)

        if value is None:
            return None

        if key == "spotCutting":
            return SPOT_CUTTING_STATES.get(value, f"unknown_{value}")

        # Convert enum values like MowerActivity.PARKED to "parked"
        if hasattr(value, "name"):
            return value.name.lower()

        # Keep duration values as seconds.
        # Home Assistant will display them nicely because we set
        # device_class=SensorDeviceClass.DURATION.
        return value
