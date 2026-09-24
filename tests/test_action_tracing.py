"""Provenance distinguishes a wire error, absent response and transport failure."""

import asyncio
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from automower_ble.protocol import BLEClient, ResponseResult as R

from test_connection import Mower
from gardena_connection_tests.tracing import REQUEST_TRACE, action_id, trace_action


class TracingTests(unittest.IsolatedAsyncioTestCase):
    async def test_action_ids_are_distinct_and_not_inherited_by_heartbeat(self):
        mower = Mower(1, "00:00:00:00:00:00", 1234)
        other = Mower(2, "00:00:00:00:00:01", 4567)

        async def child():
            return action_id(mower)

        with trace_action(mower, "Start"):
            self.assertEqual(action_id(mower), "1:Start")
            self.assertEqual(action_id(other), "none")
            self.assertEqual(await asyncio.create_task(child()), "none")
            with trace_action(mower, "nested"):
                self.assertEqual(action_id(mower), "2:nested")
            self.assertEqual(action_id(mower), "1:Start")
        with trace_action(mower, "Dock"):
            self.assertEqual(action_id(mower), "3:Dock")
        self.assertEqual(action_id(mower), "none")

    async def test_wire_unknown_and_missing_response_have_different_provenance(self):
        for frame, source in ((bytes(16) + bytes([R.UNKNOWN_ERROR]), "frame_received"), (None, "no_response")):
            for method_name in ("command_response", "command_response_locked"):
                mower = Mower(1, "00:00:00:00:00:00", 1234)
                mower.is_connected = Mock(return_value=True)
                mower._write_data = AsyncMock()
                mower._read_data = AsyncMock(return_value=frame)
                mower.disconnect = AsyncMock()
                with self.assertLogs("gardena_connection_tests.connection", "DEBUG") as logs:
                    result, _ = await getattr(mower, method_name)("StartTrigger", warn_on_error=False)
                self.assertIs(result, R.UNKNOWN_ERROR)
                text = "\n".join(logs.output)
                self.assertIn("response_source=" + source, text)
                self.assertIn("wire_result=" + (str(int(R.UNKNOWN_ERROR)) if frame else "None"), text)
                self.assertIsNone(REQUEST_TRACE.get())

    async def test_timeout_names_failing_command_without_private_exception(self):
        mower = Mower(1, "00:00:00:00:00:00", 1234)
        mower.is_connected = Mock(return_value=True)
        mower._write_data = AsyncMock()
        mower._read_data = AsyncMock(side_effect=TimeoutError("PRIVATE PAYLOAD"))
        with trace_action(mower, "Start"), self.assertLogs("gardena_connection_tests.connection", "DEBUG") as logs:
            with self.assertRaises(TimeoutError):
                await mower.command_response_locked("StartTrigger")
        text = "\n".join(logs.output)
        self.assertIn("Mower command StartTrigger", text)
        self.assertIn("response_source=TimeoutError", text)
        self.assertIn("action=1:Start session=0", text)
        self.assertNotIn("PRIVATE", text)
        self.assertIsNone(REQUEST_TRACE.get())
        self.assertFalse(mower.lock.locked())

    async def test_session_changes_only_for_new_connection_attempt(self):
        mower = Mower(1, "00:00:00:00:00:00", 1234)
        client = SimpleNamespace(is_connected=True, disconnect=AsyncMock())

        async def connect(instance, device):
            instance.client = client
            instance.write_char = object()
            return R.OK

        with patch.object(BLEClient, "connect", connect), patch.object(mower, "_ensure_keep_alive"):
            await mower.connect(object())
            self.assertEqual(mower.session_id, 1)
            await mower.connect(object())
            self.assertEqual(mower.session_id, 1)
            await mower.disconnect()
            await mower.connect(object())
            self.assertEqual(mower.session_id, 2)
            self.assertEqual(mower.connection_diagnostics["session"], 2)
        await mower.disconnect()
