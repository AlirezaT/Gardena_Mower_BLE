"""Provides the DataUpdateCoordinator."""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from .automower_ble.mower import Mower
from .automower_ble.protocol import ResponseResult
from bleak import BleakError
from bleak_retry_connector import close_stale_connections_by_address

from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, LOGGER

if TYPE_CHECKING:
    from . import GardenaConfigEntry

SCAN_INTERVAL = timedelta(seconds=8)


class GardenaCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching data."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: GardenaConfigEntry,
        mower: Mower,
        address: str,
        channel_id: str,
        model: str,
    ) -> None:
        """Initialize global data updater."""
        super().__init__(
            hass=hass,
            logger=LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.address = address
        self.channel_id = channel_id
        self.model = model
        self.mower = mower
        self._spot_cutting_status_supported = True
        self._reversing_distance_supported = True
        self._starting_points_supported = True

    async def async_shutdown(self) -> None:
        """Shutdown coordinator and any connection."""
        LOGGER.debug("Shutdown")
        await super().async_shutdown()
        if self.mower.is_connected():
            await self.mower.disconnect()

    async def _async_find_device(self):
        LOGGER.debug("Trying to reconnect")
        await close_stale_connections_by_address(self.address)

        device = bluetooth.async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )

        try:
            if await self.mower.connect(device) is not ResponseResult.OK:
                raise UpdateFailed("Failed to connect")
        except BleakError as err:
            raise UpdateFailed("Failed to connect") from err

    async def _async_update_data(self) -> dict[str, Any]:
        """Poll the device."""
        LOGGER.debug("Polling device")
        

        data: dict[str, Any] = {}

        try:
            if not self.mower.is_connected():
                await self._async_find_device()
        except BleakError as err:
            raise UpdateFailed("Failed to connect") from err

        try:
            data["battery_level"] = await self.mower.battery_level()
            LOGGER.debug("battery_level" + str(data["battery_level"]))
            if data["battery_level"] is None:
                await self._async_find_device()
                raise UpdateFailed("Error getting data from device")

            data["activity"] = await self.mower.mower_activity()
            LOGGER.debug("activity:" + str(data["activity"]))
            if data["activity"] is None:
                await self._async_find_device()
                raise UpdateFailed("Error getting data from device")

            data["state"] = await self.mower.mower_state()
            LOGGER.debug("state:" + str(data["state"]))
            if data["state"] is None:
                await self._async_find_device()
                raise UpdateFailed("Error getting data from device")
            
            data["next_start_time"] = await self.mower.mower_next_start_time()
            LOGGER.debug("next_start_time: " + str(data["next_start_time"]))
#            if data["next_start_time"] is None:
#                await self._async_find_device()
#                raise UpdateFailed("Error getting data from device")

            data["errorCode"] = await self.mower.command("GetError")
            LOGGER.debug("errorCode: " + str(data["errorCode"]))

            data["NumberOfMessages"] = await self.mower.command("GetNumberOfMessages")
            LOGGER.debug("NumberOfMessages: " + str(data["NumberOfMessages"]))

            data["RemainingChargingTime"] = await self.mower.command("GetRemainingChargingTime")
            LOGGER.debug("RemainingChargingTime: " + str(data["RemainingChargingTime"]))

            try:
                data["DrivePastWire"] = await self.mower.command("GetDrivePastWire")
                LOGGER.debug("DrivePastWire: " + str(data["DrivePastWire"]))
            except KeyError:
                LOGGER.debug("GetDrivePastWire not found in protocol.json - skipping")

            if self._reversing_distance_supported:
                try:
                    result, reversing_distance = await self.mower.command_response(
                        "GetReversingDistance",
                        warn_on_error=False,
                    )
                    if result is ResponseResult.OK and reversing_distance is not None:
                        data["ReversingDistance"] = reversing_distance
                        LOGGER.debug("ReversingDistance: %s", reversing_distance)
                    else:
                        self._reversing_distance_supported = False
                        LOGGER.debug(
                            "GetReversingDistance returned %s - disabling reversing distance polling",
                            result.name,
                        )
                except (KeyError, ValueError, IndexError):
                    self._reversing_distance_supported = False
                    LOGGER.debug(
                        "GetReversingDistance failed - disabling reversing distance polling",
                        exc_info=True,
                    )

            if self._starting_points_supported:
                try:
                    starting_point_proportions = []
                    for starting_point_id in range(1, 4):
                        result, starting_point = await self.mower.command_response(
                            "GetStartingPoint",
                            warn_on_error=False,
                            startingPointId=starting_point_id,
                        )
                        if result is not ResponseResult.OK or starting_point is None:
                            LOGGER.debug(
                                "GetStartingPoint %s returned %s - stopping starting point polling",
                                starting_point_id,
                                result.name,
                            )
                            break

                        prefix = f"StartingPoint{starting_point_id}"
                        data[f"{prefix}Enabled"] = bool(starting_point["enabled"])
                        data[f"{prefix}Proportion"] = starting_point["proportion"]
                        data[f"{prefix}Wire"] = starting_point["wire"]
                        data[f"{prefix}Distance"] = starting_point["distance"]
                        data[f"{prefix}CorridorCut"] = bool(
                            starting_point["corridorCut"]
                        )
                        starting_point_proportions.append(
                            int(starting_point["proportion"])
                        )
                        LOGGER.debug("%s: %s", prefix, starting_point)

                    if starting_point_proportions:
                        data.setdefault(
                            "StartingPointChargingStationProportion",
                            max(
                                0,
                                100 - sum(starting_point_proportions),
                            ),
                        )
                    else:
                        self._starting_points_supported = False
                        LOGGER.debug(
                            "No starting points returned - disabling starting point polling"
                        )
                except (KeyError, ValueError, IndexError):
                    self._starting_points_supported = False
                    LOGGER.debug(
                        "GetStartingPoint failed - disabling starting point polling",
                        exc_info=True,
                    )

            if self._spot_cutting_status_supported:
                try:
                    result, spot_cutting = await self.mower.command_response(
                        "GetSpotCuttingState", warn_on_error=False
                    )
                    if result is ResponseResult.OK:
                        data["spotCutting"] = spot_cutting
                        LOGGER.debug("spotCutting: " + str(data["spotCutting"]))
                    else:
                        self._spot_cutting_status_supported = False
                        LOGGER.debug(
                            "GetSpotCuttingState returned %s - disabling spot cutting status polling",
                            result.name,
                        )
                except (KeyError, ValueError, IndexError):
                    self._spot_cutting_status_supported = False
                    LOGGER.debug(
                        "GetSpotCuttingState failed - disabling spot cutting status polling",
                        exc_info=True,
                    )

            # workaround for issue21
            try:
                data["statistics"] = await self.mower.command("GetAllStatistics")
                LOGGER.debug("statuses: " + str(data["statistics"]))

                # Flatten statistics into top-level coordinator data
                if data["statistics"]:
                    for key, value in data["statistics"].items():
                        data[key] = value

            except ValueError as e:
                if "Data length mismatch" in str(e):
                    LOGGER.debug("Known fail on GetAllStatistics - skipping")
                    data["statistics"] = None
                else:
                    raise

            data["operatorstate"] = await self.mower.command("IsOperatorLoggedIn")
            LOGGER.debug("IsOperatorLoggedIn: " + str(data["operatorstate"]))

            data["last_message"] = await self.mower.command("GetMessage", messageId=0)
            LOGGER.debug("last_message: " + str(data["last_message"]))

            self._last_successful_update = datetime.now()
            self._last_data = data


        except BleakError as err:
            LOGGER.error("Error getting data from device")
            await self._async_find_device()
            raise UpdateFailed("Error getting data from device") from err
        
        LOGGER.debug("MOWER DATA: %s", data)

        return data
