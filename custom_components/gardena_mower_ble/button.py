"""Support for button entities."""

from __future__ import annotations

from homeassistant.components import bluetooth
from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GardenaConfigEntry
from .automower_ble.protocol import ResponseResult
from .const import LOGGER
from .coordinator import GardenaCoordinator
from .entity import GardenaMowerBleDescriptorEntity

DESCRIPTIONS = (
    ButtonEntityDescription(
        key="StartSpotCutting",
        name="Spot Cut",
        icon="mdi:content-cut",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GardenaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Gardena Automower BLE button entities."""
    coordinator = entry.runtime_data

    async_add_entities(
        GardenaMowerBleButton(coordinator, description) for description in DESCRIPTIONS
    )


class GardenaMowerBleButton(GardenaMowerBleDescriptorEntity, ButtonEntity):
    """Representation of a Gardena mower button entity."""

    entity_description: ButtonEntityDescription

    async def async_press(self) -> None:
        """Handle the button press."""
        LOGGER.debug("Pressing %s button", self.entity_description.key)

        if not self.coordinator.mower.is_connected():
            device = bluetooth.async_ble_device_from_address(
                self.coordinator.hass, self.coordinator.address, connectable=True
            )
            if await self.coordinator.mower.connect(device) is not ResponseResult.OK:
                return

        result, _ = await self.coordinator.mower.command_response(
            self.entity_description.key
        )
        if result is ResponseResult.INVALID_ID:
            raise HomeAssistantError(
                "Spot Cut is not supported by this mower or firmware"
            )
        if result is not ResponseResult.OK:
            raise HomeAssistantError(f"Spot Cut failed: {result.name}")

        await self.coordinator.async_request_refresh()
