"""Support for number entities."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import EntityCategory, PERCENTAGE, UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GardenaConfigEntry
from .automower_ble.protocol import ResponseResult
from .const import LOGGER
from .entity import GardenaMowerBleDescriptorEntity

DRIVE_PAST_WIRE_SCALE = 10
REVERSING_DISTANCE_SCALE = 10


@dataclass(frozen=True, kw_only=True)
class GardenaMowerBleNumberEntityDescription(NumberEntityDescription):
    """Description for mower number entities."""

    set_command: str
    value_parameter: str
    starting_point_id: int | None = None
    scale: float = 1


DESCRIPTIONS = (
    GardenaMowerBleNumberEntityDescription(
        key="DrivePastWire",
        name="Drive Past Wire",
        icon="mdi:map-marker-distance",
        native_min_value=0,
        native_max_value=35,
        native_step=1,
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        set_command="SetDrivePastWire",
        value_parameter="distance",
        scale=DRIVE_PAST_WIRE_SCALE,
    ),
    GardenaMowerBleNumberEntityDescription(
        key="ReversingDistance",
        name="Charging Station Starting Point Distance",
        icon="mdi:map-marker-distance",
        native_min_value=60,
        native_max_value=250,
        native_step=1,
        native_unit_of_measurement=UnitOfLength.CENTIMETERS,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        set_command="SetReversingDistance",
        value_parameter="distance",
        scale=REVERSING_DISTANCE_SCALE,
    ),
    *(
        GardenaMowerBleNumberEntityDescription(
            key=f"StartingPoint{starting_point_id}Distance",
            name=f"Starting Point {starting_point_id} Distance",
            icon="mdi:map-marker-distance",
            native_min_value=1,
            native_max_value=600,
            native_step=1,
            native_unit_of_measurement=UnitOfLength.METERS,
            mode=NumberMode.BOX,
            entity_category=EntityCategory.CONFIG,
            set_command="SetStartingPointDistance",
            value_parameter="distance",
            starting_point_id=starting_point_id,
        )
        for starting_point_id in range(1, 4)
    ),
    *(
        GardenaMowerBleNumberEntityDescription(
            key=f"StartingPoint{starting_point_id}Proportion",
            name=f"Starting Point {starting_point_id} Mowing Share",
            icon="mdi:percent",
            native_min_value=0,
            native_max_value=100,
            native_step=1,
            native_unit_of_measurement=PERCENTAGE,
            mode=NumberMode.SLIDER,
            entity_category=EntityCategory.CONFIG,
            set_command="SetStartingPointProportion",
            value_parameter="proportion",
            starting_point_id=starting_point_id,
        )
        for starting_point_id in range(1, 4)
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

    entity_description: GardenaMowerBleNumberEntityDescription

    @property
    def native_value(self) -> float | None:
        """Return the number value."""
        value = self.coordinator.data.get(self.entity_description.key)
        if value is None:
            return None

        return int(value) / self.entity_description.scale

    async def async_set_native_value(self, value: float) -> None:
        """Set the number value."""
        description = self.entity_description
        LOGGER.debug("Setting %s to %s", description.key, value)
        kwargs = {
            description.value_parameter: round(value * description.scale),
        }
        if description.starting_point_id is not None:
            kwargs["startingPointId"] = description.starting_point_id

        result, _ = await self.coordinator.mower.command_response(
            description.set_command,
            **kwargs,
        )
        if result is not ResponseResult.OK:
            raise HomeAssistantError(f"{description.name} failed: {result.name}")

        await self.coordinator.async_request_refresh()
