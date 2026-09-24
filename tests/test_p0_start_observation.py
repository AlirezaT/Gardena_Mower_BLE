"""P0 service confirmation stays read-only, paced, bounded and cancellable."""

import asyncio
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from automower_ble.protocol import MowerActivity as A, MowerState as S, ResponseResult as R
from bleak import BleakError

from test_connection import Mower
from test_model_capabilities import model
from test_release_fixes import CONTROL
from gardena_connection_tests.traffic import background_poll, foreground_action


class P0StartTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mower = Mower(1, "00:00:00:00:00:00", 1234)
        self.mower.capabilities = model(14)
        self.mower.is_connected = Mock(return_value=True)
        self.mower.disconnect = AsyncMock()
        self.mower.mower_state = AsyncMock(return_value=S.RESTRICTED)
        self.mower.mower_activity = AsyncMock(return_value=A.PARKED)
        self.mower.command_response = AsyncMock(return_value=(R.OK, 0))
        self.mower.command_response_locked = AsyncMock(side_effect=[
            (R.OK, None), (R.OK, None), (R.UNKNOWN_ERROR, None),
        ])
        self.ensure = AsyncMock()
        self.entity = SimpleNamespace(coordinator=SimpleNamespace(mower=self.mower))
        self.real_sleep = asyncio.sleep
        self.sleeps = []

    async def sleep(self, seconds):
        self.sleeps.append(seconds)
        # Preserve scheduling without waiting five real seconds in unit tests.
        await self.real_sleep(0)

    async def start(self):
        @foreground_action
        async def action(entity):
            return await CONTROL.start_manual_mowing(self.mower, 3, self.ensure)
        return await action(self.entity)

    def writes(self):
        return [c.args[0] for c in self.mower.command_response_locked.await_args_list]

    def assert_no_replay(self):
        self.assertEqual(self.writes(), ["SetMode", "SetOverrideMow", "StartTrigger"])
        self.ensure.assert_awaited_once()
        self.mower.disconnect.assert_not_awaited()
        self.assertFalse(self.mower.lock.locked())
        self.assertEqual(self.mower.lock._actions, 0)

    async def test_one_observer_waits_before_each_sample_and_retains_departure(self):
        self.mower.mower_state.side_effect = [S.RESTRICTED, S.IN_OPERATION, S.IN_OPERATION]
        self.mower.mower_activity.side_effect = [A.PARKED, A.CHARGING, A.GOING_OUT]
        with patch.object(CONTROL.asyncio, "sleep", self.sleep):
            self.assertEqual(await self.start(), (S.IN_OPERATION, A.GOING_OUT))
        self.assertEqual(self.sleeps, [5, 5])
        self.assertEqual(self.mower.mower_state.await_count, 3)
        self.assertEqual(self.mower.mower_activity.await_count, 3)
        self.assertEqual([c.args[0] for c in self.mower.command_response.await_args_list],
                         ["GetMode", "GetOverride", "GetRestrictionReason", "GetRemainingChargingTime"])
        self.assert_no_replay()

    async def test_ok_reply_does_not_publish_mowing_before_departure(self):
        self.mower.command_response_locked.side_effect = [(R.OK, None)] * 3
        self.mower.mower_state.side_effect = [S.RESTRICTED, S.IN_OPERATION]
        self.mower.mower_activity.side_effect = [A.PARKED, A.MOWING]
        with patch.object(CONTROL.asyncio, "sleep", self.sleep):
            self.assertEqual(await self.start(), (S.IN_OPERATION, A.MOWING))
        self.assertEqual(self.sleeps, [5])
        self.assert_no_replay()

    async def test_charging_or_pending_alone_cannot_confirm_departure(self):
        for state in (S.IN_OPERATION, S.PENDING_START):
            with self.subTest(state=state):
                self.setUp()
                self.mower.mower_state.return_value = state
                self.mower.mower_activity.return_value = A.CHARGING
                with patch.object(CONTROL, "START_OBSERVATION_SECONDS", .02), patch.object(CONTROL, "P0_START_POLL_SECONDS", .001):
                    with self.assertRaisesRegex(CONTROL.ManualStartError, "CHARGING"):
                        await self.start()
                self.assert_no_replay()

    async def test_pause_and_heartbeat_can_run_while_background_waits(self):
        polled = asyncio.Event()

        @background_poll
        async def poll():
            async with self.mower.lock:
                polled.set()

        self.mower.mower_state.side_effect = [S.RESTRICTED, S.IN_OPERATION]
        self.mower.mower_activity.side_effect = [A.PARKED, A.GOING_OUT]
        pending = None

        async def sleep(seconds):
            nonlocal pending
            self.assertEqual(seconds, 5)
            self.assertFalse(self.mower.lock.locked())
            pending = asyncio.create_task(poll())
            await self.real_sleep(0)
            async with self.mower.lock:  # Explicit Pause remains eligible.
                pass
            await self.mower._timed_command(AsyncMock(return_value=None), "KeepAlive")
            self.assertFalse(polled.is_set())

        with patch.object(CONTROL.asyncio, "sleep", sleep):
            await self.start()
        await asyncio.wait_for(pending, .2)
        self.assertTrue(polled.is_set())
        self.assert_no_replay()

    async def test_disconnect_or_new_session_during_wait_is_not_confirmed(self):
        for changed in (False, True):
            with self.subTest(new_session=changed):
                self.setUp()

                async def sleep(seconds):
                    if changed:
                        self.mower.session_id += 1
                    else:
                        self.mower.is_connected.return_value = False

                with patch.object(CONTROL.asyncio, "sleep", sleep):
                    with self.assertRaisesRegex(CONTROL.ManualStartError, "start was not repeated"):
                        await self.start()
                self.assertEqual(self.mower.mower_state.await_count, 1)
                self.assert_no_replay()

    async def test_cancellation_during_wait_restores_background_access(self):
        with patch.object(CONTROL.asyncio, "sleep", AsyncMock(side_effect=asyncio.CancelledError)):
            with self.assertRaises(asyncio.CancelledError):
                await self.start()
        self.assert_no_replay()

    async def test_safety_stop_during_observation_is_not_ignored(self):
        self.mower.mower_state.side_effect = [S.RESTRICTED, S.STOPPED]
        with patch.object(CONTROL.asyncio, "sleep", self.sleep):
            with self.assertRaisesRegex(CONTROL.ManualStartError, "STOPPED"):
                await self.start()
        self.assert_no_replay()

    async def test_explicit_trigger_rejection_is_not_observed_as_success(self):
        self.mower.command_response_locked.side_effect = [(R.OK, None), (R.OK, None), (R.NOT_ALLOWED, None)]
        with patch.object(CONTROL.asyncio, "sleep", self.sleep):
            with self.assertRaisesRegex(CONTROL.ManualStartError, "NOT_ALLOWED"):
                await self.start()
        self.assertEqual(self.sleeps, [])
        self.assert_no_replay()

    async def test_changed_session_while_waiting_for_sample_lock_is_rejected(self):
        async with self.mower.lock:
            task = asyncio.create_task(CONTROL._p0_start_state(self.mower, self.mower.session_id))
            await self.real_sleep(0)
            self.mower.session_id += 1
        with self.assertRaises(BleakError):
            await task
        self.mower.mower_state.assert_not_awaited()

    async def test_safety_state_after_diagnostics_prevents_all_writes(self):
        for state in (S.STOPPED, S.WAIT_FOR_SAFETYPIN, S.ERROR, S.FATAL_ERROR, S.OFF):
            self.mower.mower_state.return_value = state
            with self.assertRaises(CONTROL.ManualStartError):
                await self.start()
        self.mower.command_response_locked.assert_not_awaited()

    async def test_snapshot_timeout_or_cancellation_never_starts(self):
        for error in (TimeoutError, BleakError, asyncio.CancelledError):
            self.mower.command_response.side_effect = error()
            with self.assertRaises(error):
                await self.start()
            self.mower.command_response_locked.assert_not_awaited()
            self.assertFalse(self.mower.lock.locked())
            self.assertEqual(self.mower.lock._actions, 0)

    async def test_optional_rejected_snapshot_field_does_not_invent_values(self):
        self.mower.command_response.side_effect = [(R.OK, 2), (R.OK, {"action": 0, "duration": 0, "secret": "PRIVATE"}),
                                                   (R.INVALID_ID, 123), (R.OK, 600)]
        self.mower.mower_state.side_effect = [S.RESTRICTED, S.IN_OPERATION]
        self.mower.mower_activity.side_effect = [A.PARKED, A.GOING_OUT]
        with self.assertLogs("control", "DEBUG") as logs, patch.object(CONTROL.asyncio, "sleep", self.sleep):
            await self.start()
        text = "\n".join(logs.output)
        self.assertIn("P0 pre-start snapshot action=1:action session=0", text)
        self.assertIn("INVALID_ID", text)
        self.assertIn("unavailable", text)
        self.assertNotIn("PRIVATE", text)
        self.assert_no_replay()

    async def test_read_timeout_after_trigger_never_replays(self):
        self.mower.mower_state.side_effect = [S.RESTRICTED, TimeoutError()]
        with patch.object(CONTROL.asyncio, "sleep", self.sleep):
            with self.assertRaises(CONTROL.ManualStartError):
                await self.start()
        self.assert_no_replay()

    async def test_minimo_keeps_existing_path_without_extra_snapshot(self):
        self.mower.capabilities = model(29)
        self.mower.mower_override = AsyncMock(return_value=R.OK)
        with patch.object(CONTROL.asyncio, "sleep", self.sleep):
            self.assertIsNone(await self.start())
        self.mower.mower_override.assert_awaited_once_with(3)
        self.mower.command_response.assert_not_awaited()
        self.assertEqual(self.sleeps, [])
