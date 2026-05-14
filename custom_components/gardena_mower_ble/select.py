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


@dataclass(frozen=True, kw_only=True)
class GardenaMowerBleSelectEntityDescription(SelectEntityDescription):
    """Description for mower select entities."""

    set_command: str
    starting_point_id: int


DESCRIPTIONS = tuple(
    GardenaMowerBleSelectEntityDescription(
        key=f"StartingPoint{starting_point_id}Wire",
        name=f"Starting Point {starting_point_id} Wire",
        icon="mdi:source-branch",
        entity_category=EntityCategory.CONFIG,
        options=list(WIRE_IDS_BY_OPTION),
        set_command="SetStartingPointWire",
        starting_point_id=starting_point_id,
    )
    for starting_point_id in range(1, 4)
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
        return WIRE_OPTIONS_BY_ID.get(int(value))

    async def async_select_option(self, option: str) -> None:
        """Set the selected option."""
        if option not in WIRE_IDS_BY_OPTION:
            raise HomeAssistantError(f"Unknown wire option: {option}")

        description = self.entity_description
        result, _ = await self.coordinator.mower.command_response(
            description.set_command,
            startingPointId=description.starting_point_id,
            wire=WIRE_IDS_BY_OPTION[option],
        )
        if result is not ResponseResult.OK:
            raise HomeAssistantError(f"{description.name} failed: {result.name}")

        await self.coordinator.async_request_refresh()
