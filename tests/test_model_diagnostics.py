"""Generation-specific diagnostic sources and unknown/error handling."""

from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock
from automower_ble.protocol import ResponseResult
from test_model_capabilities import model
from gardena_connection_tests.model_diagnostics import (
    read_model_diagnostics,
    read_optional,
    read_statistics,
    read_spot_status,
    read_model_settings,
)


class DiagnosticTests(unittest.IsolatedAsyncioTestCase):
    async def test_settings_retry_busy_and_reject_invalid_bools(self):
        busy = True

        async def response(command, **kwargs):
            if busy:
                return ResponseResult.DEVICE_BUSY, None
            return ResponseResult.OK, 2 if command in (
                "GetGarageEnabled",
                "GetSensorControlEnabled",
            ) else 100

        mower = SimpleNamespace(
            capabilities=model(29), command_response=AsyncMock(side_effect=response)
        )
        unsupported = set()
        data = await read_model_settings(mower, unsupported)
        self.assertIsNone(data["ReversingDistance"])
        busy = False
        data = await read_model_settings(mower, unsupported)
        self.assertEqual(data["ReversingDistance"], 100)
        self.assertIsNone(data["GarageEnabled"])
        self.assertIsNone(data["garageSupported"])
        self.assertIsNone(data["SensorControlEnabled"])
        self.assertFalse(unsupported)

    async def test_spot_status_generation_mapping_and_runtime_gate(self):
        for device_type, values, expected in (
            (14, [1], 3),
            (14, [0], 0),
            (14, [2], None),
            (29, [1], 1),
            (29, [4], None),
            (34, [0], None),
            (34, [1, 3], 3),
            (99, [], None),
        ):
            mower = SimpleNamespace(
                capabilities=model(device_type),
                command_response=AsyncMock(
                    side_effect=[(ResponseResult.OK, value) for value in values]
                ),
            )
            self.assertEqual(await read_spot_status(mower, set()), expected)
            self.assertEqual(mower.command_response.await_count, len(values))

    async def test_transient_failure_retries_but_unsupported_stops(self):
        mower = SimpleNamespace(
            command_response=AsyncMock(
                side_effect=[
                    (ResponseResult.DEVICE_BUSY, None),
                    (ResponseResult.OK, 42),
                    (ResponseResult.INVALID_ID, None),
                ]
            )
        )
        unsupported = set()
        self.assertIsNone(await read_optional(mower, unsupported, "Read"))
        self.assertEqual(await read_optional(mower, unsupported, "Read"), 42)
        self.assertIsNone(await read_optional(mower, unsupported, "Read"))
        self.assertIsNone(await read_optional(mower, unsupported, "Read"))
        self.assertEqual(mower.command_response.await_count, 3)

    async def test_g4_collision_lift_and_front_rear_average(self):
        async def response(command, **kwargs):
            if command == "GetCollisionSensorStatus":
                return ResponseResult.OK, {"front": 0, "rear": 1}
            if command == "GetLiftSensorStatus":
                return ResponseResult.OK, 1
            if command == "GetLoopSignalStrength":
                return ResponseResult.OK, (20, 80)[kwargs["signalType"]]
            if command == "GetLoopSignals":
                return ResponseResult.OK, {
                    "guide1Signal": 3,
                    "guide2Signal": 4,
                    "guide3Signal": 5,
                }
            return ResponseResult.OK, 999999

        mower = SimpleNamespace(
            capabilities=model(29), command_response=AsyncMock(side_effect=response)
        )
        data = await read_model_diagnostics(mower, set())
        self.assertTrue(data["collision"])
        self.assertTrue(data["lift"])
        self.assertEqual(data["loopSignalStrength"], 50)
        self.assertIsNone(data["batteryCurrent"])
        self.assertNotIn("guide2Signal", data)
        self.assertNotIn("guide3Signal", data)
        self.assertNotIn(
            "GetComboardSensorData",
            [call.args[0] for call in mower.command_response.await_args_list],
        )

    async def test_g3_uses_only_legacy_diagnostics(self):
        mower = SimpleNamespace(
            capabilities=model(14),
            command_response=AsyncMock(
                return_value=(
                    ResponseResult.OK,
                    {"collision": 0, "lift": 1, "pitch": 123, "signalQuality": 77},
                )
            ),
        )
        data = await read_model_diagnostics(mower, set())
        self.assertEqual(
            [call.args[0] for call in mower.command_response.await_args_list],
            ["GetComboardSensorData", "GetSignalQuality"],
        )
        self.assertEqual(data["pitch"], 123)
        self.assertNotIn("batteryVoltage", data)

    async def test_unknown_model_does_not_guess_generation(self):
        mower = SimpleNamespace(capabilities=model(99), command_response=AsyncMock())
        self.assertEqual(await read_model_diagnostics(mower, set()), {})
        mower.command_response.assert_not_awaited()

    async def test_statistics_do_not_depend_on_aggregate_layout(self):
        async def response(command, **kwargs):
            return (
                (ResponseResult.INVALID_ID, None)
                if command == "GetAllStatistics"
                else (ResponseResult.OK, 100)
            )

        mower = SimpleNamespace(command_response=AsyncMock(side_effect=response))
        data = await read_statistics(mower, set())
        self.assertEqual(data["totalRunningTime"], 100)
        self.assertEqual(data["numberOfChargingCycles"], 100)
        self.assertIsNone(data["cuttingBladeUsageTime"])
