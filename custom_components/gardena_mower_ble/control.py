"""Recover an explicitly requested start without changing modes during setup."""

import asyncio
import logging

from automower_ble.protocol import MowerActivity, MowerState, ResponseResult
from bleak import BleakError

_LOGGER = logging.getLogger(__name__)
START_OBSERVATION_SECONDS = 15
START_POLL_SECONDS = 2


class ManualStartError(RuntimeError):
    """A manual start could not be confirmed."""


async def _read_start_state(mower):
    state = await mower.mower_state()
    activity = await mower.mower_activity()
    _LOGGER.debug("Fresh start state: state=%s, activity=%s", state, activity)
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


async def start_manual_mowing(mower, duration, ensure_connected):
    """Send once; observe an ambiguous start without disconnecting or replaying."""
    await ensure_connected()
    await _read_start_state(mower)
    try:
        result = await mower.mower_override(duration)
    except (BleakError, TimeoutError):
        result = ResponseResult.UNKNOWN_ERROR
    _LOGGER.debug("Manual start attempt 1: result=%s", result.name)
    if result is ResponseResult.OK:
        return
    if result not in (ResponseResult.UNKNOWN_ERROR, ResponseResult.DEVICE_BUSY):
        state, activity = await _read_start_state(mower)
        raise ManualStartError(
            f"Start mowing failed: {result.name}; state={state.name}, "
            f"activity={activity.name}. Check the mower display and BLE diagnostics"
        )

    # City 500/41.6 can enter IN_OPERATION/CHARGING during its countdown.
    # That is not proof of mowing, nor a reason to tear down a live session.
    # The app's duration-start path does not reconnect/replay on this response.
    _LOGGER.debug("Observing ambiguous start for up to %ss; no reconnect or replay", START_OBSERVATION_SECONDS)
    last_state = "unavailable"
    try:
        async with asyncio.timeout(START_OBSERVATION_SECONDS):
            while mower.is_connected():
                state, activity = await _read_start_state(mower)
                last_state = f"{state.name}/{activity.name}"
                if _start_accepted(state, activity):
                    _LOGGER.debug("Ambiguous start confirmed on existing session: %s", last_state)
                    return
                await asyncio.sleep(START_POLL_SECONDS)
    except (BleakError, TimeoutError):
        # Let ordinary polling handle a lost link. Never replay a movement
        # command whose outcome is unknown. Cancellation/safety errors propagate.
        _LOGGER.debug("Start observation ended or connection was lost; last state=%s", last_state)
    raise ManualStartError(
        "Start acceptance is unknown; start was not repeated and no recovery "
        "reconnect was requested. The mower may already be mowing or waiting "
        f"to leave the dock. Last state: {last_state}. Check the mower before retrying"
    )
