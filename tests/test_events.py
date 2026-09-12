"""Pairing completion requires a valid event, not just an accepted command."""

import asyncio
import unittest
from unittest.mock import AsyncMock

from automower_ble.helpers import crc
from automower_ble.protocol import Command, ResponseResult
from test_connection import Mower
from gardena_connection_tests.events import pairing_event


def packet(minor=2, kind=2, channel=1):
    data = Command(channel, {"major": 4692, "minor": minor}).generate_request()
    data[10] = kind
    data[-2] = crc(data, 1, len(data) - 3)
    return data


class EventTests(unittest.IsolatedAsyncioTestCase):
    def mower(self):
        mower = Mower(1, "00:00:00:00:00:00", 1234)
        mower.command_response = AsyncMock(return_value=(ResponseResult.OK, None))
        return mower

    def test_only_valid_current_channel_pairing_events_are_accepted(self):
        self.assertIs(pairing_event(packet(), 1), True)
        self.assertIs(pairing_event(packet(1), 1), False)
        for frame in (packet(3), packet(kind=1), packet(channel=2), packet()[:-1]):
            self.assertIsNone(pairing_event(frame, 1))
        broken = packet()
        broken[-2] ^= 1
        self.assertIsNone(pairing_event(broken, 1))

    async def test_fragmented_event_before_coalesced_reply(self):
        mower = self.mower()
        mower._pairing_pending = True
        event, reply = packet(), packet(kind=1)
        for chunk in (event[:1], event[1:5], event[5:] + reply):
            mower.queue.put_nowait(chunk)
        self.assertEqual(await mower._read_data(), reply)
        self.assertIs(mower._pairing_result, True)

    async def test_reply_then_event_retains_trailing_frame(self):
        mower = self.mower()
        mower._pairing_pending = True
        mower.queue.put_nowait(packet(kind=1) + packet())
        self.assertEqual(await mower._read_data(), packet(kind=1))
        self.assertEqual(await mower._next_frame(), packet())

    async def test_completion_failure_timeout_and_disconnect(self):
        for frame, message in (
            (packet(), None),
            (packet(1), "pairing failed"),
            (None, "Disconnected"),
            (b"", "completion was not confirmed"),
        ):
            mower = self.mower()

            async def command(*args, **kwargs):
                if frame != b"":
                    mower.queue.put_nowait(frame)
                return ResponseResult.OK, None

            mower.command_response.side_effect = command
            if message:
                with self.assertRaisesRegex(RuntimeError, message):
                    await mower.generate_loop_signal(timeout=0.01)
            else:
                await mower.generate_loop_signal(timeout=0.01)
            self.assertFalse(mower._pairing_pending)
            mower.command_response.assert_awaited_once_with("GenerateLoopSignal")

    async def test_rejected_command_does_not_wait_for_completion(self):
        mower = self.mower()
        mower.command_response.return_value = ResponseResult.INVALID_ID, None
        with self.assertRaisesRegex(RuntimeError, "rejected: INVALID_ID"):
            await mower.generate_loop_signal()
        self.assertFalse(mower._pairing_pending)

    async def test_cancellation_cleans_pending_listener(self):
        mower = self.mower()
        task = asyncio.create_task(mower.generate_loop_signal())
        await asyncio.sleep(0)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertFalse(mower._pairing_pending)

    async def test_wait_keeps_session_alive_without_repeating_pairing(self):
        mower = self.mower()

        async def command(name, **kwargs):
            if name == "KeepAlive":
                mower._record_pairing_event(packet())
            return ResponseResult.OK, None

        mower.command_response.side_effect = command
        await mower.generate_loop_signal(timeout=1, heartbeat_interval=0.001)
        self.assertEqual(
            [call.args[0] for call in mower.command_response.await_args_list],
            ["GenerateLoopSignal", "KeepAlive"],
        )
