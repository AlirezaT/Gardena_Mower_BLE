"""Recover an explicitly requested start without changing modes during setup."""

from automower_ble.protocol import MowerActivity, MowerState, ResponseResult
from bleak import BleakError


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
    """Verify state and retry once with a fresh session after a transient failure."""
    await ensure_connected()
    await _read_start_state(mower)
    result = ResponseResult.UNKNOWN_ERROR
    for attempt in range(2):
        try:
            result = await mower.mower_override(duration)
        except (BleakError, TimeoutError):
            if attempt:
                raise ManualStartError(
                    "BLE connection failed during start; acceptance is unknown. "
                    "Check mower state before retrying"
                ) from None
            result = ResponseResult.UNKNOWN_ERROR
        if result is ResponseResult.OK:
            return
        if attempt or result not in (
            ResponseResult.UNKNOWN_ERROR,
            ResponseResult.DEVICE_BUSY,
        ):
            state, activity = await _read_start_state(mower)
            if result in (
                ResponseResult.UNKNOWN_ERROR,
                ResponseResult.DEVICE_BUSY,
            ) and _start_accepted(state, activity):
                return
            raise ManualStartError(
                f"Start mowing failed: {result.name}; state={state.name}, "
                f"activity={activity.name}. Check the mower display and BLE diagnostics"
            )
        # Re-authenticate only for this explicit user/automation command. Read
        # back state before replaying so an accepted start is not sent twice.
        await mower.disconnect()
        await ensure_connected()
        state, activity = await _read_start_state(mower)
        if _start_accepted(state, activity):
            return
