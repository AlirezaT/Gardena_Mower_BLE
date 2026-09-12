"""The Gardena Autoconnect Bluetooth lawn mower platform."""

import asyncio
import voluptuous as vol

from automower_ble.protocol import (
    ModeOfOperation,
    MowerActivity,
    MowerState,
    ResponseResult,
)

from homeassistant.components import bluetooth
from homeassistant.components.lawn_mower import (
    LawnMowerActivity,
    LawnMowerEntity,
    LawnMowerEntityFeature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers import entity_platform

from . import GardenaConfigEntry
from .const import LOGGER
from .control import start_manual_mowing
from .coordinator import GardenaCoordinator
from .entity import GardenaMowerBleEntity
from .duration import validate_duration


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: GardenaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up AutomowerLawnMower integration from a config entry."""
    coordinator = config_entry.runtime_data
    address = coordinator.address

    entity_platform.async_get_current_platform().async_register_entity_service(
        "start_mowing_for",
        {vol.Required("duration_hours"): validate_duration},
        "async_start_mowing",
    )

    async_add_entities(
        [
            AutomowerLawnMower(
                coordinator,
                address,
            ),
        ]
    )


class AutomowerLawnMower(GardenaMowerBleEntity, LawnMowerEntity):
    """Gardena Automower."""

    _attr_name = None
    _attr_supported_features = (
        LawnMowerEntityFeature.PAUSE
        | LawnMowerEntityFeature.START_MOWING
        | LawnMowerEntityFeature.DOCK
    )

    def __init__(
        self,
        coordinator: GardenaCoordinator,
        address: str,
    ) -> None:
        """Initialize the lawn mower."""
        super().__init__(coordinator)
        self._attr_unique_id = str(address)

    def _get_activity(self) -> LawnMowerActivity | None:
        """Return the current lawn mower activity."""
        if self.coordinator.data is None:
            return None

        state = self.coordinator.data["state"]
        activity = self.coordinator.data["activity"]

        if state is None or activity is None:
            return None

        if state == MowerState.PAUSED:
            return LawnMowerActivity.PAUSED
        if state in (MowerState.STOPPED, MowerState.OFF, MowerState.WAIT_FOR_SAFETYPIN):
            # This is actually stopped, but that isn't an option
            return LawnMowerActivity.ERROR
        if state == MowerState.PENDING_START and activity == MowerActivity.NONE:
            # This happens when the mower is safety stopped and we try to send a
            # command to start it.
            return LawnMowerActivity.ERROR
        if state in (
            MowerState.RESTRICTED,
            MowerState.IN_OPERATION,
            MowerState.PENDING_START,
        ):
            if activity in (
                MowerActivity.CHARGING,
                MowerActivity.PARKED,
                MowerActivity.NONE,
            ):
                return LawnMowerActivity.DOCKED
            if activity in (MowerActivity.GOING_OUT, MowerActivity.MOWING):
                return LawnMowerActivity.MOWING
            if activity == MowerActivity.GOING_HOME:
                return LawnMowerActivity.RETURNING
        return LawnMowerActivity.ERROR

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        LOGGER.debug("AutomowerLawnMower: _handle_coordinator_update")

        self._attr_activity = self._get_activity()
        self._attr_available = self._attr_activity is not None
        super()._handle_coordinator_update()

    @property
    def extra_state_attributes(self):
        """Retain the accepted run budget independently of the manual preference."""
        return {
            "last_start_duration_hours": self.coordinator.config_entry.options.get(
                "last_start_duration_hours"
            )
        }

    async def async_start_mowing(self, duration_hours=None) -> None:
        """Start an explicit run, without overwriting the manual preference."""
        LOGGER.debug("Starting mower")

        try:
            duration = validate_duration(
                self.coordinator.manual_mowing_duration_hours
                if duration_hours is None else duration_hours
            )
            await start_manual_mowing(
                self.coordinator.mower,
                duration,
                self.coordinator._async_find_device,
            )
        except Exception as err:
            raise HomeAssistantError(str(err)) from err
        self.coordinator.hass.config_entries.async_update_entry(
            self.coordinator.config_entry,
            options={**self.coordinator.config_entry.options,
                     "last_start_duration_hours": duration},
        )
        self.coordinator.update_cached_data(
            {
                "activity": MowerActivity.MOWING,
                "state": MowerState.IN_OPERATION,
                "mode": ModeOfOperation.AUTO,
                "permanentPark": False,
            }
        )
        self.coordinator.schedule_action_refresh()

        self._attr_activity = self._get_activity()
        self.async_write_ha_state()

    async def async_dock(self) -> None:
        """Start docking."""
        LOGGER.debug("Start docking")

        if not self.coordinator.mower.is_connected():
            device = bluetooth.async_ble_device_from_address(
                self.coordinator.hass, self.coordinator.address, connectable=True
            )
            if await self.coordinator.mower.connect(device) is not ResponseResult.OK:
                raise HomeAssistantError("Unable to connect to mower")
        if self.coordinator.data.get("state") == MowerState.PAUSED:
            result = await self.coordinator.mower.mower_resume()
            if result is not ResponseResult.OK:
                raise HomeAssistantError(f"Resume before docking failed: {result.name}")
            await asyncio.sleep(1)

        result = await self.coordinator.mower.mower_park()
        if result is not ResponseResult.OK:
            raise HomeAssistantError(f"Dock failed: {result.name}")

        self.coordinator.update_cached_data(
            {
                "activity": MowerActivity.GOING_HOME,
                "state": MowerState.IN_OPERATION,
            }
        )
        self.coordinator.schedule_action_refresh()

        self._attr_activity = self._get_activity()
        self.async_write_ha_state()

    async def async_pause(self) -> None:
        """Pause mower."""
        LOGGER.debug("Pausing mower")

        if not self.coordinator.mower.is_connected():
            device = bluetooth.async_ble_device_from_address(
                self.coordinator.hass, self.coordinator.address, connectable=True
            )
            if await self.coordinator.mower.connect(device) is not ResponseResult.OK:
                raise HomeAssistantError("Unable to connect to mower")

        result, _ = await self.coordinator.mower.command_response("Pause")
        if result is not ResponseResult.OK:
            raise HomeAssistantError(f"Pause failed: {result.name}")
        self.coordinator.update_cached_data({"state": MowerState.PAUSED})
        self.coordinator.schedule_action_refresh()

        self._attr_activity = self._get_activity()
        self.async_write_ha_state()
