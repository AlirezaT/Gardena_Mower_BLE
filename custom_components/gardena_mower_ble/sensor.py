"""Support for sensor entities."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfTemperature,
    UnitOfTime,
    EntityCategory,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GardenaConfigEntry
from .automower_ble.error_codes import ErrorCodes
from .entity import GardenaMowerBleDescriptorEntity

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
    SensorEntityDescription(
        key="StartingPointChargingStationProportion",
        name="Charging Station Mowing Share",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:home-percent",
    ),
    SensorEntityDescription(
        key="last_message",
        name="Last Message",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:message-alert",
    ),
    SensorEntityDescription(
        key="modelName",
        name="Model",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:robot-mower",
    ),
    SensorEntityDescription(
        key="mowerName",
        name="Mower Name",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:tag",
    ),
    SensorEntityDescription(
        key="serialNumber",
        name="Serial Number",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:identifier",
    ),
    SensorEntityDescription(
        key="hardwareSerialNumber",
        name="Hardware Serial Number",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:identifier",
    ),
    SensorEntityDescription(
        key="hardwareRevision",
        name="Hardware Revision",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:chip",
    ),
    SensorEntityDescription(
        key="productionTime",
        name="Production Time",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:factory",
    ),
    SensorEntityDescription(
        key="nodeIprId",
        name="Node IPR ID",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:identifier",
    ),
    SensorEntityDescription(
        key="husqvarnaId",
        name="Husqvarna ID",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:identifier",
    ),
    SensorEntityDescription(
        key="bootSoftwareVersion",
        name="Boot Software Version",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:chip",
    ),
    SensorEntityDescription(
        key="applicationSoftwareVersion",
        name="Application Software Version",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:chip",
    ),
    SensorEntityDescription(
        key="subSoftwareVersion",
        name="Sub Software Version",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:chip",
    ),
    SensorEntityDescription(
        key="pitch",
        name="Pitch",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:angle-acute",
    ),
    SensorEntityDescription(
        key="roll",
        name="Roll",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:angle-acute",
    ),
    SensorEntityDescription(
        key="mowerTemperature",
        name="Mower Temperature",
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:thermometer",
    ),
    SensorEntityDescription(
        key="signalQuality",
        name="Signal Quality",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:signal",
    ),
    SensorEntityDescription(
        key="a0Signal",
        name="A0 Signal",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:sine-wave",
    ),
    SensorEntityDescription(
        key="fSignal",
        name="F Signal",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:sine-wave",
    ),
    SensorEntityDescription(
        key="nSignal",
        name="N Signal",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:sine-wave",
    ),
    *(
        SensorEntityDescription(
            key=f"guide{guide_id}Signal",
            name=f"Guide {guide_id} Signal",
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC,
            icon="mdi:sine-wave",
        )
        for guide_id in range(1, 4)
    ),
    SensorEntityDescription(
        key="messageFromChargingStation",
        name="Message From Charging Station",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:home-message",
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
            return _describe_error_code(error_code)

        value = self.coordinator.data.get(key)

        if value is None:
            return None

        if key == "spotCutting":
            return SPOT_CUTTING_STATES.get(value, f"unknown_{value}")

        if key == "last_message":
            return _format_message(value)

        # Convert enum values like MowerActivity.PARKED to "parked"
        if hasattr(value, "name"):
            return value.name.lower()

        # Keep duration values as seconds.
        # Home Assistant will display them nicely because we set
        # device_class=SensorDeviceClass.DURATION.
        return value

    @property
    def extra_state_attributes(self) -> dict[str, str | int] | None:
        """Return extra attributes for structured message sensors."""
        if self.entity_description.key != "last_message":
            return None

        message = self.coordinator.data.get("last_message")
        if not isinstance(message, dict):
            return None

        attributes = dict(message)
        code = message.get("code")
        if isinstance(code, int):
            attributes["description"] = _describe_error_code(code)
        return attributes


def _describe_error_code(error_code: int) -> str:
    """Return a readable mower error description."""
    if error_code == 0:
        return "No error"
    try:
        return ErrorCodes(error_code).name.replace("_", " ").title()
    except ValueError:
        return f"Unknown error ({error_code})"


def _format_message(message: object) -> str | None:
    """Return a compact display value for a mower message."""
    if not isinstance(message, dict):
        return None

    code = message.get("code")
    if not isinstance(code, int):
        return None
    return _describe_error_code(code)
