"""The Gardena Autoconnect Bluetooth integration."""

from .automower_ble.mower import Mower
from .automower_ble.protocol import ResponseResult
from bleak import BleakError
from bleak_retry_connector import close_stale_connections_by_address, get_device
import voluptuous as vol

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, CONF_CLIENT_ID, CONF_PIN, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
    HomeAssistantError,
)

from .const import DOMAIN, LOGGER
from .coordinator import GardenaCoordinator

type GardenaConfigEntry = ConfigEntry[GardenaCoordinator]

PLATFORMS = [
    Platform.BUTTON,
    Platform.CALENDAR,
    Platform.LAWN_MOWER,
    Platform.NUMBER,
    Platform.SENSOR,
]

SERVICE_CLEAR_SCHEDULE = "clear_schedule"
SERVICE_DELETE_SCHEDULE = "delete_schedule"


async def async_setup_entry(hass: HomeAssistant, entry: GardenaConfigEntry) -> bool:
    """Set up Gardena Autoconnect Bluetooth from a config entry."""
    _async_register_services(hass)

    if CONF_PIN not in entry.data:
        raise ConfigEntryAuthFailed(
            translation_domain=DOMAIN,
            translation_key="pin_required",
            translation_placeholders={"domain_name": "Gardena Automower BLE"},
        )

    address = entry.data[CONF_ADDRESS]
    pin = int(entry.data[CONF_PIN])
    channel_id = entry.data[CONF_CLIENT_ID]

    mower = Mower(channel_id, address, pin)

    await close_stale_connections_by_address(address)

    LOGGER.debug("connecting to %s with channel ID %s", address, str(channel_id))
    try:
        device = bluetooth.async_ble_device_from_address(
            hass, address, connectable=True
        ) or await get_device(address)
        response_result = await mower.connect(device)
        if response_result == ResponseResult.INVALID_PIN:
            raise ConfigEntryAuthFailed(
                f"Unable to connect to device {address} due to wrong PIN"
            )
        if response_result != ResponseResult.OK:
            raise ConfigEntryNotReady(
                f"Unable to connect to device {address}, mower returned {response_result}"
            )
    except (TimeoutError, BleakError) as exception:
        raise ConfigEntryNotReady(
            f"Unable to connect to device {address} due to {exception}"
        ) from exception

    LOGGER.debug("connected and paired")

    model = await mower.get_model()
    LOGGER.debug("Connected to Automower: %s", model)

    coordinator = GardenaCoordinator(hass, entry, mower, address, channel_id, model)

    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


def _async_register_services(hass: HomeAssistant) -> None:
    """Register integration services."""
    async def async_delete_schedule(call: ServiceCall) -> None:
        """Delete one mower schedule task by its 1-based index."""
        coordinator = await _async_get_service_coordinator(
            hass, call.data.get("config_entry_id")
        )
        schedule_index = call.data["index"] - 1
        tasks = await coordinator.mower.get_tasks()
        if schedule_index < 0 or schedule_index >= len(tasks):
            raise HomeAssistantError(f"Schedule {call.data['index']} does not exist")

        del tasks[schedule_index]
        await coordinator.mower.set_tasks(tasks)
        await coordinator.async_request_refresh()

    async def async_clear_schedule(call: ServiceCall) -> None:
        """Clear all mower schedule tasks."""
        coordinator = await _async_get_service_coordinator(
            hass, call.data.get("config_entry_id")
        )
        await coordinator.mower.clear_tasks()
        await coordinator.async_request_refresh()

    if not hass.services.has_service(DOMAIN, SERVICE_DELETE_SCHEDULE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_DELETE_SCHEDULE,
            async_delete_schedule,
            schema=vol.Schema(
                {
                    vol.Required("index"): vol.All(vol.Coerce(int), vol.Range(min=1)),
                    vol.Optional("config_entry_id"): str,
                }
            ),
        )

    if not hass.services.has_service(DOMAIN, SERVICE_CLEAR_SCHEDULE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_CLEAR_SCHEDULE,
            async_clear_schedule,
            schema=vol.Schema({vol.Optional("config_entry_id"): str}),
        )


async def _async_get_service_coordinator(
    hass: HomeAssistant, entry_id: str | None
) -> GardenaCoordinator:
    """Return the coordinator targeted by a service call."""
    entries = [
        entry
        for entry in hass.config_entries.async_entries(DOMAIN)
        if getattr(entry, "runtime_data", None) is not None
        and (entry_id is None or entry.entry_id == entry_id)
    ]
    if not entries:
        raise HomeAssistantError("No loaded Gardena mower BLE config entry found")
    if entry_id is None and len(entries) > 1:
        raise HomeAssistantError(
            "config_entry_id is required when multiple mowers are loaded"
        )

    coordinator: GardenaCoordinator = entries[0].runtime_data
    if not coordinator.mower.is_connected():
        await coordinator._async_find_device()

    return coordinator


async def async_unload_entry(hass: HomeAssistant, entry: GardenaConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator: GardenaCoordinator = entry.runtime_data
        await coordinator.async_shutdown()

    return unload_ok
