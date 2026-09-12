"""App-confirmed point enable/disable side effects on both generations."""

import unittest
from unittest.mock import AsyncMock, patch
from automower_ble.protocol import ResponseResult
from test_connection import Mower
from test_model_capabilities import model
from gardena_connection_tests.settings_protocol import set_starting_point_enabled


class StartingPointTests(unittest.IsolatedAsyncioTestCase):
    async def test_enabled_and_disabled_workflows_for_both_generations(self):
        for device_type in (14, 29, 43, 34):
            for enabled in (True, False):
                mower = Mower(1, "00:00:00:00:00:00", 1234)
                mower.capabilities = model(device_type)
                mower.command_response = AsyncMock(
                    return_value=(ResponseResult.OK, None)
                )
                point = {"enabled": int(enabled), "proportion": 30 if enabled else 0}
                with patch(
                    "gardena_connection_tests.settings_protocol.read_starting_point",
                    AsyncMock(return_value=(ResponseResult.OK, point)),
                ) as read:
                    result, actual = await set_starting_point_enabled(mower, 1, enabled)
                self.assertIs(result, ResponseResult.OK)
                self.assertEqual(actual, point)
                expected = ["SetStartingPointEnabled"]
                if not enabled:
                    expected.append("SetStartingPointProportion")
                expected.append("SetStartingPointEnabled")
                self.assertEqual(
                    [call.args[0] for call in mower.command_response.await_args_list],
                    expected,
                )
                if not enabled:
                    self.assertEqual(
                        mower.command_response.await_args_list[1].kwargs,
                        {"startingPointId": 1, "proportion": 0},
                    )
                read.assert_awaited_once_with(mower, 1)

    async def test_partial_failure_is_not_reported_as_success(self):
        mower = Mower(1, "00:00:00:00:00:00", 1234)
        mower.capabilities = model(14)
        mower.command_response = AsyncMock(
            side_effect=[(ResponseResult.OK, None), (ResponseResult.DEVICE_BUSY, None)]
        )
        with patch(
            "gardena_connection_tests.settings_protocol.read_starting_point",
            AsyncMock(),
        ) as read:
            self.assertEqual(
                await set_starting_point_enabled(mower, 1, False),
                (ResponseResult.DEVICE_BUSY, None),
            )
        read.assert_not_awaited()

    async def test_readback_mismatch_rejected(self):
        mower = Mower(1, "00:00:00:00:00:00", 1234)
        mower.capabilities = model(29)
        mower.command_response = AsyncMock(return_value=(ResponseResult.OK, None))
        with patch(
            "gardena_connection_tests.settings_protocol.read_starting_point",
            AsyncMock(
                return_value=(ResponseResult.OK, {"enabled": False, "proportion": 50})
            ),
        ):
            self.assertEqual(
                await set_starting_point_enabled(mower, 1, False),
                (ResponseResult.UNKNOWN_ERROR, None),
            )
