"""Scheduled Dock must arm parking before releasing a paused mower."""

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from bleak import BleakError
from automower_ble.protocol import ModeOfOperation as Mode
from automower_ble.protocol import MowerActivity as Activity
from automower_ble.protocol import MowerState as State
from automower_ble.protocol import OverrideAction as Override
from automower_ble.protocol import ResponseResult as R
from test_connection import Mower
from test_model_capabilities import model
from test_release_fixes import method
from gardena_connection_tests.parking import INDEFINITE, NEXT_SCHEDULE, TIMED

MODELS = (14, 18, 22, 25, 29, 30, 34, 35, 36, 37, 43)


class DockTests(unittest.IsolatedAsyncioTestCase):
    async def test_three_hour_start_pause_dock_replaces_override_before_trigger(self):
        mower, reads = self.mower()
        original = mower.command_response.side_effect
        trigger_overrides = []

        async def reply(name, **kwargs):
            if name == "SetOverrideMow":
                self.assertEqual(kwargs["duration"], 10800)
                reads["GetOverride"] = {"action": Override.FORCEDMOW}
            elif name == "Pause":
                reads["GetState"] = State.PAUSED
            elif name == "SetOverrideParkUntilNextStart":
                reads["GetOverride"] = {"action": Override.FORCEDPARK}
            elif name == "StartTrigger":
                trigger_overrides.append(reads["GetOverride"]["action"])
            return await original(name, **kwargs)

        mower.command_response.side_effect = reply
        mower.command_response_locked = mower.command_response
        self.assertIs(await mower.mower_override(3), R.OK)
        await mower.command_response("Pause")
        self.assertIs(await mower.mower_park(mode=NEXT_SCHEDULE), R.OK)
        self.assertEqual(trigger_overrides, [Override.FORCEDMOW, Override.FORCEDPARK])

    async def test_readback_transport_loss_and_cancellation_do_not_repeat_trigger(self):
        for error in (BleakError, asyncio.CancelledError):
            mower, reads = self.mower()
            original = mower.command_response.side_effect

            async def reply(name, **kwargs):
                if name == "GetMode" and reads["GetState"] == State.IN_OPERATION:
                    raise error("lost")
                return await original(name, **kwargs)

            mower.command_response.side_effect = reply
            if error is asyncio.CancelledError:
                with self.assertRaises(error):
                    await mower.mower_park(mode=NEXT_SCHEDULE)
            else:
                self.assertIs(await mower.mower_park(mode=NEXT_SCHEDULE), R.UNKNOWN_ERROR)
            self.assertFalse(mower.lock.locked())
            self.assertEqual([c.args[0] for c in mower.command_response.await_args_list].count("StartTrigger"), 1)

    def mower(self, device_type=14, count=1, trigger=R.OK, activity=Activity.GOING_HOME):
        mower = Mower(1, "00:00:00:00:00:00")
        mower.capabilities = model(device_type)
        mower.is_connected = Mock(return_value=True)
        reads = {
            "GetState": State.PAUSED,
            "GetNumberOfTasks": count,
            "GetMode": Mode.AUTO,
            "GetOverride": {"action": Override.FORCEDPARK},
            "GetActivity": activity,
        }

        async def reply(command, **kwargs):
            if command == "SetMode":
                reads["GetMode"] = kwargs["mode"]
            if command == "StartTrigger":
                reads["GetState"] = State.IN_OPERATION
                return trigger, None
            return R.OK, reads.get(command)

        mower.command_response = AsyncMock(side_effect=reply)
        return mower, reads

    async def test_all_profiles_arm_scheduled_park_before_trigger(self):
        for device_type in MODELS:
            for state in (State.PAUSED, State.IN_OPERATION, State.RESTRICTED):
                mower, reads = self.mower(device_type)
                reads["GetState"] = state
                self.assertIs(await mower.mower_park(mode=NEXT_SCHEDULE), R.OK)
                calls = mower.command_response.await_args_list
                self.assertEqual([c.args[0] for c in calls], [
                    "GetState", "GetMode", "GetNumberOfTasks", "SetMode",
                    "SetOverrideParkUntilNextStart", "StartTrigger",
                    "GetMode", "GetOverride", "GetState", "GetActivity",
                ])
                self.assertEqual(calls[3].kwargs["mode"], Mode.AUTO)

    async def test_no_calendar_keeps_generation_specific_permanent_sequence(self):
        for device_type in MODELS:
            mower, _ = self.mower(device_type, count=0)
            self.assertIs(await mower.mower_park(), R.OK)
            writes = [c for c in mower.command_response.await_args_list if not c.args[0].startswith("Get")]
            expected = ["SetMode", "StartTrigger"] if mower.capabilities.generation == 3 else ["SetMode", "ClearOverride", "StartTrigger"]
            self.assertEqual([c.args[0] for c in writes], expected)
            self.assertEqual(writes[0].kwargs["mode"], Mode.HOME)

    async def test_empty_schedule_falls_back_to_indefinite_for_all_profiles(self):
        for device_type in MODELS:
            with self.subTest(device_type=device_type):
                mower, _ = self.mower(device_type, count=0)
                self.assertIs(await mower.mower_park(mode=NEXT_SCHEDULE), R.OK)
                calls = mower.command_response.await_args_list
                writes = [c for c in calls if c.args[0] not in (
                    "GetState", "GetMode", "GetNumberOfTasks", "GetActivity", "GetOverride",
                )]
                expected = ["SetMode"]
                if mower.capabilities.generation == 4:
                    expected.append("ClearOverride")
                expected.append("StartTrigger")
                self.assertEqual([c.args[0] for c in writes], expected)
                self.assertEqual(writes[0].kwargs["mode"], Mode.HOME)

    async def test_preparation_failures_stop_without_trigger(self):
        for device_type in (14, 29):
            for command in ("GetState", "GetNumberOfTasks", "SetMode", "SetOverrideParkUntilNextStart"):
                mower, _ = self.mower(device_type)
                original = mower.command_response.side_effect

                async def reply(name, **kwargs):
                    return (R.DEVICE_BUSY, None) if name == command else await original(name, **kwargs)

                mower.command_response.side_effect = reply
                self.assertIs(await mower.mower_park(mode=NEXT_SCHEDULE), R.DEVICE_BUSY)
                names = [c.args[0] for c in mower.command_response.await_args_list]
                self.assertEqual(names[-1], command)
                self.assertNotIn("StartTrigger", names)

    async def test_unknown_profiles_safety_states_and_bad_counts_do_not_write(self):
        mower, _ = self.mower(99)
        self.assertIs(await mower.mower_park(mode=NEXT_SCHEDULE), R.NOT_AVAILABLE)
        mower.command_response.assert_not_awaited()
        for state in (State.OFF, State.STOPPED, State.WAIT_FOR_SAFETYPIN, State.ERROR, State.FATAL_ERROR, None):
            mower, reads = self.mower()
            reads["GetState"] = state
            self.assertIs(await mower.mower_park(mode=NEXT_SCHEDULE), R.NOT_ALLOWED)
            self.assertEqual(mower.command_response.await_count, 1)
        for count in (None, True, False, -1, "1", 0.0, 16, 0xFFFFFFFF):
            mower, _ = self.mower(count=count)
            self.assertIs(await mower.mower_park(mode=NEXT_SCHEDULE), R.NOT_AVAILABLE)
            self.assertEqual(mower.command_response.await_count, 3)

    async def test_ambiguous_trigger_requires_fresh_park_confirmation(self):
        for device_type in (14, 29):
            for activity in (Activity.GOING_HOME, Activity.PARKED, Activity.CHARGING):
                mower, _ = self.mower(device_type, trigger=R.UNKNOWN_ERROR, activity=activity)
                self.assertIs(await mower.mower_park(mode=NEXT_SCHEDULE), R.OK)
                self.assertEqual([c.args[0] for c in mower.command_response.await_args_list].count("StartTrigger"), 1)

    async def test_explicit_trigger_failure_is_not_overridden_by_readback(self):
        for result in (R.NOT_ALLOWED, R.DEVICE_BUSY, R.INVALID_ID):
            mower, _ = self.mower(trigger=result)
            self.assertIs(await mower.mower_park(mode=NEXT_SCHEDULE), result)
            self.assertEqual(mower.command_response.await_args_list[-1].args[0], "StartTrigger")

    async def test_mowing_after_acknowledgement_is_observed_without_replay(self):
        mower, reads = self.mower(activity=Activity.MOWING)

        async def settle(_):
            reads["GetActivity"] = Activity.GOING_HOME

        with patch("gardena_connection_tests.actions.asyncio.sleep", side_effect=settle) as sleep:
            self.assertIs(await mower.mower_park(mode=NEXT_SCHEDULE), R.OK)
        sleep.assert_awaited_once()
        self.assertEqual([c.args[0] for c in mower.command_response.await_args_list].count("StartTrigger"), 1)

    async def test_failed_or_mismatched_readback_is_not_success(self):
        for command, value in (
            ("GetMode", Mode.HOME), ("GetOverride", {"action": Override.FORCEDMOW}),
            ("GetState", State.PAUSED), ("GetActivity", Activity.MOWING),
            ("GetActivity", None),
            ("GetMode", False), ("GetActivity", True),
            ("GetOverride", {"action": True}),
        ):
            mower, reads = self.mower()
            original = mower.command_response.side_effect

            async def reply(name, **kwargs):
                result = await original(name, **kwargs)
                if name == "StartTrigger":
                    reads[command] = value
                return result

            mower.command_response.side_effect = reply
            with patch("gardena_connection_tests.actions.asyncio.sleep", side_effect=TimeoutError):
                self.assertIs(await mower.mower_park(mode=NEXT_SCHEDULE), R.UNKNOWN_ERROR)
        mower, reads = self.mower()
        original = mower.command_response.side_effect

        async def bad_read(name, **kwargs):
            if name == "GetMode" and reads["GetState"] == State.IN_OPERATION:
                return R.DEVICE_BUSY, Mode.AUTO
            return await original(name, **kwargs)

        mower.command_response.side_effect = bad_read
        with patch("gardena_connection_tests.actions.asyncio.sleep", side_effect=TimeoutError):
            self.assertIs(await mower.mower_park(mode=NEXT_SCHEDULE), R.UNKNOWN_ERROR)

    async def test_observation_timeout_does_not_replay(self):
        mower, _ = self.mower(activity=Activity.MOWING)
        with patch("gardena_connection_tests.actions.PARK_OBSERVATION_SECONDS", 0.01):
            self.assertIs(await mower.mower_park(mode=NEXT_SCHEDULE), R.UNKNOWN_ERROR)
        self.assertFalse(mower.lock.locked())
        self.assertEqual([c.args[0] for c in mower.command_response.await_args_list].count("StartTrigger"), 1)

    async def test_cancellation_and_transport_failure_propagate_without_replay(self):
        for error in (asyncio.CancelledError, BleakError):
            mower, _ = self.mower()
            mower.command_response.side_effect = error("interrupted")
            with self.assertRaises(error):
                await mower.mower_park(mode=NEXT_SCHEDULE)
            self.assertFalse(mower.lock.locked())
            self.assertEqual(mower.command_response.await_count, 1)

    async def test_poll_cannot_interleave_with_park_transaction(self):
        mower, _ = self.mower()
        preparing, attempted = asyncio.Event(), asyncio.Event()
        order = []
        original = mower.command_response.side_effect

        async def reply(name, **kwargs):
            order.append(name)
            if name == "SetMode":
                preparing.set()
                await attempted.wait()
            return await original(name, **kwargs)

        async def poll():
            await preparing.wait()
            attempted.set()
            async with mower.lock:
                order.append("poll")

        mower.command_response.side_effect = reply
        result, _ = await asyncio.gather(mower.mower_park(mode=NEXT_SCHEDULE), poll())
        self.assertIs(result, R.OK)
        self.assertGreater(order.index("poll"), order.index("StartTrigger"))

    async def test_observation_sleep_allows_pause_without_replaying_dock(self):
        mower, reads = self.mower(activity=Activity.MOWING)

        async def pause(_):
            async def other_task():
                async with mower.lock:
                    reads["GetState"] = State.PAUSED
            await asyncio.wait_for(asyncio.create_task(other_task()), 0.1)
            raise TimeoutError

        with patch("gardena_connection_tests.actions.asyncio.sleep", side_effect=pause):
            self.assertIs(await mower.mower_park(mode=NEXT_SCHEDULE), R.UNKNOWN_ERROR)
        self.assertEqual(reads["GetState"], State.PAUSED)
        self.assertEqual([c.args[0] for c in mower.command_response.await_args_list].count("StartTrigger"), 1)

    async def test_safety_state_during_confirmation_stops_observing(self):
        mower, reads = self.mower()
        original = mower.command_response.side_effect

        async def reply(name, **kwargs):
            result = await original(name, **kwargs)
            if name == "StartTrigger":
                reads["GetState"] = State.STOPPED
            return result

        mower.command_response.side_effect = reply
        self.assertIs(await mower.mower_park(mode=NEXT_SCHEDULE), R.NOT_ALLOWED)

    async def test_failed_clear_override_in_empty_calendar_does_not_trigger(self):
        mower, _ = self.mower(29, count=0)
        original = mower.command_response.side_effect

        async def reply(name, **kwargs):
            return (R.UNKNOWN_ERROR, None) if name == "ClearOverride" else await original(name, **kwargs)

        mower.command_response.side_effect = reply
        self.assertIs(await mower.mower_park(), R.UNKNOWN_ERROR)
        self.assertEqual(mower.command_response.await_args_list[-1].args[0], "ClearOverride")

    async def test_entity_never_resumes_or_publishes_optimistic_returning(self):
        dock = method("lawn_mower.py", "AutomowerLawnMower", "async_dock", {
            "LOGGER": Mock(), "ResponseResult": R, "HomeAssistantError": RuntimeError,
            "BleakError": BleakError,
        })
        for result in (R.OK, R.UNKNOWN_ERROR, R.NOT_ALLOWED):
            coordinator = SimpleNamespace(
                parking_mode=INDEFINITE, parking_duration_hours=3,
                _async_find_device=AsyncMock(),
                mower=SimpleNamespace(mower_park=AsyncMock(return_value=result), mower_resume=AsyncMock()),
                data={"state": State.PAUSED},
                update_cached_data=Mock(), schedule_action_refresh=Mock(),
            )
            entity = SimpleNamespace(coordinator=coordinator)
            if result is R.OK:
                await dock(entity)
            else:
                with self.assertRaises(RuntimeError):
                    await dock(entity)
            coordinator.mower.mower_resume.assert_not_awaited()
            coordinator.update_cached_data.assert_not_called()
            coordinator.schedule_action_refresh.assert_called_once()

    async def test_default_indefinite_ignores_calendar_and_preserves_hold(self):
        for device_type in (14, 29):
            for option in (INDEFINITE, NEXT_SCHEDULE, TIMED):
                mower, reads = self.mower(device_type, count=5)
                reads["GetMode"] = Mode.HOME
                self.assertIs(await mower.mower_park(mode=option), R.OK)
                calls = mower.command_response.await_args_list
                self.assertNotIn("GetNumberOfTasks", [c.args[0] for c in calls])
                self.assertNotIn("SetOverridePark", [c.args[0] for c in calls])
                self.assertNotIn("SetOverrideParkUntilNextStart", [c.args[0] for c in calls])
                self.assertTrue(all(c.kwargs["mode"] == Mode.HOME for c in calls if c.args[0] == "SetMode"))
            mower, _ = self.mower(device_type, count=5)
            self.assertIs(await mower.mower_park(), R.OK)
            self.assertNotIn("GetNumberOfTasks", [c.args[0] for c in mower.command_response.await_args_list])

    async def test_timed_parking_duration_and_invalid_inputs(self):
        for device_type in (14, 29):
            mower, _ = self.mower(device_type)
            self.assertIs(await mower.mower_park(mode=TIMED, duration_hours=1.5), R.OK)
            calls = mower.command_response.await_args_list
            override = next(c for c in calls if c.args[0] == "SetOverridePark")
            self.assertEqual(override.kwargs["duration"], 5400)
            self.assertLess(calls.index(override), next(i for i, c in enumerate(calls) if c.args[0] == "StartTrigger"))
        for duration in (True, 0, -1, 25, float("nan"), 0.6):
            mower, _ = self.mower()
            with self.assertRaises(ValueError):
                await mower.mower_park(mode=TIMED, duration_hours=duration)
            mower.command_response.assert_not_awaited()
