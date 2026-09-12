"""Support for number entities."""

from __future__ import annotations

from dataclasses import dataclass, replace

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
    RestoreNumber,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfLength, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import GardenaConfigEntry
from .const import LOGGER
from .duration import CONF_MANUAL_MOWING_DURATION, validate_duration
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
        key="ManualMowingDuration",
        name="Manual Mowing Duration",
        icon="mdi:timer-play-outline",
        native_min_value=0.5,
        native_max_value=24,
        native_step=0.5,
        native_unit_of_measurement=UnitOfTime.HOURS,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        set_command="",
        value_parameter="duration",
    ),
    GardenaMowerBleNumberEntityDescription(
        key="DrivePastWire",
        name="Drive Past Wire",
        icon="mdi:map-marker-distance",
        native_min_value=20,
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
        native_max_value=300,
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
        for starting_point_id in range(1, 6)
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
        for starting_point_id in range(1, 6)
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GardenaConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Gardena Automower BLE number entities."""
    coordinator = entry.runtime_data

    descriptions = []
    for description in DESCRIPTIONS:
        if description.starting_point_id is not None and description.starting_point_id > coordinator.capabilities.point_count:
            continue
        if description.starting_point_id is not None and description.value_parameter == "distance":
            bounds = coordinator.capabilities.point_distance_bounds
            if bounds is None:
                continue
            description = replace(description, native_min_value=bounds[0], native_max_value=bounds[1])
        if description.key in ("DrivePastWire", "ReversingDistance"):
            bounds = (coordinator.capabilities.drive_bounds if description.key == "DrivePastWire"
                      else coordinator.capabilities.reversing_bounds)
            if bounds is None:
                continue
            description = replace(description, native_min_value=bounds[0], native_max_value=bounds[1])
        descriptions.append(description)

    async_add_entities(
        (
            GardenaMowerBleManualDuration(coordinator, description)
            if description.key == "ManualMowingDuration"
            else GardenaMowerBleNumber(coordinator, description)
        )
        for description in descriptions
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

        return float(value) / self.entity_description.scale

    async def async_set_native_value(self, value: float) -> None:
        """Set the number value."""
        description = self.entity_description
        LOGGER.debug("Setting %s to %s", description.key, value)
        if description.key == "ManualMowingDuration":
            self.coordinator.set_manual_mowing_duration(value)
            return

        if (
            description.value_parameter == "proportion"
            and description.starting_point_id is not None
        ):
            if any(
                self.coordinator.data.get(f"StartingPoint{point_id}Proportion") is None
                for point_id in range(1, self.coordinator.capabilities.point_count + 1)
                if point_id != description.starting_point_id
            ):
                raise HomeAssistantError("Refresh all starting point shares before changing a share")
            other_total = sum(
                int(
                    self.coordinator.data.get(
                        f"StartingPoint{starting_point_id}Proportion"
                    )
                    or 0
                )
                for starting_point_id in range(1, self.coordinator.capabilities.point_count + 1)
                if starting_point_id != description.starting_point_id
            )
            if other_total + round(value) > 100:
                raise HomeAssistantError(
                    "Starting point mowing shares cannot exceed 100% total"
                )

        kwargs = {
            description.value_parameter: round(value * description.scale),
        }
        if description.starting_point_id is not None:
            kwargs["startingPointId"] = description.starting_point_id

        native_value = round(value * description.scale)
        await self._async_setting_command_response(
            description.set_command,
            human_name=description.name or description.key,
            **kwargs,
        )

        self.coordinator.update_cached_data(
            {description.key: native_value},
            recalculate_starting_point_share=description.value_parameter
            == "proportion",
        )
        self.coordinator.schedule_settings_refresh()


class GardenaMowerBleManualDuration(GardenaMowerBleNumber, RestoreNumber):
    """Restore the previous virtual number when upgrading an existing entry."""

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if CONF_MANUAL_MOWING_DURATION in self.coordinator.config_entry.options:
            return
        restored = await self.async_get_last_number_data()
        if restored is not None:
            previous_value = restored.native_value
        else:
            # Versions before 3.08 did not store Number extra data.
            state = await self.async_get_last_state()
            if state is None:
                return
            previous_value = state.state
        try:
            value = validate_duration(previous_value)
        except (TypeError, ValueError):
            return
        self.coordinator.set_manual_mowing_duration(value)
