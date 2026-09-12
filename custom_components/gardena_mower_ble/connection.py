"""Serialize the connection lifecycle of the original AutoMower-BLE library."""

import asyncio
import logging
from contextlib import suppress

from automower_ble.mower import Mower as UpstreamMower
from automower_ble.protocol import ResponseResult
from bleak import BleakError

from .settings_protocol import corrected_protocol
from .model_capabilities import ModelCapabilities, identify_model
from .schedule import ScheduleMixin
from .actions import ActionMixin
from .timestamps import local_timestamp
from .events import EventMixin

_LOGGER = logging.getLogger(__name__)


class _TaskLock:
    """An asyncio lock reentrant only for its owning task."""

    def __init__(self):
        self._lock = asyncio.Lock()
        self._owner = None
        self._depth = 0

    def locked(self):
        return self._lock.locked()

    async def __aenter__(self):
        task = asyncio.current_task()
        if self._owner is not task:
            await self._lock.acquire()
            self._owner = task
        self._depth += 1
        return self

    async def __aexit__(self, *_exc):
        self._depth -= 1
        if not self._depth:
            self._owner = None
            self._lock.release()


class Mower(EventMixin, ActionMixin, ScheduleMixin, UpstreamMower):
    """Use the upstream protocol with an atomic, fully initialized session."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Covers upstream schedule operations that hold the command lock too.
        self.lock = _TaskLock()
        self._session_ready = False
        self._connecting_task = None
        self._settings_protocol_corrected = False
        self.capabilities = ModelCapabilities()
        self._event_frame_buffer = bytearray()
        self._pairing_pending = False
        self._pairing_result = None

    async def initialize_capabilities(self, brand=None):
        """Identify this session with reads only, before creating HA entities."""
        identity = await self.command("GetModel")
        firmware = await self.command("GetSwVersionStringAppl")
        self.capabilities = identify_model(identity, firmware, brand)
        if self.capabilities.platform == "unknown":
            _LOGGER.warning("Mower model identity is unknown; model-dependent settings are disabled")
        elif self.capabilities.platform == "P0" and self.capabilities.firmware_pair is None:
            _LOGGER.warning("P0 firmware version is unrecognized; firmware-dependent settings are disabled")
        self.protocol = corrected_protocol(await self.get_protocol(), self.capabilities)

    async def get_protocol(self):
        """Overlay only app-verified setting definitions for this mower."""
        protocol = await super().get_protocol()
        if not self._settings_protocol_corrected:
            self.protocol = corrected_protocol(protocol)
            self._settings_protocol_corrected = True
        return self.protocol

    def is_connected(self):
        return self._session_ready and super().is_connected()

    async def mower_next_start_time(self, timezone=None):
        value = await self.command("GetNextStartTime")
        return local_timestamp(value, timezone)

    async def connect(self, device):
        async with self.lock:
            if self.is_connected():
                return await super().connect(device)
            await self.disconnect()
            self._connecting_task = asyncio.current_task()
            try:
                result = await super().connect(device)
                self._session_ready = (
                    result is ResponseResult.OK and super().is_connected()
                )
                if result is ResponseResult.OK and not self._session_ready:
                    return ResponseResult.UNKNOWN_ERROR
                return result
            finally:
                self._connecting_task = None
                if not self._session_ready:
                    await self.disconnect()

    async def _request_response_locked(self, request_data):
        async with self.lock:
            if not self.is_connected() and (
                self._connecting_task is not asyncio.current_task()
            ):
                raise BleakError("Mower connection is not ready; reconnect required")
            # The upstream request path flushes its queue. Match that for any
            # coalesced bytes retained by the event-aware frame reader too.
            self._event_frame_buffer.clear()
            result = await super()._request_response_locked(request_data)
            # Upstream consumes CancelledError; preserve HA timeouts/shutdown.
            if asyncio.current_task().cancelling():
                raise asyncio.CancelledError
            return result

    async def _write_data(self, data):
        client, characteristic = self.client, self.write_char
        if client is None or not client.is_connected or characteristic is None:
            raise BleakError("Mower disconnected before the BLE write")
        chunk_size = self.MTU_SIZE - 3
        for offset in range(0, len(data), chunk_size):
            await client.write_gatt_char(
                characteristic, data[offset : offset + chunk_size], response=False
            )

    async def disconnect(self):
        async with self.lock:
            self._session_ready = False
            self._event_frame_buffer.clear()
            self.keep_alive_event.set()
            task = self.task
            if task is not asyncio.current_task():
                self.task = None
                if task is not None:
                    task.cancel()
                    with suppress(asyncio.CancelledError):
                        await task
            client, self.client = self.client, None
            self.write_char = self.read_char = None
            self._notify_started = False
            self.queue.put_nowait(None)
            if client is not None:
                try:
                    async with asyncio.timeout(10):
                        await client.disconnect()
                except (BleakError, TimeoutError) as err:
                    _LOGGER.debug("BLE disconnect cleanup failed: %s", err)
