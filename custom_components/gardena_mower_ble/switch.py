"""Support for switch entities."""

from __future__ import annotations

from dataclasses import dataclass
import time

from automower_ble.protocol import (
    ModeOfOperation,
    MowerActivity,
    MowerState,
    OverrideAction,
    ResponseResult,
)

from homeassistant.components import bluetooth
from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GardenaConfigEntry
from .entity import GardenaMowerBleDescriptorEntity
from .settings_protocol import set_starting_point_enabled

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
    required_key: str | None = None


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
        key="FrostSensorEnabled",
        name="Frost Sensor",
        icon="mdi:snowflake",
        entity_category=EntityCategory.CONFIG,
        set_command="SetFrostSensorEnabled",
        value_parameter="enabled",
        required_key="FrostSensorWritable",
    ),
    GardenaMowerBleSwitchEntityDescription(
        key="GarageEnabled",
        name="Avoid Garage",
        icon="mdi:garage",
        entity_category=EntityCategory.CONFIG,
        set_command="SetGarageEnabled",
        value_parameter="enabled",
    ),
    GardenaMowerBleSwitchEntityDescription(
        key="ZoneProtectEnabled",
        name="ZoneProtect",
        icon="mdi:shield-outline",
        entity_category=EntityCategory.CONFIG,
        set_command="SetZoneProtectEnabled",
        value_parameter="enabled",
        required_key="zoneProtectSupported",
    ),
    GardenaMowerBleSwitchEntityDescription(
        key="AntiCollisionRadarEnabled",
        name="Anti-collision Radar",
        icon="mdi:radar",
        entity_category=EntityCategory.CONFIG,
        set_command="SetAntiCollisionRadarEnabled",
        value_parameter="enabled",
        required_key="AntiCollisionRadarAvailable",
    ),
    GardenaMowerBleSwitchEntityDescription(
        key="EcoMode",
        name="Eco Mode",
        icon="mdi:leaf",
        entity_category=EntityCategory.CONFIG,
        set_command="SetEcoModeEnabled",
        value_parameter="enabled",
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
        for starting_point_id in range(1, 6)
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
        for starting_point_id in range(1, 6)
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GardenaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Gardena Automower BLE switch entities."""
    coordinator = entry.runtime_data

    def should_create(description: SwitchEntityDescription) -> bool:
        """Return true if this switch is supported by the mower data."""
        if coordinator.capabilities.entity_is_model_excluded(description.key):
            return False
        if description.key == "spotCutting" and coordinator.capabilities.platform not in ("P0", "P005"):
            if coordinator.data.get("spotCutting") is None:
                return False
        if isinstance(description, GardenaMowerBleSwitchEntityDescription):
            capabilities = coordinator.capabilities
            if description.starting_point_id is not None:
                if description.starting_point_id > capabilities.point_count:
                    return False
                if description.set_command == "SetStartingPointCorridorCut" and capabilities.corridor_read is None:
                    return False
            if description.key == "GarageEnabled" and not capabilities.garage:
                return False
            if description.key == "AntiCollisionRadarEnabled" and not capabilities.radar:
                return False
            if description.key == "ZoneProtectEnabled" and capabilities.zone_group is None:
                return False
        if (
            description.key not in coordinator.data
            and description.key not in ALWAYS_CREATE_SWITCHES
        ):
            return False
        if (
            isinstance(description, GardenaMowerBleSwitchEntityDescription)
            and description.required_key is not None
        ):
            return bool(coordinator.data.get(description.required_key))
        return True

    async_add_entities(
        (
            GardenaMowerBleSpotCutSwitch(coordinator, description)
            if description.key == "spotCutting"
            else GardenaMowerBlePermanentParkSwitch(coordinator, description)
            if description.key == "permanentPark"
            else GardenaMowerBleSwitch(coordinator, description)
        )
        for description in DESCRIPTIONS
        if should_create(description)
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

        command = description.set_command
        if description.key == "ZoneProtectEnabled":
            if self.coordinator.data.get("zoneProtectSupported") is not True:
                raise HomeAssistantError(
                    "ZoneProtect availability has not been confirmed; refresh settings first"
                )
        if description.key == "FrostSensorEnabled":
            command = self.coordinator.data.get("FrostSensorSetCommand")
            if command not in ("SetFrostSensorEnabled", "SetFrostSensorV1Enabled"):
                raise HomeAssistantError("Frost sensor module has not been confirmed; refresh settings first")

        if command == "SetStartingPointEnabled":
            await self._async_ensure_connected()
            try:
                result, _ = await set_starting_point_enabled(
                    self.coordinator.mower, description.starting_point_id, state_enabled
                )
                if result is not ResponseResult.OK:
                    raise HomeAssistantError(f"Starting point update/read-back failed: {result.name}")
            finally:
                self.coordinator.schedule_settings_refresh()
        else:
            await self._async_setting_command_response(
                command,
                human_name=description.name or description.key,
                **request,
            )

        updates = {description.key: state_enabled}
        if command == "SetStartingPointEnabled" and not state_enabled:
            updates[f"StartingPoint{description.starting_point_id}Proportion"] = 0
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
            override = self._spot_cut_restore_state.get("override") or {}
            if override.get("action") is OverrideAction.FORCEDMOW:
                # Compare device timestamps in their own clock domain, then use
                # monotonic elapsed time so host timezone/DST cannot extend a run.
                captured_at = time.monotonic()
                result, mower_time = await self.coordinator.mower.command_response("GetTime")
                start, duration = override.get("startTime"), override.get("duration")
                if (result is ResponseResult.OK and type(mower_time) is int
                    and type(start) is int and type(duration) is int
                    and 0 < start <= mower_time and duration > 0):
                    self._spot_cut_restore_state["override_deadline"] = captured_at + max(
                        0, start + duration - mower_time
                    )

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

        if override.get("action") is OverrideAction.FORCEDMOW:
            duration = self._restore_duration_hours(override)
            if duration <= 0:
                # Missing/expired timing is not permission for another full run.
                result = await self.coordinator.mower.mower_park()
                if result is not ResponseResult.OK:
                    raise HomeAssistantError(f"Restore previous state failed: {result.name}")
                return {"activity": MowerActivity.GOING_HOME}
            result = await self.coordinator.mower.mower_override(duration)
            if result is not ResponseResult.OK:
                raise HomeAssistantError(f"Restore previous state failed: {result.name}")
            return {
                "activity": MowerActivity.MOWING,
                "state": MowerState.IN_OPERATION,
                "mode": ModeOfOperation.AUTO,
                "permanentPark": False,
            }

        if activity in (MowerActivity.MOWING, MowerActivity.GOING_OUT):
            # Restore the planner, not a new manual mowing allowance. Deliberately
            # leave physical activity to the next poll instead of claiming mowing.
            result = await self.coordinator.mower.mower_resume_schedule()
            if result is not ResponseResult.OK:
                raise HomeAssistantError(f"Restore schedule failed: {result.name}")
            result = await self.coordinator.mower.mower_resume()
            if result is not ResponseResult.OK:
                raise HomeAssistantError(f"Resume schedule failed: {result.name}")
            return {"mode": ModeOfOperation.AUTO, "permanentPark": False}

        result = await self.coordinator.mower.mower_park()
        if result is not ResponseResult.OK:
            raise HomeAssistantError(f"Restore previous state failed: {result.name}")
        return {
            "activity": MowerActivity.GOING_HOME,
            "state": MowerState.IN_OPERATION,
        }

    def _restore_duration_hours(self, override: dict) -> float:
        """Return remaining manual mowing duration from a previous override."""
        deadline = (self._spot_cut_restore_state or {}).get("override_deadline")
        if type(deadline) not in (int, float):
            return 0
        return max(0, deadline - time.monotonic()) / 3600

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
