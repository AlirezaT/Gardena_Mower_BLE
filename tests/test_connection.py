"""Exercise connection races against the actual pinned upstream library."""

import asyncio
import importlib.util
import sys
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import AsyncMock, patch

from automower_ble.protocol import BLEClient, ResponseResult
from bleak import BleakError

_PATH = Path(__file__).parents[1] / "custom_components/gardena_mower_ble/connection.py"
_PACKAGE = ModuleType("gardena_connection_tests")
_PACKAGE.__path__ = [str(_PATH.parent)]
sys.modules[_PACKAGE.__name__] = _PACKAGE
_SPEC = importlib.util.spec_from_file_location(
    "gardena_connection_tests.connection", _PATH
)
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

    async def test_pairing_wait_is_bounded_and_cleans_client(self):
        self.client.pair = AsyncMock(side_effect=lambda: None)

        async def stalled_pair():
            await asyncio.Event().wait()

        self.client.pair.side_effect = stalled_pair

        with (
            patch("automower_ble.protocol.establish_connection", AsyncMock(return_value=self.client)),
            patch.object(_MODULE, "CONNECT_TIMEOUT", 0.01),
        ):
            with self.assertRaisesRegex(BleakError, "connection/pairing timed out"):
                await self.mower.connect(SimpleNamespace(name="test mower"))
        self.client.pair.assert_awaited_once()
        self.client.disconnect.assert_awaited_once()
        self.assertEqual(self.mower.connection_diagnostics["outcome"], "timeout")
        self.assertIsNone(self.mower.client)

    async def test_external_cancellation_is_not_a_pairing_error(self):
        started = asyncio.Event()

        async def connect(mower, device):
            mower.client = self.client
            started.set()
            await asyncio.Event().wait()

        with patch.object(BLEClient, "connect", connect):
            task = asyncio.create_task(self.mower.connect(object()))
            await started.wait()
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
        self.client.disconnect.assert_awaited_once()
        self.assertEqual(self.mower.connection_diagnostics["outcome"], "cancelled")

    async def test_source_is_actual_backend_not_discovery_candidate(self):
        self.client._backend = SimpleNamespace(_source="actual proxy", secret="not exported")
        self.client._connected_scanner = SimpleNamespace(source="actual proxy", name="Kitchen")

        async def connect(mower, device):
            self.ready()
            return ResponseResult.OK

        with (
            patch.object(BLEClient, "connect", connect),
            patch.object(self.mower, "_ensure_keep_alive"),
        ):
            await self.mower.connect(SimpleNamespace(details={"source": "other proxy"}))
        self.assertEqual(self.mower.connection_diagnostics["source"], "actual proxy")
        self.assertEqual(self.mower.connection_diagnostics["source_name"], "Kitchen")
        self.assertNotIn("secret", str(self.mower.connection_diagnostics))
        await self.mower.disconnect()
        self.assertEqual(self.mower.connection_diagnostics["source"], "actual proxy")

    async def test_new_attempt_does_not_reuse_previous_proxy(self):
        self.mower.connection_diagnostics = {"source": "old proxy"}

        async def connect(mower, device):
            raise BleakError("no connection")

        with patch.object(BLEClient, "connect", connect):
            with self.assertRaises(BleakError):
                await self.mower.connect(object())
        self.assertNotIn("source", self.mower.connection_diagnostics)

    def test_access_refused_does_not_claim_invalid_pin(self):
        message = _MODULE.connection_failure(ResponseResult.NOT_ALLOWED)
        self.assertIn("pairing mode", message)
        self.assertIn("does not by itself mean the PIN is wrong", message)
        self.assertIn("rejected the operator PIN", _MODULE.connection_failure(ResponseResult.INVALID_PIN))

    def test_bluez_diagnostics_omit_mower_device_path(self):
        self.mower.client = self.client
        self.client._backend = SimpleNamespace(_device_path="/org/bluez/hci1/dev_private")
        self.mower._capture_connection_source()
        self.assertEqual(self.mower.connection_diagnostics["adapter"], "hci1")
        self.assertNotIn("dev_private", str(self.mower.connection_diagnostics))

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

        with (
            patch.object(BLEClient, "connect", connect),
            patch.object(self.mower, "_ensure_keep_alive"),
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
