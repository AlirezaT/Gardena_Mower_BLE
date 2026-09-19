"""Recover an explicitly requested start without changing modes during setup."""

import logging

from automower_ble.protocol import MowerActivity, MowerState, ResponseResult
from bleak import BleakError

_LOGGER = logging.getLogger(__name__)


class ManualStartError(RuntimeError):
    """A manual start could not be confirmed."""


async def _read_start_state(mower):
    state = await mower.mower_state()
    activity = await mower.mower_activity()
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
    """Confirm ambiguous starts on the current session before reconnecting."""
    await ensure_connected()
    await _read_start_state(mower)
    result = ResponseResult.UNKNOWN_ERROR
    for attempt in range(2):
        try:
            result = await mower.mower_override(duration)
        except (BleakError, TimeoutError):
            result = ResponseResult.UNKNOWN_ERROR
        if result is ResponseResult.OK:
            return
        transient = result in (
            ResponseResult.UNKNOWN_ERROR,
            ResponseResult.DEVICE_BUSY,
        )
        if transient and mower.is_connected():
            try:
                state, activity = await _read_start_state(mower)
            except (BleakError, TimeoutError):
                # The response may have been lost after the command took effect.
                # Safety/unknown-state errors intentionally remain fatal here.
                pass
            else:
                if _start_accepted(state, activity):
                    _LOGGER.debug("Ambiguous start confirmed on existing session: state=%s, activity=%s", state.name, activity.name)
                    return
        if not transient:
            state, activity = await _read_start_state(mower)
            raise ManualStartError(
                f"Start mowing failed: {result.name}; state={state.name}, "
                f"activity={activity.name}. Check the mower display and BLE diagnostics"
            )
        if attempt:
            raise ManualStartError(
                "Start acceptance could not be confirmed after one retry. "
                "The mower may have started; check its state before requesting start again"
            )
        # Re-authenticate only for this explicit user/automation command. Read
        # back state before replaying so an accepted start is not sent twice.
        try:
            _LOGGER.debug("Start acceptance unconfirmed; reconnecting once before checking state again")
            await mower.disconnect()
            await ensure_connected()
        except Exception as err:
            # Includes HA UpdateFailed from ensure_connected. Do not catch
            # CancelledError or replay a command whose acceptance is unknown.
            raise ManualStartError(
                "Start acceptance is unknown: reconnecting to confirm it failed. "
                "The mower may already be mowing. Check its state before retrying. "
                f"Connection detail: {err}"
            ) from err
        try:
            state, activity = await _read_start_state(mower)
        except (BleakError, TimeoutError) as err:
            raise ManualStartError(
                "Start acceptance is unknown: state could not be read after reconnecting. "
                "The mower may already be mowing; start was not repeated"
            ) from err
        if _start_accepted(state, activity):
            return
