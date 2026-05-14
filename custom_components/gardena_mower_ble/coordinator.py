"""Provides the DataUpdateCoordinator."""

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from .automower_ble.mower import Mower
from .automower_ble.protocol import ResponseResult
from .automower_ble.error_codes import ErrorCodes
from bleak import BleakError
from bleak_retry_connector import close_stale_connections_by_address

from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, LOGGER

if TYPE_CHECKING:
    from . import GardenaConfigEntry

SCAN_INTERVAL = timedelta(seconds=8)
ACTION_REFRESH_DELAY = 4
DEFAULT_MANUAL_MOWING_DURATION_HOURS = 3.0


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
        self._comboard_sensor_data_supported = True
        self._signal_quality_supported = True
        self._battery_diagnostics_supported = True
        self._orientation_diagnostics_supported = True
        self._sensor_control_supported = True
        self._frost_sensor_supported = True
        self._unsupported_static_commands: set[str] = set()
        self._static_data: dict[str, Any] = {}
        self.manual_mowing_duration_hours = DEFAULT_MANUAL_MOWING_DURATION_HOURS
        self._delayed_refresh_cancel = None

    async def async_shutdown(self) -> None:
        """Shutdown coordinator and any connection."""
        LOGGER.debug("Shutdown")
        await super().async_shutdown()
        if self.mower.is_connected():
            await self.mower.disconnect()
        if self._delayed_refresh_cancel is not None:
            self._delayed_refresh_cancel()
            self._delayed_refresh_cancel = None

    def schedule_action_refresh(self) -> None:
        """Schedule one follow-up refresh after an action state transition."""
        if self._delayed_refresh_cancel is not None:
            self._delayed_refresh_cancel()

        async def _refresh(_now) -> None:
            self._delayed_refresh_cancel = None
            await self.async_request_refresh()

        self._delayed_refresh_cancel = async_call_later(
            self.hass,
            ACTION_REFRESH_DELAY,
            _refresh,
        )

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
        data["ManualMowingDuration"] = self.manual_mowing_duration_hours
        data["modelName"] = self.model

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

            await self._async_update_static_info(data)

            if self._battery_diagnostics_supported:
                try:
                    battery_diagnostics = {
                        "batteryVoltage": "GetBatteryVoltage",
                        "batteryCurrent": "GetBatteryCurrent",
                        "batteryTemperature": "GetBatteryTemperature",
                    }
                    for key, command_name in battery_diagnostics.items():
                        result, value = await self.mower.command_response(
                            command_name, warn_on_error=False
                        )
                        if result is not ResponseResult.OK or value is None:
                            self._battery_diagnostics_supported = False
                            LOGGER.debug(
                                "%s returned %s - disabling battery diagnostic polling",
                                command_name,
                                result.name,
                            )
                            break
                        data[key] = value
                    LOGGER.debug(
                        "Battery diagnostics: voltage=%s current=%s temperature=%s",
                        data.get("batteryVoltage"),
                        data.get("batteryCurrent"),
                        data.get("batteryTemperature"),
                    )
                except (KeyError, ValueError, IndexError):
                    self._battery_diagnostics_supported = False
                    LOGGER.debug(
                        "Battery diagnostics failed - disabling battery diagnostic polling",
                        exc_info=True,
                    )

            try:
                data["DrivePastWire"] = await self.mower.command("GetDrivePastWire")
                LOGGER.debug("DrivePastWire: " + str(data["DrivePastWire"]))
            except KeyError:
                LOGGER.debug("GetDrivePastWire not found in protocol.json - skipping")

            if self._sensor_control_supported:
                try:
                    sensor_control_commands = {
                        "SensorControlEnabled": "GetSensorControlEnabled",
                        "SensorControlSensitivity": "GetSensorControlSensitivity",
                    }
                    for key, command_name in sensor_control_commands.items():
                        result, value = await self.mower.command_response(
                            command_name, warn_on_error=False
                        )
                        if result is not ResponseResult.OK or value is None:
                            self._sensor_control_supported = False
                            LOGGER.debug(
                                "%s returned %s - disabling SensorControl polling",
                                command_name,
                                result.name,
                            )
                            break
                        data[key] = value
                    LOGGER.debug(
                        "SensorControl: enabled=%s sensitivity=%s",
                        data.get("SensorControlEnabled"),
                        data.get("SensorControlSensitivity"),
                    )
                except (KeyError, ValueError, IndexError):
                    self._sensor_control_supported = False
                    LOGGER.debug(
                        "SensorControl polling failed - disabling SensorControl polling",
                        exc_info=True,
                    )

            if self._frost_sensor_supported:
                try:
                    result, frost_sensor_enabled = await self.mower.command_response(
                        "GetFrostSensorEnabled", warn_on_error=False
                    )
                    if result is ResponseResult.OK and frost_sensor_enabled is not None:
                        data["FrostSensorEnabled"] = frost_sensor_enabled
                        LOGGER.debug("FrostSensorEnabled: %s", frost_sensor_enabled)
                    else:
                        self._frost_sensor_supported = False
                        LOGGER.debug(
                            "GetFrostSensorEnabled returned %s - disabling frost sensor polling",
                            result.name,
                        )
                except (KeyError, ValueError, IndexError):
                    self._frost_sensor_supported = False
                    LOGGER.debug(
                        "GetFrostSensorEnabled failed - disabling frost sensor polling",
                        exc_info=True,
                    )

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

            if self._comboard_sensor_data_supported:
                try:
                    result, sensor_data = await self.mower.command_response(
                        "GetComboardSensorData", warn_on_error=False
                    )
                    if result is ResponseResult.OK and sensor_data is not None:
                        data.update(sensor_data)
                        LOGGER.debug("ComboardSensorData: %s", sensor_data)
                    else:
                        self._comboard_sensor_data_supported = False
                        LOGGER.debug(
                            "GetComboardSensorData returned %s - disabling realtime sensor polling",
                            result.name,
                        )
                except (KeyError, ValueError, IndexError):
                    self._comboard_sensor_data_supported = False
                    LOGGER.debug(
                        "GetComboardSensorData failed - disabling realtime sensor polling",
                        exc_info=True,
                    )

            if self._signal_quality_supported:
                try:
                    result, signal_quality = await self.mower.command_response(
                        "GetSignalQuality", warn_on_error=False
                    )
                    if result is ResponseResult.OK and signal_quality is not None:
                        data.update(signal_quality)
                        LOGGER.debug("SignalQuality: %s", signal_quality)
                    else:
                        self._signal_quality_supported = False
                        LOGGER.debug(
                            "GetSignalQuality returned %s - disabling signal quality polling",
                            result.name,
                        )
                except (KeyError, ValueError, IndexError):
                    self._signal_quality_supported = False
                    LOGGER.debug(
                        "GetSignalQuality failed - disabling signal quality polling",
                        exc_info=True,
                    )

            if self._orientation_diagnostics_supported:
                try:
                    orientation_diagnostics = {
                        "orientationPitch": "GetOrientationPitch",
                        "orientationRoll": "GetOrientationRoll",
                    }
                    for key, command_name in orientation_diagnostics.items():
                        result, value = await self.mower.command_response(
                            command_name, warn_on_error=False
                        )
                        if result is not ResponseResult.OK or value is None:
                            self._orientation_diagnostics_supported = False
                            LOGGER.debug(
                                "%s returned %s - disabling orientation diagnostic polling",
                                command_name,
                                result.name,
                            )
                            break
                        data[key] = value
                    LOGGER.debug(
                        "Orientation diagnostics: pitch=%s roll=%s",
                        data.get("orientationPitch"),
                        data.get("orientationRoll"),
                    )
                except (KeyError, ValueError, IndexError):
                    self._orientation_diagnostics_supported = False
                    LOGGER.debug(
                        "Orientation diagnostics failed - disabling orientation diagnostic polling",
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

            try:
                data["last_message"] = await self.mower.command(
                    "GetMessage", messageId=0
                )
                LOGGER.debug("last_message: " + str(data["last_message"]))
            except (ValueError, IndexError) as err:
                LOGGER.debug("Unable to read last mower message: %s", err)

            self._last_successful_update = datetime.now()
            self._last_data = data


        except BleakError as err:
            LOGGER.error("Error getting data from device")
            await self._async_find_device()
            raise UpdateFailed("Error getting data from device") from err
        
        LOGGER.debug("MOWER DATA: %s", data)

        return data

    async def _async_update_static_info(self, data: dict[str, Any]) -> None:
        """Fetch mostly-static mower information and copy it into coordinator data."""
        static_commands = {
            "mowerName": "GetUserMowerNameAsAsciiString",
            "serialNumber": "GetSerialNumber",
            "hardwareSerialNumber": "GetHwSerialNumber",
            "hardwareRevision": "GetHardwareRevision",
            "productionTime": "GetProductionTime",
            "nodeIprId": "GetNodeIprId",
            "husqvarnaId": "GetHusqvarnaId",
            "bootSoftwareVersion": "GetSwVersionStringBoot",
            "applicationSoftwareVersion": "GetSwVersionStringAppl",
            "subSoftwareVersion": "GetSwVersionStringSub",
        }

        for key, command_name in static_commands.items():
            if (
                key in self._static_data
                or command_name in self._unsupported_static_commands
            ):
                continue
            try:
                result, value = await self.mower.command_response(
                    command_name, warn_on_error=False
                )
            except (KeyError, ValueError, IndexError):
                self._unsupported_static_commands.add(command_name)
                LOGGER.debug("%s failed - disabling static info polling", command_name)
                continue

            if result is not ResponseResult.OK or value is None:
                self._unsupported_static_commands.add(command_name)
                LOGGER.debug(
                    "%s returned %s - disabling static info polling",
                    command_name,
                    result.name,
                )
                continue

            if key == "productionTime":
                value = datetime.fromtimestamp(value, timezone.utc)
            self._static_data[key] = value

        data.update(self._static_data)

    async def log_error_history(self, max_entries: int | None = None) -> None:
        """Read mower message history and write it to the HA log."""
        count = await self.mower.command("GetNumberOfMessages")
        if count is None:
            LOGGER.warning("Unable to read mower message history count")
            return

        entries_to_read = min(int(count), max_entries or int(count))
        LOGGER.info(
            "Reading %s of %s mower message history entries", entries_to_read, count
        )
        for message_id in range(entries_to_read):
            try:
                message = await self.mower.command("GetMessage", messageId=message_id)
            except (ValueError, IndexError) as err:
                LOGGER.warning("Unable to read mower message %s: %s", message_id, err)
                continue
            if not message:
                continue

            code = message.get("code")
            timestamp = message.get("time")
            time_text = (
                datetime.fromtimestamp(timestamp, timezone.utc).isoformat()
                if isinstance(timestamp, int) and timestamp > 0
                else "unknown time"
            )
            LOGGER.info(
                "Mower message %s: %s, code=%s, severity=%s, time=%s",
                message_id,
                self._describe_error_code(code),
                code,
                message.get("severity"),
                time_text,
            )

    @staticmethod
    def _describe_error_code(error_code: object) -> str:
        """Return a readable mower error description."""
        if not isinstance(error_code, int):
            return "Unknown error"
        if error_code == 0:
            return "No error"
        try:
            return ErrorCodes(error_code).name.replace("_", " ").title()
        except ValueError:
            return f"Unknown error ({error_code})"
