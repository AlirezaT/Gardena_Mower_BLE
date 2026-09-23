"""Serialized, result-checked model-dependent actions."""

import asyncio
import logging
from time import monotonic

from automower_ble.protocol import ModeOfOperation, MowerActivity, MowerState, OverrideAction, ResponseResult
from bleak import BleakError
from .parking import INDEFINITE, TIMED, NEXT_SCHEDULE, PARKING_OPTIONS, validate_parking_duration

_LOGGER = logging.getLogger(__name__)
PARK_OBSERVATION_SECONDS = 15
PARK_POLL_SECONDS = 2


class ActionMixin:
    async def mower_override(self, duration_hours=3.0):
        """Match the app's timed-start sequence on the P0 platform."""
        if self.capabilities.platform != "P0":
            return await super().mower_override(duration_hours)
        if duration_hours <= 0:
            raise ValueError("Duration must be greater than 0")
        async with self.lock:
            # ClearOverride belongs to resume-schedule, not this app path.
            for command, values in (
                ("SetMode", {"mode": ModeOfOperation.AUTO}),
                ("SetOverrideMow", {"duration": int(duration_hours * 3600)}),
                ("StartTrigger", {}),
            ):
                started = monotonic()
                _LOGGER.debug("P0 timed start: sending %s", command)
                try:
                    result, _ = await self.command_response_locked(
                        command, warn_on_error=False, **values
                    )
                except BaseException as err:
                    # No exception text/payloads: they may contain private data.
                    _LOGGER.debug("P0 timed start: %s ended with %s after %.3fs", command, type(err).__name__, monotonic() - started)
                    raise
                _LOGGER.debug("P0 timed start: %s result=%s elapsed=%.3fs", command, result.name, monotonic() - started)
                if command == "StartTrigger":
                    if result is ResponseResult.OK:
                        return result
                    # Retain upstream's existing state confirmation/timing;
                    # change only the command sequence in this experiment.
                    return await self._start_trigger_result_locked(
                        result, "manual mowing",
                        (MowerActivity.GOING_OUT, MowerActivity.MOWING),
                    )
                if result is not ResponseResult.OK:
                    return result

    async def _spot_cut_available(self):
        if self.capabilities.platform in ("P0", "P005"):
            return True
        if self.capabilities.platform not in ("P005GA", "P14"):
            return False
        result, available = await self.command_response(
            "GetSpotCutAvailable", warn_on_error=False
        )
        return (
            result is ResponseResult.OK
            and type(available) in (bool, int)
            and available == 1
        )

    async def mower_spot_cut(self):
        async with self.lock:
            if not await self._spot_cut_available():
                return ResponseResult.NOT_AVAILABLE
            if self.capabilities.platform == "P005":
                # Preserve the owner's physically tested Minimo command sequence.
                return await super().mower_spot_cut()
            commands = [("Pause", {}), ("SetMode", {"mode": ModeOfOperation.AUTO})]
            if self.capabilities.generation == 3:
                commands.extend(
                    [("SetOverrideMow", {"duration": 300}), ("StartSpotCutting", {})]
                )
            else:
                commands.append(("PrepareSpotCutting", {}))
            commands.append(("StartTrigger", {}))
            return await self._action_sequence(commands)

    async def mower_stop_spot_cut(self):
        async with self.lock:
            if not await self._spot_cut_available():
                return ResponseResult.NOT_AVAILABLE
            if self.capabilities.platform == "P005":
                return await super().mower_stop_spot_cut()
            command = (
                "StopSpotCutting"
                if self.capabilities.generation == 3
                else "AbortSpotCutting"
            )
            return await self._action_sequence([(command, {})])

    async def _action_sequence(self, commands):
        async with self.lock:
            for command, values in commands:
                result, _ = await self.command_response(command, **values)
                if result is not ResponseResult.OK:
                    return result
        return ResponseResult.OK

    async def mower_park(self, mode=INDEFINITE, duration_hours=3):
        """Configure the parking target before triggering; never resume mowing first."""
        if mode not in PARKING_OPTIONS.values():
            raise ValueError("Unknown parking mode")
        duration = validate_parking_duration(duration_hours) if mode == TIMED else None
        generation = self.capabilities.generation
        if generation not in (3, 4):
            return ResponseResult.NOT_AVAILABLE
        async with self.lock:
            result, state = await self.command_response("GetState", warn_on_error=False)
            if result is not ResponseResult.OK:
                return result
            if state not in (
                MowerState.PAUSED, MowerState.RESTRICTED,
                MowerState.IN_OPERATION, MowerState.PENDING_START,
            ):
                return ResponseResult.NOT_ALLOWED
            result, current_mode = await self.command_response("GetMode", warn_on_error=False)
            if result is not ResponseResult.OK:
                return result
            if isinstance(current_mode, bool) or current_mode not in (ModeOfOperation.AUTO, ModeOfOperation.HOME):
                return ResponseResult.UNKNOWN_ERROR
            # Return Home must never weaken an existing indefinite hold. Start or
            # Resume schedule is the explicit way to leave HOME mode.
            permanent = mode == INDEFINITE or current_mode == ModeOfOperation.HOME
            if mode == NEXT_SCHEDULE and not permanent:
                result, count = await self.command_response("GetNumberOfTasks", warn_on_error=False)
                if result is not ResponseResult.OK:
                    return result
                if type(count) is not int or not 0 <= count <= 15:
                    return ResponseResult.NOT_AVAILABLE
                if count == 0:
                    permanent = True
                    _LOGGER.debug("No onboard tasks: parking until further notice instead of until next schedule")
            _LOGGER.debug("Dock policy: requested=%s effective_indefinite=%s", mode, permanent)
            commands = [("SetMode", {"mode": ModeOfOperation.HOME if permanent else ModeOfOperation.AUTO})]
            if not permanent:
                commands.append(("SetOverridePark", {"duration": int(duration * 3600)}) if mode == TIMED else ("SetOverrideParkUntilNextStart", {}))
            elif generation == 4:
                commands.append(("ClearOverride", {}))
            result = await self._action_sequence(commands)
            if result is not ResponseResult.OK:
                return result
            result, _ = await self.command_response("StartTrigger", warn_on_error=False)
            if result not in (ResponseResult.OK, ResponseResult.UNKNOWN_ERROR):
                return result
        return await self._confirm_dock(permanent)

    async def _confirm_dock(self, permanent):
        """Observe fresh parking state on this session without replay or reconnect."""
        expected_mode = ModeOfOperation.HOME if permanent else ModeOfOperation.AUTO
        try:
            async with asyncio.timeout(PARK_OBSERVATION_SECONDS):
                while self.is_connected():
                    readings = {}
                    # Serialize each sample, not the sleep between samples: a
                    # new Pause/Dock request must be able to take the lock.
                    async with self.lock:
                        for command in ("GetMode", "GetOverride", "GetState", "GetActivity"):
                            if permanent and command == "GetOverride":
                                continue
                            result, value = await self.command_response(command, warn_on_error=False)
                            if result is not ResponseResult.OK:
                                break
                            readings[command] = value
                    override = readings.get("GetOverride")
                    parked_override = (
                        isinstance(override, dict)
                        and not isinstance(override.get("action"), bool)
                        and override.get("action") == OverrideAction.FORCEDPARK
                    )
                    _LOGGER.debug(
                        "Dock read-back: mode=%s state=%s activity=%s park_override=%s permanent=%s",
                        readings.get("GetMode"), readings.get("GetState"),
                        readings.get("GetActivity"), parked_override, permanent,
                    )
                    if readings.get("GetState") in (
                        MowerState.OFF, MowerState.WAIT_FOR_SAFETYPIN, MowerState.STOPPED,
                        MowerState.ERROR, MowerState.FATAL_ERROR,
                    ):
                        return ResponseResult.NOT_ALLOWED
                    if (
                        not any(isinstance(readings.get(key), bool) for key in ("GetMode", "GetState", "GetActivity"))
                        and readings.get("GetMode") == expected_mode
                        and (permanent or parked_override)
                        and readings.get("GetState") in (MowerState.IN_OPERATION, MowerState.RESTRICTED)
                        and readings.get("GetActivity") in (
                            MowerActivity.GOING_HOME, MowerActivity.PARKED, MowerActivity.CHARGING,
                        )
                    ):
                        return ResponseResult.OK
                    await asyncio.sleep(PARK_POLL_SECONDS)
        except (BleakError, TimeoutError):
            # Ordinary polling handles transport recovery. Do not replay a trigger.
            _LOGGER.debug("Dock observation ended without confirmation")
        return ResponseResult.UNKNOWN_ERROR

    async def mower_park_permanently(self):
        generation = self.capabilities.generation
        if generation not in (3, 4):
            return ResponseResult.NOT_AVAILABLE
        commands = [("SetMode", {"mode": ModeOfOperation.HOME})]
        if generation == 4:
            commands.append(("ClearOverride", {}))
        async with self.lock:
            result = await self._action_sequence(commands)
            if result is not ResponseResult.OK:
                return result
            result, _ = await self.command_response("StartTrigger", warn_on_error=False)
            if result is ResponseResult.UNKNOWN_ERROR:
                # Like upstream's mowing trigger handling, allow firmware time to
                # settle. Never infer success from cached HOME or activity alone.
                await asyncio.sleep(2)
                readings = {}
                for command in ("GetMode", "GetState", "GetActivity"):
                    status, value = await self.command_response(command, warn_on_error=False)
                    if status is not ResponseResult.OK:
                        break
                    readings[command] = value
                if (
                    readings.get("GetMode") == ModeOfOperation.HOME
                    and readings.get("GetState") in (MowerState.IN_OPERATION, MowerState.RESTRICTED)
                    and readings.get("GetActivity") in (
                        MowerActivity.GOING_HOME, MowerActivity.PARKED, MowerActivity.CHARGING
                    )
                ):
                    _LOGGER.debug("Permanent park confirmed by fresh readings after StartTrigger UNKNOWN_ERROR")
                    return ResponseResult.OK
            if result is not ResponseResult.OK:
                _LOGGER.warning("Permanent park StartTrigger returned %s; success not confirmed", result.name)
            return result

    async def mower_resume(self):
        return await self._action_sequence([("StartTrigger", {})])

    async def mower_resume_schedule(self):
        return await self._action_sequence(
            [
                ("ClearOverride", {}),
                ("SetMode", {"mode": ModeOfOperation.AUTO}),
            ]
        )
