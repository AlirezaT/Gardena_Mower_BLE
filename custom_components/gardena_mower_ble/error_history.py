"""Read and present the robot's message log, not HA recorder history."""

import asyncio

from automower_ble.protocol import ResponseResult

from .presentation import describe_error
from .timestamps import message_time_attributes

APP_HISTORY_LIMIT = 50
SEVERITIES = ("unknown", "fatal", "error", "warning", "info", "debug", "software")


def history_signature(count, latest):
    """Detect count/head changes even when a full device log rotates."""
    if type(count) is not int or not 0 <= count < 0xFFFFFFFF:
        return None
    if count == 0:
        return (0,)
    if not isinstance(latest, dict):
        return None
    fields = tuple(latest.get(key) for key in ("time", "code", "severity"))
    if any(type(value) is not int for value in fields):
        return None
    return (count, *fields)


def history_attributes(data):
    """Expose history separately from the current error sensor state."""
    snapshot = data.get("error_history_snapshot")
    entries = snapshot["entries"] if snapshot is not None else []
    return {
        "error_history": entries,
        "error_history_status": data.get("error_history_status", "not_loaded"),
        "error_history_updated_at": data.get("error_history_updated_at"),
        "error_history_source": "robot",
        "error_history_total": snapshot["total_messages"]
        if snapshot is not None
        else None,
        "error_history_limit": APP_HISTORY_LIMIT,
        "error_history_order": "device_index",
        "latest_stored_message": entries[0] if entries else None,
    }


async def read_error_history(mower, *, max_entries=10, offset=0, timezone=None):
    """Read a bounded page in device index order; never hide incomplete reads.

    App 9.2.0 caps its view at 50 messages and requests chunks of ten.
    Count/first-entry checks detect common rotations, not atomic snapshots.
    """
    if type(max_entries) is not int or not 1 <= max_entries <= APP_HISTORY_LIMIT:
        raise ValueError("max_entries must be an integer from 1 to 50")
    if type(offset) is not int or not 0 <= offset < APP_HISTORY_LIMIT:
        raise ValueError("offset must be an integer from 0 to 49")

    async def read(command, **kwargs):
        result, value = await mower.command_response(
            command, warn_on_error=False, **kwargs
        )
        if result is not ResponseResult.OK:
            raise RuntimeError(
                f"Cannot read mower history: {command} returned {result.name}"
            )
        return value

    def validate_count(value):
        if type(value) is not int or not 0 <= value < 0xFFFFFFFF:
            raise ValueError("Invalid mower message count")
        return value

    def validate_message(value):
        if not isinstance(value, dict):
            raise ValueError("Invalid mower history entry")
        for key, maximum in (
            ("time", 0xFFFFFFFF),
            ("code", 0xFFFFFFFF),
            ("severity", 255),
        ):
            if type(value.get(key)) is not int or not 0 <= value[key] <= maximum:
                raise ValueError(f"Invalid mower history {key}")
        return {key: value[key] for key in ("time", "code", "severity")}

    async with asyncio.timeout(60), mower.lock:
        total = validate_count(await read("GetNumberOfMessages"))
        available = min(total, APP_HISTORY_LIMIT)
        end = min(offset + max_entries, available)
        raw_entries = []
        for index in range(offset, end):
            raw_entries.append(
                validate_message(await read("GetMessage", messageId=index))
            )
        if validate_count(await read("GetNumberOfMessages")) != total:
            raise RuntimeError("Mower history changed during reading; retry")
        if (
            raw_entries
            and validate_message(await read("GetMessage", messageId=offset))
            != raw_entries[0]
        ):
            raise RuntimeError("Mower history changed during reading; retry")

    capabilities = mower.capabilities
    entries = []
    for index, message in enumerate(raw_entries, start=offset):
        severity = message["severity"]
        entries.append(
            {
                "index": index,
                **message,
                "description": describe_error(
                    message["code"], capabilities.platform, capabilities
                ),
                "severity_name": SEVERITIES[severity]
                if severity < len(SEVERITIES)
                else "unknown",
                **message_time_attributes(message["time"], timezone),
            }
        )
    return {
        "source": "robot",
        "total_messages": total,
        "available_messages": available,
        "history_limit": APP_HISTORY_LIMIT,
        "offset": offset,
        "returned": len(entries),
        "next_offset": end if end < available else None,
        "order": "device_index",
        "entries": entries,
    }
