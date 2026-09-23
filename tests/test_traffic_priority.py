"""Real traffic lock, action wrapper and HA-facing reconnect/backoff regressions."""

import asyncio
import ast
import logging
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from automower_ble.protocol import ResponseResult as R, MowerActivity as A, MowerState as S
from bleak import BleakError
from test_connection import Mower
from test_release_fixes import COMPONENT, CONTROL, method
from gardena_connection_tests.traffic import BACKGROUND_READ, background_poll, foreground_action


class TrafficTests(unittest.IsolatedAsyncioTestCase):
    def test_priority_is_wired_into_start_dock_and_background_entry_points(self):
        for filename, class_name, name, decorator in (
            ("lawn_mower.py", "AutomowerLawnMower", "async_start_mowing", "foreground_action"),
            ("lawn_mower.py", "AutomowerLawnMower", "async_dock", "foreground_action"),
            ("coordinator.py", "GardenaCoordinator", "_async_update_data", "background_poll"),
            ("calendar.py", "GardenaMowerScheduleCalendar", "async_update", "background_poll"),
            ("calendar.py", "GardenaMowerScheduleCalendar", "async_get_events", "background_poll"),
        ):
            tree = ast.parse((COMPONENT / filename).read_text())
            cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == class_name)
            node = next(n for n in cls.body if isinstance(n, ast.AsyncFunctionDef) and n.name == name)
            self.assertIn(decorator, [d.id for d in node.decorator_list if isinstance(d, ast.Name)])

    async def test_inflight_poll_completes_without_cancellation_before_action(self):
        mower = Mower(1, "00:00:00:00:00:00")
        entered, finish = asyncio.Event(), asyncio.Event()
        order = []

        @background_poll
        async def poll():
            async with mower.lock:
                entered.set()
                await finish.wait()
                order.append("reply")

        @foreground_action
        async def action(self):
            async with mower.lock:
                order.append("action")

        poll_task = asyncio.create_task(poll())
        await entered.wait()
        action_task = asyncio.create_task(action(SimpleNamespace(coordinator=SimpleNamespace(mower=mower))))
        await asyncio.sleep(0)
        self.assertFalse(action_task.done())
        finish.set()
        await asyncio.gather(poll_task, action_task)
        self.assertEqual(order, ["reply", "action"])

    async def test_queued_poll_yields_but_user_pause_and_heartbeat_can_run(self):
        mower = Mower(1, "00:00:00:00:00:00")
        attempted, completed = asyncio.Event(), asyncio.Event()

        @background_poll
        async def poll():
            attempted.set()
            async with mower.lock:
                completed.set()

        # Poll is already queued before the action window is opened.
        async with mower.lock:
            task = asyncio.create_task(poll())
            await attempted.wait()
            window = mower.lock.action_window()
            await window.__aenter__()
        await asyncio.sleep(0)
        self.assertFalse(completed.is_set())
        async with mower.lock:  # User Pause can still acquire the wire.
            pass
        token = BACKGROUND_READ.set(True)  # Keep-alive task inherited poll context.
        try:
            self.assertEqual(
                await asyncio.wait_for(mower._timed_command(AsyncMock(return_value="ok"), "KeepAlive"), .2),
                "ok",
            )
        finally:
            BACKGROUND_READ.reset(token)
        await window.__aexit__(None, None, None)
        await asyncio.wait_for(task, .2)
        self.assertTrue(completed.is_set())

    async def test_nested_windows_and_cancelled_waiter_do_not_leak_priority(self):
        mower = Mower(1, "00:00:00:00:00:00")

        @background_poll
        async def poll():
            async with mower.lock:
                return True

        async with mower.lock.action_window():
            async with mower.lock.action_window():
                blocked = asyncio.create_task(poll())
                await asyncio.sleep(0)
            self.assertFalse(blocked.done())
            blocked.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await blocked
        self.assertTrue(await asyncio.wait_for(poll(), .2))
        self.assertEqual(mower.lock._actions, 0)

    async def test_confirmation_succeeds_while_background_poll_is_deferred(self):
        mower = Mower(1, "00:00:00:00:00:00")
        triggered = False
        pending = None
        polled = asyncio.Event()

        @background_poll
        async def poll():
            async with mower.lock:
                polled.set()
                await asyncio.sleep(.1)

        async def state():
            async with mower.lock:
                return S.IN_OPERATION if triggered else S.RESTRICTED

        async def activity():
            async with mower.lock:
                return A.GOING_OUT if triggered else A.PARKED

        async def start(_duration):
            nonlocal triggered, pending
            triggered = True
            pending = asyncio.create_task(poll())
            await asyncio.sleep(0)
            return R.UNKNOWN_ERROR

        mower.mower_state = state
        mower.mower_activity = activity
        mower.mower_override = AsyncMock(side_effect=start)
        mower.is_connected = lambda: True
        entity = SimpleNamespace(coordinator=SimpleNamespace(mower=mower))

        @foreground_action
        async def action(self):
            await CONTROL.start_manual_mowing(mower, 3, AsyncMock())
            self.assertion = not polled.is_set()

        await asyncio.wait_for(action(entity), .5)
        self.assertTrue(entity.assertion)
        await pending
        mower.mower_override.assert_awaited_once()

    async def test_action_exception_and_cancellation_restore_polling(self):
        mower = Mower(1, "00:00:00:00:00:00")
        entity = SimpleNamespace(coordinator=SimpleNamespace(mower=mower))
        for error in (RuntimeError, asyncio.CancelledError):
            @foreground_action
            async def action(self):
                raise error()
            with self.assertRaises(error):
                await action(entity)
            self.assertEqual(mower.lock._actions, 0)
            self.assertTrue(mower.lock._background_allowed.is_set())


class RecoveryTests(unittest.IsolatedAsyncioTestCase):
    def reconnect(self, devices):
        mower = Mower(1, "00:00:00:00:00:00")
        mower.is_connected = Mock(return_value=False)
        mower.disconnect = AsyncMock()
        mower.connect = AsyncMock(return_value=R.OK)
        lookup = Mock(side_effect=devices)
        connect = method("coordinator.py", "GardenaCoordinator", "_async_find_device", {
            "asyncio": asyncio, "LOGGER": logging.getLogger(__name__),
            "close_stale_connections_by_address": AsyncMock(),
            "bluetooth": SimpleNamespace(async_ble_device_from_address=lookup),
            "UpdateFailed": RuntimeError, "BleakError": BleakError,
            "ResponseResult": R, "connection_failure": lambda result: result.name,
            "DISCOVERY_WAIT_SECONDS": .03, "DISCOVERY_POLL_SECONDS": .001,
        })
        coordinator = SimpleNamespace(mower=mower, hass=None, address=mower.address)
        return connect, coordinator, lookup

    async def test_late_advertisement_connects_once_without_movement(self):
        device = object()
        connect, coordinator, lookup = self.reconnect([None, None, device])
        await connect(coordinator)
        self.assertEqual(lookup.call_count, 3)
        coordinator.mower.connect.assert_awaited_once_with(device)

    async def test_missing_advertisement_times_out_without_connect(self):
        connect, coordinator, lookup = self.reconnect(None)
        lookup.return_value = None
        with self.assertRaisesRegex(RuntimeError, "no movement command was sent"):
            await connect(coordinator)
        coordinator.mower.connect.assert_not_awaited()
        self.assertFalse(coordinator.mower.lock.locked())

    async def test_discovery_cancellation_releases_lock(self):
        connect, coordinator, lookup = self.reconnect(None)
        lookup.return_value = None
        task = asyncio.create_task(connect(coordinator))
        await asyncio.sleep(0)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        coordinator.mower.connect.assert_not_awaited()
        self.assertFalse(coordinator.mower.lock.locked())

    async def test_static_failures_back_off_and_success_caches(self):
        now = [1000]
        read = method("coordinator.py", "GardenaCoordinator", "_async_update_static_info", {
            "Any": object, "monotonic": lambda: now[0], "STATIC_RETRY_SECONDS": 300,
            "ResponseResult": R, "UNSUPPORTED": {R.NOT_AVAILABLE},
            "LOGGER": logging.getLogger(__name__),
        })
        coordinator = SimpleNamespace(
            _static_data={}, _static_retry_after={}, _unsupported_static_commands=set(),
            mower=SimpleNamespace(command_response=AsyncMock(return_value=(R.UNKNOWN_ERROR, None))),
        )
        await read(coordinator, {})
        first = coordinator.mower.command_response.await_count
        self.assertGreater(first, 0)
        await read(coordinator, {})
        self.assertEqual(coordinator.mower.command_response.await_count, first)
        self.assertEqual(coordinator._unsupported_static_commands, set())
        now[0] += 301
        coordinator.mower.command_response.return_value = (R.OK, 1234)
        data = {}
        await read(coordinator, data)
        self.assertEqual(data["productionTime"], 1234)
        second = coordinator.mower.command_response.await_count
        now[0] += 301
        await read(coordinator, {})
        self.assertEqual(coordinator.mower.command_response.await_count, second)

    async def test_static_timeout_is_not_swallowed_or_retried_immediately(self):
        read = method("coordinator.py", "GardenaCoordinator", "_async_update_static_info", {
            "Any": object, "monotonic": lambda: 1000, "STATIC_RETRY_SECONDS": 300,
            "ResponseResult": R, "UNSUPPORTED": {R.NOT_AVAILABLE},
            "LOGGER": logging.getLogger(__name__),
        })
        command = AsyncMock(side_effect=TimeoutError)
        coordinator = SimpleNamespace(
            _static_data={}, _static_retry_after={}, _unsupported_static_commands=set(),
            mower=SimpleNamespace(command_response=command),
        )
        with self.assertRaises(TimeoutError):
            await read(coordinator, {})
        self.assertEqual(coordinator._static_retry_after["GetUserMowerName"], 1300)
        self.assertEqual(coordinator._unsupported_static_commands, set())
