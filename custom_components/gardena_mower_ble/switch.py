"""Support for switch entities."""

from __future__ import annotations

from dataclasses import dataclass
import time

from homeassistant.components import bluetooth
from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GardenaConfigEntry
from .automower_ble.protocol import (
    ModeOfOperation,
    MowerActivity,
    MowerState,
    OverrideAction,
    ResponseResult,
)
from .entity import GardenaMowerBleDescriptorEntity

ALWAYS_CREATE_SWITCHES = {
    "EcoMode",
    "permanentPark",
}


@dataclass(frozen=True, kw_only=True)
class GardenaMowerBleSwitchEntityDescription(SwitchEntityDescription):
    """Description for mower switch entities."""

    set_command: str
    value_parameter: str
    invert_value: bool = False
    starting_point_id: int | None = None


DESCRIPTIONS = (
    SwitchEntityDescription(
        key="spotCutting",
        name="Spot Cut",
        icon="mdi:content-cut",
    ),
    SwitchEntityDescription(
        key="permanentPark",
        name="Park Until Further Notice",
        icon="mdi:home-lock",
    ),
    GardenaMowerBleSwitchEntityDescription(
        key="SensorControlEnabled",
        name="SensorControl",
        icon="mdi:grass",
        entity_category=EntityCategory.CONFIG,
        set_command="SetSensorControlEnabled",
        value_parameter="enabled",
    ),
    GardenaMowerBleSwitchEntityDescription(
        key="EcoMode",
        name="Eco Mode",
        icon="mdi:leaf",
        entity_category=EntityCategory.CONFIG,
        set_command="SetChargingStationLoopSignalGeneration",
        value_parameter="enabled",
        invert_value=True,
    ),
    *(
        GardenaMowerBleSwitchEntityDescription(
            key=f"StartingPoint{starting_point_id}Enabled",
            name=f"Starting Point {starting_point_id}",
            icon="mdi:map-marker-check",
            entity_category=EntityCategory.CONFIG,
            set_command="SetStartingPointEnabled",
            starting_point_id=starting_point_id,
            value_parameter="enabled",
        )
        for starting_point_id in range(1, 4)
    ),
    *(
        GardenaMowerBleSwitchEntityDescription(
            key=f"StartingPoint{starting_point_id}CorridorCut",
            name=f"Starting Point {starting_point_id} CorridorCut",
            icon="mdi:arrow-collapse-horizontal",
            entity_category=EntityCategory.CONFIG,
            set_command="SetStartingPointCorridorCut",
            starting_point_id=starting_point_id,
            value_parameter="corridorCut",
        )
        for starting_point_id in range(1, 4)
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GardenaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Gardena Automower BLE switch entities."""
    coordinator = entry.runtime_data

    async_add_entities(
        (
            GardenaMowerBleSpotCutSwitch(coordinator, description)
            if description.key == "spotCutting"
            else GardenaMowerBlePermanentParkSwitch(coordinator, description)
            if description.key == "permanentPark"
            else GardenaMowerBleSwitch(coordinator, description)
        )
        for description in DESCRIPTIONS
        if description.key in coordinator.data
        or description.key in ALWAYS_CREATE_SWITCHES
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
        state_enabled = enabled
        if description.invert_value:
            enabled = not enabled
        request = {description.value_parameter: enabled}
        if description.starting_point_id is not None:
            request["startingPointId"] = description.starting_point_id

        await self._async_setting_command_response(
            description.set_command,
            human_name=description.name or description.key,
            **request,
        )

        updates = {description.key: state_enabled}
        if description.key == "EcoMode":
            updates["ChargingStationLoopSignalGeneration"] = not state_enabled
        self.coordinator.update_cached_data(
            updates,
            recalculate_starting_point_share=description.key.startswith(
                "StartingPoint"
            )
            and description.key.endswith("Enabled"),
        )
        self.coordinator.schedule_settings_refresh()


class GardenaMowerBleSpotCutSwitch(GardenaMowerBleDescriptorEntity, SwitchEntity):
    """Representation of the SpotCut switch."""

    entity_description: SwitchEntityDescription
    _spot_cut_restore_state: dict | None

    def __init__(
        self, coordinator, description: SwitchEntityDescription
    ) -> None:
        """Initialize the SpotCut switch."""
        super().__init__(coordinator, description)
        self._spot_cut_restore_state = None

    @property
    def is_on(self) -> bool | None:
        """Return true if SpotCut is active."""
        value = self.coordinator.data.get(self.entity_description.key)
        if value is None:
            return None
        return bool(value)

    async def async_turn_on(self, **kwargs) -> None:
        """Start SpotCut."""
        await self._async_ensure_connected()
        if not self.is_on:
            self._spot_cut_restore_state = self._capture_restore_state()

        result = await self.coordinator.mower.mower_spot_cut()
        if result is not ResponseResult.OK:
            raise HomeAssistantError(f"Spot Cut failed: {result.name}")

        self.coordinator.update_cached_data({"spotCutting": 3})
        self.coordinator.schedule_action_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Stop SpotCut."""
        await self._async_ensure_connected()
        result = await self.coordinator.mower.mower_stop_spot_cut()
        if result is not ResponseResult.OK:
            raise HomeAssistantError(f"Stop Spot Cut failed: {result.name}")

        updates = {"spotCutting": 0}
        updates.update(await self._async_restore_previous_state())
        self._spot_cut_restore_state = None
        self.coordinator.update_cached_data(updates)
        self.coordinator.schedule_action_refresh()

    def _capture_restore_state(self) -> dict:
        """Capture enough mower state to restore after manual SpotCut stop."""
        data = self.coordinator.data or {}
        return {
            "activity": data.get("activity"),
            "state": data.get("state"),
            "mode": data.get("mode"),
            "override": data.get("override"),
            "permanentPark": data.get("permanentPark"),
        }

    async def _async_restore_previous_state(self) -> dict:
        """Best-effort restore of the mower state that existed before SpotCut."""
        restore_state = self._spot_cut_restore_state
        if not restore_state:
            return {}

        activity = restore_state.get("activity")
        mower_state = restore_state.get("state")
        mode = restore_state.get("mode")
        override = restore_state.get("override") or {}

        if restore_state.get("permanentPark") or mode is ModeOfOperation.HOME:
            result = await self.coordinator.mower.mower_park_permanently()
            if result is not ResponseResult.OK:
                raise HomeAssistantError(f"Restore previous state failed: {result.name}")
            return {
                "activity": MowerActivity.GOING_HOME,
                "state": MowerState.IN_OPERATION,
                "mode": ModeOfOperation.HOME,
                "permanentPark": True,
            }

        if mower_state is MowerState.PAUSED or activity is MowerActivity.STOPPED_IN_GARDEN:
            return {"state": MowerState.PAUSED}

        if activity in (
            MowerActivity.MOWING,
            MowerActivity.GOING_OUT,
        ) or override.get("action") is OverrideAction.FORCEDMOW:
            result = await self.coordinator.mower.mower_override(
                self._restore_duration_hours(override)
            )
            if result is not ResponseResult.OK:
                raise HomeAssistantError(f"Restore previous state failed: {result.name}")
            return {
                "activity": MowerActivity.MOWING,
                "state": MowerState.IN_OPERATION,
                "mode": ModeOfOperation.AUTO,
                "permanentPark": False,
            }

        result = await self.coordinator.mower.mower_park()
        if result is not ResponseResult.OK:
            raise HomeAssistantError(f"Restore previous state failed: {result.name}")
        return {
            "activity": MowerActivity.GOING_HOME,
            "state": MowerState.IN_OPERATION,
        }

    def _restore_duration_hours(self, override: dict) -> float:
        """Return remaining manual mowing duration from a previous override."""
        duration = override.get("duration")
        if not isinstance(duration, int) or duration <= 0:
            return self.coordinator.manual_mowing_duration_hours

        start_time = override.get("startTime")
        if isinstance(start_time, int) and start_time > 0:
            remaining = (start_time + duration) - int(time.time())
            if remaining > 0:
                duration = remaining

        return max(1 / 60, duration / 3600)

    async def _async_ensure_connected(self) -> None:
        """Connect to the mower if needed."""
        if self.coordinator.mower.is_connected():
            return

        device = bluetooth.async_ble_device_from_address(
            self.coordinator.hass, self.coordinator.address, connectable=True
        )
        if await self.coordinator.mower.connect(device) is not ResponseResult.OK:
            raise HomeAssistantError("Unable to connect to mower")


class GardenaMowerBlePermanentParkSwitch(GardenaMowerBleDescriptorEntity, SwitchEntity):
    """Representation of the park until further notice switch."""

    entity_description: SwitchEntityDescription

    @property
    def is_on(self) -> bool | None:
        """Return true if the mower is parked until further notice."""
        value = self.coordinator.data.get(self.entity_description.key)
        if value is None:
            return None
        return bool(value)

    async def async_turn_on(self, **kwargs) -> None:
        """Park until further notice."""
        await self._async_ensure_connected()
        result = await self.coordinator.mower.mower_park_permanently()
        if result is not ResponseResult.OK:
            raise HomeAssistantError(
                f"{self.entity_description.name} failed: {result.name}"
            )

        self.coordinator.update_cached_data(
            {
                "permanentPark": True,
                "mode": ModeOfOperation.HOME,
            }
        )
        self.coordinator.schedule_action_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        """Return the mower to scheduled operation."""
        await self._async_ensure_connected()
        result = await self.coordinator.mower.mower_resume_schedule()
        if result is not ResponseResult.OK:
            raise HomeAssistantError(
                f"{self.entity_description.name} failed: {result.name}"
            )

        self.coordinator.update_cached_data(
            {
                "permanentPark": False,
                "mode": ModeOfOperation.AUTO,
            }
        )
        self.coordinator.schedule_action_refresh()

    async def _async_ensure_connected(self) -> None:
        """Connect to the mower if needed."""
        if self.coordinator.mower.is_connected():
            return

        device = bluetooth.async_ble_device_from_address(
            self.coordinator.hass, self.coordinator.address, connectable=True
        )
        if await self.coordinator.mower.connect(device) is not ResponseResult.OK:
            raise HomeAssistantError("Unable to connect to mower")
