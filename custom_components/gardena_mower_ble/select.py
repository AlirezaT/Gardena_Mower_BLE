"""Support for select entities."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GardenaConfigEntry
from .automower_ble.protocol import ResponseResult
from .entity import GardenaMowerBleDescriptorEntity

WIRE_OPTIONS_BY_ID = {
    0: "Right boundary wire",
    1: "Left boundary wire",
    2: "Guide wire 1",
    3: "Guide wire 2",
    4: "Guide wire 3",
}
WIRE_IDS_BY_OPTION = {value: key for key, value in WIRE_OPTIONS_BY_ID.items()}

SENSOR_CONTROL_SENSITIVITY_OPTIONS_BY_ID = {
    0: "Low",
    1: "Medium",
    2: "High",
}
SENSOR_CONTROL_SENSITIVITY_IDS_BY_OPTION = {
    value: key for key, value in SENSOR_CONTROL_SENSITIVITY_OPTIONS_BY_ID.items()
}


@dataclass(frozen=True, kw_only=True)
class GardenaMowerBleSelectEntityDescription(SelectEntityDescription):
    """Description for mower select entities."""

    set_command: str
    value_parameter: str
    options_by_id: dict[int, str]
    ids_by_option: dict[str, int]
    starting_point_id: int | None = None


DESCRIPTIONS = (
    GardenaMowerBleSelectEntityDescription(
        key="SensorControlSensitivity",
        name="SensorControl Sensitivity",
        icon="mdi:grass",
        entity_category=EntityCategory.CONFIG,
        options=list(SENSOR_CONTROL_SENSITIVITY_IDS_BY_OPTION),
        set_command="SetSensorControlSensitivity",
        value_parameter="sensitivity",
        options_by_id=SENSOR_CONTROL_SENSITIVITY_OPTIONS_BY_ID,
        ids_by_option=SENSOR_CONTROL_SENSITIVITY_IDS_BY_OPTION,
    ),
    *(
        GardenaMowerBleSelectEntityDescription(
            key=f"StartingPoint{starting_point_id}Wire",
            name=f"Starting Point {starting_point_id} Wire",
            icon="mdi:source-branch",
            entity_category=EntityCategory.CONFIG,
            options=list(WIRE_IDS_BY_OPTION),
            set_command="SetStartingPointWire",
            value_parameter="wire",
            options_by_id=WIRE_OPTIONS_BY_ID,
            ids_by_option=WIRE_IDS_BY_OPTION,
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
    """Set up Gardena Automower BLE select entities."""
    coordinator = entry.runtime_data

    async_add_entities(
        GardenaMowerBleSelect(coordinator, description)
        for description in DESCRIPTIONS
        if description.key in coordinator.data
    )


class GardenaMowerBleSelect(GardenaMowerBleDescriptorEntity, SelectEntity):
    """Representation of a Gardena mower select entity."""

    entity_description: GardenaMowerBleSelectEntityDescription

    @property
    def current_option(self) -> str | None:
        """Return the selected option."""
        value = self.coordinator.data.get(self.entity_description.key)
        if value is None:
            return None
        return self.entity_description.options_by_id.get(int(value))

    async def async_select_option(self, option: str) -> None:
        """Set the selected option."""
        if option not in self.entity_description.ids_by_option:
            raise HomeAssistantError(f"Unknown option: {option}")

        description = self.entity_description
        request = {
            description.value_parameter: description.ids_by_option[option],
        }
        if description.starting_point_id is not None:
            request["startingPointId"] = description.starting_point_id

        result, _ = await self.coordinator.mower.command_response(
            description.set_command,
            **request,
        )
        if result is not ResponseResult.OK:
            raise HomeAssistantError(f"{description.name} failed: {result.name}")

        await self.coordinator.async_request_refresh()
