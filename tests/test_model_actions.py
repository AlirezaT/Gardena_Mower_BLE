"""Action ordering and SpotCut restore must not create extra mowing time."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from automower_ble.mower import Mower as UpstreamMower

from automower_ble.protocol import (
    ModeOfOperation,
    MowerActivity,
    MowerState,
    OverrideAction,
    ResponseResult,
)
from test_connection import Mower
from test_model_capabilities import model
from test_release_fixes import method


class ActionTests(unittest.IsolatedAsyncioTestCase):
    def mower(self, device_type):
        mower = Mower(1, "00:00:00:00:00:00", 1234)
        mower.capabilities = model(device_type)
        mower.command_response = AsyncMock(return_value=(ResponseResult.OK, None))
        return mower

    async def test_park_sequence_per_generation(self):
        for device_type, expected in (
            (14, ["SetMode", "StartTrigger"]),
            (29, ["SetMode", "ClearOverride", "StartTrigger"]),
            (99, []),
        ):
            mower = self.mower(device_type)
            result = await mower.mower_park_permanently()
            self.assertEqual(
                [c.args[0] for c in mower.command_response.await_args_list], expected
            )
            self.assertIs(
                result, ResponseResult.OK if expected else ResponseResult.NOT_AVAILABLE
            )

    async def test_park_stops_on_each_failed_reply(self):
        for fail_at in range(3):
            mower = self.mower(29)
            mower.command_response.side_effect = [
                (ResponseResult.OK, None)
            ] * fail_at + [(ResponseResult.DEVICE_BUSY, None)]
            self.assertIs(
                await mower.mower_park_permanently(), ResponseResult.DEVICE_BUSY
            )
            self.assertEqual(mower.command_response.await_count, fail_at + 1)

    async def test_resume_failures_propagate(self):
        mower = self.mower(29)
        mower.command_response.return_value = ResponseResult.DEVICE_BUSY, None
        self.assertIs(await mower.mower_resume(), ResponseResult.DEVICE_BUSY)
        mower.command_response.reset_mock()
        self.assertIs(await mower.mower_resume_schedule(), ResponseResult.DEVICE_BUSY)
        mower.command_response.assert_awaited_once_with("ClearOverride")

    async def test_g3_spot_sequence_and_stop(self):
        mower = self.mower(14)
        self.assertIs(await mower.mower_spot_cut(), ResponseResult.OK)
        self.assertEqual(
            [c.args[0] for c in mower.command_response.await_args_list],
            ["Pause", "SetMode", "SetOverrideMow", "StartSpotCutting", "StartTrigger"],
        )
        self.assertEqual(
            mower.command_response.await_args_list[2].kwargs, {"duration": 300}
        )
        mower.command_response.reset_mock()
        await mower.mower_stop_spot_cut()
        mower.command_response.assert_awaited_once_with("StopSpotCutting")

    async def test_minimo_still_delegates_to_tested_upstream_sequence(self):
        mower = self.mower(29)
        for name in ("mower_spot_cut", "mower_stop_spot_cut"):
            with patch.object(
                UpstreamMower, name, AsyncMock(return_value=ResponseResult.OK)
            ) as original:
                self.assertIs(await getattr(mower, name)(), ResponseResult.OK)
                original.assert_awaited_once()

    async def test_other_g4_requires_availability_then_uses_modern_actions(self):
        for device_type in (34, 43):
            mower = self.mower(device_type)
            self.assertIs(await mower.mower_spot_cut(), ResponseResult.NOT_AVAILABLE)
            mower.command_response.reset_mock()
            mower.command_response.return_value = ResponseResult.OK, True
            self.assertIs(await mower.mower_spot_cut(), ResponseResult.OK)
            self.assertEqual(
                [c.args[0] for c in mower.command_response.await_args_list],
                [
                    "GetSpotCutAvailable",
                    "Pause",
                    "SetMode",
                    "PrepareSpotCutting",
                    "StartTrigger",
                ],
            )
            mower.command_response.reset_mock()
            await mower.mower_stop_spot_cut()
            self.assertEqual(
                [c.args[0] for c in mower.command_response.await_args_list],
                ["GetSpotCutAvailable", "AbortSpotCutting"],
            )

    async def test_g3_spot_stops_at_each_failure(self):
        for index in range(5):
            mower = self.mower(14)
            mower.command_response.side_effect = [(ResponseResult.OK, None)] * index + [
                (ResponseResult.DEVICE_BUSY, None)
            ]
            self.assertIs(await mower.mower_spot_cut(), ResponseResult.DEVICE_BUSY)
            self.assertEqual(mower.command_response.await_count, index + 1)


class RestoreTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.namespace = dict(
            ModeOfOperation=ModeOfOperation,
            MowerActivity=MowerActivity,
            MowerState=MowerState,
            OverrideAction=OverrideAction,
            ResponseResult=ResponseResult,
            HomeAssistantError=RuntimeError,
            time=SimpleNamespace(monotonic=lambda: 10000),
        )
        self.restore = method(
            "switch.py",
            "GardenaMowerBleSpotCutSwitch",
            "_async_restore_previous_state",
            self.namespace,
        )
        self.duration = method(
            "switch.py",
            "GardenaMowerBleSpotCutSwitch",
            "_restore_duration_hours",
            self.namespace,
        )
        self.mower = SimpleNamespace(
            **{
                name: AsyncMock(return_value=ResponseResult.OK)
                for name in (
                    "mower_park",
                    "mower_park_permanently",
                    "mower_override",
                    "mower_resume",
                    "mower_resume_schedule",
                )
            }
        )
        self.entity = SimpleNamespace(coordinator=SimpleNamespace(mower=self.mower))
        self.entity._restore_duration_hours = lambda value: self.duration(
            self.entity, value
        )

    def test_expired_missing_invalid_and_future_duration_never_restarts(self):
        self.entity._spot_cut_restore_state = {}
        for value in (
            {},
            {"duration": 3600},
            {"duration": True, "startTime": 9999},
            {"duration": 3600, "startTime": 5000},
            {"duration": 3600, "startTime": 10001},
        ):
            self.assertEqual(self.duration(self.entity, value), 0)
        self.entity._spot_cut_restore_state = {"override_deadline": 9999}
        self.assertEqual(self.duration(self.entity, {}), 0)
        self.entity._spot_cut_restore_state = {"override_deadline": 11800}
        self.assertEqual(self.duration(self.entity, {}), 0.5)

    async def test_scheduled_mowing_does_not_become_manual_override(self):
        self.entity._spot_cut_restore_state = {
            "activity": MowerActivity.MOWING,
            "override": {"action": OverrideAction.NONE},
        }
        await self.restore(self.entity)
        self.mower.mower_override.assert_not_awaited()
        self.mower.mower_resume_schedule.assert_awaited_once()
        self.mower.mower_resume.assert_awaited_once()

    async def test_expired_manual_override_parks(self):
        self.entity._spot_cut_restore_state = {
            "activity": MowerActivity.MOWING,
            "override": {
                "action": OverrideAction.FORCEDMOW,
                "startTime": 5000,
                "duration": 3600,
            },
        }
        await self.restore(self.entity)
        self.mower.mower_override.assert_not_awaited()
        self.mower.mower_park.assert_awaited_once()

    async def test_live_manual_override_only_restores_remainder(self):
        self.entity._spot_cut_restore_state = {
            "activity": MowerActivity.MOWING,
            "override_deadline": 11800,
            "override": {
                "action": OverrideAction.FORCEDMOW,
                "startTime": 8200,
                "duration": 3600,
            },
        }
        await self.restore(self.entity)
        self.mower.mower_override.assert_awaited_once_with(0.5)

    async def test_park_restore_does_not_send_duplicate_start(self):
        self.entity._spot_cut_restore_state = {"permanentPark": True}
        await self.restore(self.entity)
        self.mower.mower_park_permanently.assert_awaited_once()
        self.mower.mower_resume.assert_not_awaited()

    async def test_capture_uses_device_clock_then_monotonic_deadline(self):
        turn_on = method(
            "switch.py", "GardenaMowerBleSpotCutSwitch", "async_turn_on", self.namespace
        )
        for result, device_time, expected in (
            (ResponseResult.OK, 18000, 11800),
            (ResponseResult.DEVICE_BUSY, None, None),
            (ResponseResult.OK, None, None),
        ):
            state = {
                "override": {
                    "action": OverrideAction.FORCEDMOW,
                    "startTime": 16200,
                    "duration": 3600,
                }
            }
            self.entity.is_on = False
            self.entity._async_ensure_connected = AsyncMock()
            self.entity._capture_restore_state = lambda: state
            self.mower.command_response = AsyncMock(return_value=(result, device_time))
            self.mower.mower_spot_cut = AsyncMock(return_value=ResponseResult.OK)
            self.entity.coordinator.update_cached_data = Mock()
            self.entity.coordinator.schedule_action_refresh = Mock()
            await turn_on(self.entity)
            self.assertEqual(state.get("override_deadline"), expected)
            self.mower.mower_spot_cut.assert_awaited_once()

    async def test_restore_stops_when_clearing_schedule_override_fails(self):
        self.entity._spot_cut_restore_state = {"activity": MowerActivity.MOWING}
        self.mower.mower_resume_schedule.return_value = ResponseResult.DEVICE_BUSY
        with self.assertRaisesRegex(RuntimeError, "Restore schedule failed"):
            await self.restore(self.entity)
        self.mower.mower_resume.assert_not_awaited()
        self.mower.mower_override.assert_not_awaited()
