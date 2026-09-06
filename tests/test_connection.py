"""Exercise connection races against the actual pinned upstream library."""

import asyncio
import importlib.util
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from automower_ble.protocol import BLEClient, ResponseResult
from bleak import BleakError

_PATH = Path(__file__).parents[1] / "custom_components/gardena_mower_ble/connection.py"
_SPEC = importlib.util.spec_from_file_location("gardena_connection", _PATH)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
Mower = _MODULE.Mower


class ConnectionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mower = Mower(1, "00:00:00:00:00:00", 1234)
        self.client = SimpleNamespace(
            is_connected=True,
            disconnect=AsyncMock(),
            write_gatt_char=AsyncMock(),
        )

    async def asyncTearDown(self):
        await self.mower.disconnect()

    def ready(self):
        self.mower.client = self.client
        self.mower.write_char = object()
        self.mower._session_ready = True

    async def test_command_waits_for_full_handshake(self):
        started, finish = asyncio.Event(), asyncio.Event()

        async def connect(mower, device):
            mower.client = self.client
            started.set()
            await finish.wait()
            mower.write_char = object()
            await mower._request_response(b"handshake")
            return ResponseResult.OK

        with (
            patch.object(BLEClient, "connect", connect),
            patch.object(self.mower, "_read_data", AsyncMock(return_value=b"reply")),
            patch.object(self.mower, "_ensure_keep_alive"),
        ):
            connection = asyncio.create_task(self.mower.connect(object()))
            await started.wait()
            self.assertFalse(self.mower.is_connected())
            request = asyncio.create_task(self.mower._request_response(b"command"))
            await asyncio.sleep(0)
            self.assertFalse(request.done())
            self.client.write_gatt_char.assert_not_called()
            finish.set()
            self.assertIs(await connection, ResponseResult.OK)
            self.assertEqual(await request, b"reply")
            writes = [
                call.args[1] for call in self.client.write_gatt_char.call_args_list
            ]
            self.assertEqual(writes, [b"handshake", b"command"])

    async def test_concurrent_connects_initialize_once(self):
        async def connect(mower, device):
            await asyncio.sleep(0)
            self.ready()
            return ResponseResult.OK

        calls = []

        async def counted(mower, device):
            calls.append(device)
            return await connect(mower, device)

        with (
            patch.object(BLEClient, "connect", counted),
            patch.object(self.mower, "_ensure_keep_alive"),
        ):
            results = await asyncio.gather(
                self.mower.connect(object()), self.mower.connect(object())
            )
        self.assertEqual(results, [ResponseResult.OK, ResponseResult.OK])
        self.assertEqual(len(calls), 1)

    async def test_failed_connect_cleans_partial_client(self):
        async def connect(mower, device):
            mower.client = self.client
            raise BleakError("link lost during setup")

        with patch.object(BLEClient, "connect", connect):
            with self.assertRaises(BleakError):
                await self.mower.connect(object())
        self.client.disconnect.assert_awaited_once()
        self.assertIsNone(self.mower.client)
        self.assertFalse(self.mower.is_connected())

    async def test_reconnect_cancels_old_keep_alive(self):
        self.ready()
        self.client.is_connected = False
        old_task = asyncio.create_task(asyncio.sleep(100))
        self.mower.task = old_task

        async def connect(mower, device):
            self.assertTrue(old_task.cancelled())
            self.client.is_connected = True
            self.ready()
            return ResponseResult.OK

        with (
            patch.object(BLEClient, "connect", connect),
            patch.object(self.mower, "_ensure_keep_alive"),
        ):
            await self.mower.connect(object())
        self.assertTrue(old_task.cancelled())

    async def test_authentication_failure_is_preserved_and_cleaned_up(self):
        async def connect(mower, device):
            mower.client = self.client
            return ResponseResult.INVALID_PIN

        with patch.object(BLEClient, "connect", connect):
            result = await self.mower.connect(object())
        self.assertIs(result, ResponseResult.INVALID_PIN)
        self.assertIsNone(self.mower.client)
        self.assertFalse(self.mower.is_connected())

    async def test_self_disconnecting_keep_alive_is_stopped_before_reconnect(self):
        self.ready()
        disconnected = asyncio.Event()

        async def keep_alive():
            await self.mower.disconnect()
            disconnected.set()
            await asyncio.sleep(100)

        old_task = asyncio.create_task(keep_alive())
        self.mower.task = old_task
        await disconnected.wait()

        async def connect(mower, device):
            self.assertTrue(old_task.cancelled())
            self.ready()
            return ResponseResult.OK

        with patch.object(BLEClient, "connect", connect), patch.object(
            self.mower, "_ensure_keep_alive"
        ):
            await self.mower.connect(object())
        self.assertTrue(old_task.cancelled())

    async def test_requests_after_disconnect_raise_transport_error(self):
        self.ready()
        await self.mower.disconnect()
        with self.assertRaises(BleakError):
            await self.mower._request_response(b"command")
        self.client.write_gatt_char.assert_not_called()

    async def test_missing_characteristic_never_reaches_bleak(self):
        self.ready()
        self.mower.write_char = None
        with self.assertRaises(BleakError):
            await self.mower._request_response(b"command")
        self.client.write_gatt_char.assert_not_called()
        self.assertIsNone(self.mower.client)

    async def test_disconnect_is_idempotent_even_if_transport_fails(self):
        self.ready()
        self.client.disconnect.side_effect = BleakError("proxy offline")
        await self.mower.disconnect()
        await self.mower.disconnect()
        self.client.disconnect.assert_awaited_once()
        self.assertIsNone(self.mower.client)
        self.assertFalse(self.mower.is_connected())

    async def test_request_timeout_is_not_swallowed(self):
        self.ready()
        started = asyncio.Event()

        async def read():
            started.set()
            await asyncio.Event().wait()

        with patch.object(self.mower, "_read_data", read):
            task = asyncio.create_task(self.mower._request_response(b"command"))
            await started.wait()
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.assertIsNone(self.mower.client)

    async def test_batch_lock_blocks_disconnect_without_deadlocking(self):
        self.ready()
        with patch.object(self.mower, "_read_data", AsyncMock(return_value=b"reply")):
            async with self.mower.lock:
                cleanup = asyncio.create_task(self.mower.disconnect())
                await asyncio.sleep(0)
                self.assertFalse(cleanup.done())
                self.assertEqual(
                    await self.mower._request_response_locked(b"batch"), b"reply"
                )
            await cleanup
        self.assertFalse(self.mower.is_connected())


if __name__ == "__main__":
    unittest.main()
