"""Timing must preserve results, cancellation, locking and payload privacy."""

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from automower_ble.mower import Mower as UpstreamMower
from automower_ble.protocol import ResponseResult
from test_connection import Mower


class CommandTimingTests(unittest.IsolatedAsyncioTestCase):
    async def test_result_and_arguments_preserved(self):
        mower = Mower(1, "00:00:00:00:00:00")
        expected = (ResponseResult.OK, {"private": "private-payload"})
        method = AsyncMock(return_value=expected)
        with patch.object(UpstreamMower, "command_response", method):
            with self.assertLogs("gardena_connection_tests.connection", "DEBUG") as logs:
                actual = await mower.command_response("GetMessage", warn_on_error=False, messageId=7)
        self.assertIs(actual, expected)
        method.assert_awaited_once_with("GetMessage", warn_on_error=False, messageId=7)
        text = "\n".join(logs.output)
        self.assertIn("outcome=OK", text)
        self.assertIn("lock_wait=", text)
        self.assertNotIn("private-payload", text)

    async def test_raw_command_preserves_value(self):
        mower = Mower(1, "00:00:00:00:00:00")
        with patch.object(UpstreamMower, "command", AsyncMock(return_value=0)):
            self.assertEqual(await mower.command("GetError"), 0)

    async def test_cancellation_and_exception_release_lock(self):
        mower = Mower(1, "00:00:00:00:00:00")
        for error in (asyncio.CancelledError, RuntimeError):
            with patch.object(UpstreamMower, "command", AsyncMock(side_effect=error("private-detail"))):
                with self.assertLogs("gardena_connection_tests.connection", "DEBUG") as logs:
                    with self.assertRaises(error):
                        await mower.command("GetError")
            self.assertFalse(mower.lock.locked())
            self.assertNotIn("private-detail", "\n".join(logs.output))

    async def test_cancelled_lock_wait_sends_nothing(self):
        mower = Mower(1, "00:00:00:00:00:00")
        method = AsyncMock()
        with patch.object(UpstreamMower, "command", method):
            async with mower.lock:
                task = asyncio.create_task(mower.command("GetError"))
                await asyncio.sleep(0)
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task
            method.assert_not_awaited()
