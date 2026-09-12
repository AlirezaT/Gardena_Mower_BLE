"""Keep asynchronous pairing events separate from command responses."""

import asyncio

from automower_ble.helpers import crc
from automower_ble.protocol import ResponseResult


def pairing_event(frame, channel_id):
    """Validate the linked HCP envelope before recognizing app pairing events."""
    if (
        len(frame) < 20
        or frame[:2] != b"\x02\xfd"
        or int.from_bytes(frame[2:4], "little") + 4 != len(frame)
        or frame[-1] != 3
        or frame[8] != 1
        or frame[9] != crc(frame, 1, 8)
        or frame[-2] != crc(frame, 1, len(frame) - 3)
        or int.from_bytes(frame[4:8], "little") != channel_id
        or frame[10] != 2
        or frame[11] != 0xAF
        or int.from_bytes(frame[12:14], "little") != 4692
    ):
        return None
    event = int.from_bytes(frame[14:16], "little")
    return {1: False, 2: True}.get(event)


class EventMixin:
    async def _next_frame(self):
        """Reassemble fragments and retain coalesced trailing frames."""
        buffer = self._event_frame_buffer
        while True:
            if buffer and buffer[0] != 2:
                start = buffer.find(b"\x02")
                del buffer[: start if start >= 0 else len(buffer)]
            if len(buffer) >= 4:
                length = int.from_bytes(buffer[2:4], "little") + 4
                if length < 6 or length > 4096:
                    buffer.clear()
                    raise ValueError("Invalid mower frame length")
                if len(buffer) >= length:
                    frame = bytearray(buffer[:length])
                    del buffer[:length]
                    return frame
            chunk = await self.queue.get()
            if chunk is None:
                return None
            buffer.extend(chunk)

    def _record_pairing_event(self, frame):
        value = pairing_event(frame, self.channel_id)
        if value is not None and self._pairing_pending:
            self._pairing_result = value

    async def _read_data(self):
        async with asyncio.timeout(10):
            while True:
                frame = await self._next_frame()
                if frame is None:
                    return None
                if len(frame) > 10 and frame[1] == 0xFD and frame[10] == 2:
                    self._record_pairing_event(frame)
                    continue
                return frame

    async def generate_loop_signal(self, timeout=90, heartbeat_interval=5):
        """Acceptance is not completion; wait for the app's explicit result event."""
        async with self.lock:
            self._pairing_pending = True
            self._pairing_result = None
            # Discard previous completed frames before issuing this new request.
            self._event_frame_buffer.clear()
            try:
                result, _ = await self.command_response("GenerateLoopSignal")
                if result is not ResponseResult.OK:
                    raise RuntimeError(f"Loop generation rejected: {result.name}")
                async with asyncio.timeout(timeout):
                    while self._pairing_result is None:
                        try:
                            async with asyncio.timeout(heartbeat_interval):
                                frame = await self._next_frame()
                        except TimeoutError:
                            if self._event_frame_buffer:
                                raise RuntimeError(
                                    "Incomplete frame while awaiting loop pairing; completion is unknown"
                                )
                            # The normal keep-alive task cannot acquire our action
                            # lock. Maintain this session while awaiting the event.
                            result, _ = await self.command_response(
                                "KeepAlive", warn_on_error=False
                            )
                            if result is not ResponseResult.OK:
                                raise RuntimeError(
                                    "Keep-alive failed before loop pairing completed"
                                )
                            continue
                        if frame is None:
                            raise RuntimeError(
                                "Disconnected before loop pairing completed"
                            )
                        self._record_pairing_event(frame)
                if not self._pairing_result:
                    raise RuntimeError("Mower reported loop pairing failed")
            except TimeoutError as err:
                raise RuntimeError(
                    "Loop command accepted but completion was not confirmed; check the app before retrying"
                ) from err
            finally:
                self._pairing_pending = False
