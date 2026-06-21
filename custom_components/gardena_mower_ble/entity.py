"""Provides the GardenaMowerBleEntity."""

import asyncio
from contextlib import suppress
from typing import Any

from bleak_retry_connector import close_stale_connections_by_address
from homeassistant.components import bluetooth
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import (
    CONNECTION_BLUETOOTH,
    DeviceInfo,
    format_mac,
)
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .automower_ble.protocol import ResponseResult
from .const import DOMAIN, MANUFACTURER
from .coordinator import GardenaCoordinator

TRANSIENT_WRITE_RESULTS = {
    ResponseResult.UNKNOWN_ERROR,
    ResponseResult.DEVICE_BUSY,
}
WRITE_RETRY_ATTEMPTS = 3
WRITE_RETRY_DELAY = 1.0


class GardenaMowerBleEntity(CoordinatorEntity[GardenaCoordinator]):
    """GardenaCoordinator entity for Gardena Automower Bluetooth."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: GardenaCoordinator) -> None:
        """Initialize coordinator entity."""
        super().__init__(coordinator)

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{coordinator.address}_{coordinator.channel_id}")},
            manufacturer=MANUFACTURER,
            model_id=coordinator.model,
            suggested_area="Garden",
            connections={(CONNECTION_BLUETOOTH, format_mac(coordinator.address))},
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.has_recent_data()


class GardenaMowerBleDescriptorEntity(GardenaMowerBleEntity):
    """Coordinator entity for entities with entity description."""

    def __init__(
        self, coordinator: GardenaCoordinator, description: EntityDescription
    ) -> None:
        """Initialize description entity."""
        super().__init__(coordinator)

        self._attr_unique_id = (
            f"{coordinator.address}_{coordinator.channel_id}_{description.key}"
        )
        self.entity_description = description

    async def _async_ensure_connected(self) -> None:
        """Connect to the mower if needed."""
        if self.coordinator.mower.is_connected():
            return

        await close_stale_connections_by_address(self.coordinator.address)
        device = bluetooth.async_ble_device_from_address(
            self.coordinator.hass, self.coordinator.address, connectable=True
        )
        if await self.coordinator.mower.connect(device) is not ResponseResult.OK:
            raise HomeAssistantError("Unable to connect to mower")

    async def _async_setting_command_response(
        self,
        command_name: str,
        *,
        human_name: str,
        attempts: int = WRITE_RETRY_ATTEMPTS,
        retry_delay: float = WRITE_RETRY_DELAY,
        **kwargs: Any,
    ) -> tuple[ResponseResult, Any]:
        """Send an idempotent setting command with short BLE retries."""
        last_result: ResponseResult | None = None
        last_error: Exception | None = None

        for attempt in range(1, attempts + 1):
            try:
                await self._async_ensure_connected()
                result, value = await self.coordinator.mower.command_response(
                    command_name,
                    **kwargs,
                )
            except (KeyError, ValueError) as err:
                raise HomeAssistantError(f"{human_name} failed: {err}") from err
            except Exception as err:
                last_error = err
                if self.coordinator.mower.is_connected():
                    with suppress(Exception):
                        await self.coordinator.mower.disconnect()
            else:
                if result is ResponseResult.OK:
                    return result, value
                if result not in TRANSIENT_WRITE_RESULTS:
                    raise HomeAssistantError(f"{human_name} failed: {result.name}")
                last_result = result
                if self.coordinator.mower.is_connected():
                    with suppress(Exception):
                        await self.coordinator.mower.disconnect()

            if attempt < attempts:
                await asyncio.sleep(retry_delay)

        if last_result is not None:
            raise HomeAssistantError(
                f"{human_name} failed after {attempts} attempts: {last_result.name}"
            )
        raise HomeAssistantError(
            f"{human_name} failed after {attempts} attempts: {last_error}"
        ) from last_error
