"""Recover an explicitly requested start without changing modes during setup."""

import asyncio
import logging

from automower_ble.protocol import MowerActivity, MowerState, ResponseResult
from bleak import BleakError

_LOGGER = logging.getLogger(__name__)
START_OBSERVATION_SECONDS = 15
START_POLL_SECONDS = 2
P0_START_POLL_SECONDS = 5


class ManualStartError(RuntimeError):
    """A manual start could not be confirmed."""


async def _read_start_state(mower):
    state = await mower.mower_state()
    activity = await mower.mower_activity()
    _LOGGER.debug(
        "Fresh start state: state=%s, activity=%s action=%s session=%s",
        state, activity, getattr(mower, "action_id", "none"), getattr(mower, "session_id", None),
    )
    if state is None or activity is None:
        raise ManualStartError("Cannot confirm mower state; start was not repeated")
    if state in (
        MowerState.OFF,
        MowerState.WAIT_FOR_SAFETYPIN,
        MowerState.STOPPED,
        MowerState.FATAL_ERROR,
        MowerState.ERROR,
    ):
        raise ManualStartError(
            f"Mower reports {state.name}; check the mower display, physical STOP "
            "button and safety/PIN prompt before requesting start again"
        )
    if state == MowerState.PENDING_START and activity == MowerActivity.NONE:
        raise ManualStartError(
            "Mower is pending start without activity; check the physical "
            "STOP button and safety/PIN prompt. Start was not repeated"
        )
    return state, activity


def _start_accepted(state, activity):
    return state == MowerState.PENDING_START or (
        state == MowerState.IN_OPERATION
        and activity in (MowerActivity.GOING_OUT, MowerActivity.MOWING)
    )


def _diagnostic_value(command, value):
    """Only log numeric protocol fields, never arbitrary response dictionaries."""
    if command == "GetOverride" and isinstance(value, dict):
        return {
            key: int(value[key])
            for key in ("action", "duration")
            if isinstance(value.get(key), int) and not isinstance(value[key], bool)
        }
    if isinstance(value, int) and not isinstance(value, bool):
        return int(value)
    return "unavailable"


async def _p0_start_snapshot(mower):
    """Read context before movement; missing optional values are not safety proof."""
    snapshot = {}
    async with mower.lock:
        for command in (
            "GetMode", "GetOverride", "GetRestrictionReason", "GetRemainingChargingTime",
        ):
            result, value = await mower.command_response(command, warn_on_error=False)
            snapshot[command] = {
                "result": result.name,
                "value": _diagnostic_value(command, value) if result is ResponseResult.OK else "unavailable",
            }
        # Safety state is read last, after optional diagnostics, and remains decisive.
        state, activity = await _read_start_state(mower)
    _LOGGER.debug(
        "P0 pre-start snapshot action=%s session=%s state=%s activity=%s fields=%s",
        mower.action_id, mower.session_id, state.name, activity.name, snapshot,
    )


async def _p0_start_state(mower, session):
    """Keep each status pair together, releasing the wire between samples."""
    async with mower.lock:
        if not mower.is_connected() or mower.session_id != session:
            raise BleakError("Start observation session changed; no replay")
        return await _read_start_state(mower)


async def start_manual_mowing(mower, duration, ensure_connected):
    """Send once; observe an ambiguous start without disconnecting or replaying."""
    await ensure_connected()
    p0 = getattr(getattr(mower, "capabilities", None), "platform", None) == "P0"
    if p0:
        await _p0_start_snapshot(mower)
    else:
        await _read_start_state(mower)
    session = getattr(mower, "session_id", None)
    try:
        if p0:
            result = await mower.mower_override(duration, confirm_trigger=False)
        else:
            result = await mower.mower_override(duration)
    except (BleakError, TimeoutError):
        result = ResponseResult.UNKNOWN_ERROR
    _LOGGER.debug(
        "Manual start attempt 1: result=%s action=%s session=%s",
        result.name, getattr(mower, "action_id", "none"), session,
    )
    if result is ResponseResult.OK and not p0:
        return
    if result not in (ResponseResult.OK, ResponseResult.UNKNOWN_ERROR, ResponseResult.DEVICE_BUSY):
        state, activity = await _read_start_state(mower)
        raise ManualStartError(
            f"Start mowing failed: {result.name}; state={state.name}, "
            f"activity={activity.name}. Check the mower display and BLE diagnostics"
        )

    # City 500/41.6 can enter IN_OPERATION/CHARGING during its countdown.
    # That is not proof of mowing, nor a reason to tear down a live session.
    # The app's duration-start path does not reconnect/replay on this response.
    interval = P0_START_POLL_SECONDS if p0 else START_POLL_SECONDS
    _LOGGER.debug(
        "Observing start for up to %ss interval=%ss initial_delay=%s action=%s session=%s; no reconnect or replay",
        START_OBSERVATION_SECONDS, interval, p0, getattr(mower, "action_id", "none"), session,
    )
    last_state = "unavailable"
    try:
        async with asyncio.timeout(START_OBSERVATION_SECONDS):
            while mower.is_connected():
                if p0:
                    # No upstream two-second probe followed by a duplicate sample.
                    await asyncio.sleep(interval)
                    if not mower.is_connected() or mower.session_id != session:
                        _LOGGER.debug("P0 start observation lost its original session action=%s session=%s", mower.action_id, session)
                        break
                    state, activity = await _p0_start_state(mower, session)
                else:
                    state, activity = await _read_start_state(mower)
                last_state = f"{state.name}/{activity.name}"
                accepted = (
                    state == MowerState.IN_OPERATION
                    and activity in (MowerActivity.GOING_OUT, MowerActivity.MOWING)
                ) if p0 else _start_accepted(state, activity)
                if accepted:
                    _LOGGER.debug(
                        "Start confirmed on existing session: %s action=%s session=%s",
                        last_state, getattr(mower, "action_id", "none"), session,
                    )
                    return (state, activity) if p0 else None
                if not p0:
                    await asyncio.sleep(interval)
    except (BleakError, TimeoutError):
        # Let ordinary polling handle a lost link. Never replay a movement
        # command whose outcome is unknown. Cancellation/safety errors propagate.
        _LOGGER.debug("Start observation ended or connection was lost; last state=%s", last_state)
    raise ManualStartError(
        "Start acceptance is unknown; start was not repeated and no recovery "
        "reconnect was requested. The mower may already be mowing or waiting "
        f"to leave the dock. Last state: {last_state}. Check the mower before retrying"
    )
