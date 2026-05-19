"""Support for button entities."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components import bluetooth
from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GardenaConfigEntry
from .automower_ble.protocol import ResponseResult
from .entity import GardenaMowerBleDescriptorEntity


@dataclass(frozen=True, kw_only=True)
class GardenaMowerBleCommandButtonEntityDescription(ButtonEntityDescription):
    """Description for mower command button entities."""

    command: str


DESCRIPTIONS = (
    ButtonEntityDescription(
        key="diagnostic_refresh",
        name="Diagnostic Refresh",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:refresh",
    ),
    GardenaMowerBleCommandButtonEntityDescription(
        key="generate_loop_signal",
        name="Generate Loop Signal",
        entity_category=EntityCategory.CONFIG,
        icon="mdi:sine-wave",
        command="GenerateLoopSignal",
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
        (
            GardenaMowerBleCommandButton(coordinator, description)
            if isinstance(description, GardenaMowerBleCommandButtonEntityDescription)
            else GardenaMowerBleDiagnosticRefreshButton(coordinator, description)
        )
        for description in DESCRIPTIONS
    )


class GardenaMowerBleDiagnosticRefreshButton(
    GardenaMowerBleDescriptorEntity, ButtonEntity
):
    """Button that triggers a one-shot mower refresh."""

    entity_description: ButtonEntityDescription

    async def async_press(self) -> None:
        """Request a one-shot coordinator refresh."""
        await self.coordinator.async_request_refresh()


class GardenaMowerBleCommandButton(GardenaMowerBleDescriptorEntity, ButtonEntity):
    """Button that triggers a mower command."""

    entity_description: GardenaMowerBleCommandButtonEntityDescription

    async def async_press(self) -> None:
        """Send a one-shot mower command."""
        await self._async_ensure_connected()
        result, _ = await self.coordinator.mower.command_response(
            self.entity_description.command,
            signalType=0,
        )
        if result is not ResponseResult.OK:
            raise HomeAssistantError(
                f"{self.entity_description.name} failed: {result.name}. "
                "The mower may need to be parked in the charging station."
            )

        await self.coordinator.async_request_refresh()

    async def _async_ensure_connected(self) -> None:
        """Connect to the mower if needed."""
        if self.coordinator.mower.is_connected():
            return

        device = bluetooth.async_ble_device_from_address(
            self.coordinator.hass, self.coordinator.address, connectable=True
        )
        if await self.coordinator.mower.connect(device) is not ResponseResult.OK:
            raise HomeAssistantError("Unable to connect to mower")
