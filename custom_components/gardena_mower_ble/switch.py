"""Support for switch entities."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GardenaConfigEntry
from .automower_ble.protocol import ResponseResult
from .entity import GardenaMowerBleDescriptorEntity


@dataclass(frozen=True, kw_only=True)
class GardenaMowerBleSwitchEntityDescription(SwitchEntityDescription):
    """Description for mower switch entities."""

    set_command: str
    starting_point_id: int


DESCRIPTIONS = tuple(
    GardenaMowerBleSwitchEntityDescription(
        key=f"StartingPoint{starting_point_id}Enabled",
        name=f"Starting Point {starting_point_id}",
        icon="mdi:map-marker-check",
        entity_category=EntityCategory.CONFIG,
        set_command="SetStartingPointEnabled",
        starting_point_id=starting_point_id,
    )
    for starting_point_id in range(1, 4)
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GardenaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Gardena Automower BLE switch entities."""
    coordinator = entry.runtime_data

    async_add_entities(
        GardenaMowerBleSwitch(coordinator, description)
        for description in DESCRIPTIONS
        if description.key in coordinator.data
    )


class GardenaMowerBleSwitch(GardenaMowerBleDescriptorEntity, SwitchEntity):
    """Representation of a Gardena mower switch entity."""

    entity_description: GardenaMowerBleSwitchEntityDescription

    @property
    def is_on(self) -> bool | None:
        """Return true if the switch is on."""
        value = self.coordinator.data.get(self.entity_description.key)
        if value is None:
            return None
        return bool(value)

    async def async_turn_on(self, **kwargs) -> None:
        """Turn the switch on."""
        await self._async_set_enabled(True)

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the switch off."""
        await self._async_set_enabled(False)

    async def _async_set_enabled(self, enabled: bool) -> None:
        """Enable or disable the starting point."""
        description = self.entity_description
        result, _ = await self.coordinator.mower.command_response(
            description.set_command,
            startingPointId=description.starting_point_id,
            enabled=enabled,
        )
        if result is not ResponseResult.OK:
            raise HomeAssistantError(f"{description.name} failed: {result.name}")

        await self.coordinator.async_request_refresh()
