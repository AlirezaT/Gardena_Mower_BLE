"""Regression checks for app 9.2.0 command identities and enum values."""

import ast
import logging
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from automower_ble.protocol import Command, ResponseResult

from test_release_fixes import COMPONENT, load, method

SETTINGS = load("settings_protocol")


class EntityProtocolAuditTests(unittest.IsolatedAsyncioTestCase):
    def test_radar_identity_and_response_order(self):
        protocol = SETTINGS.corrected_protocol({})
        spec = protocol["GetAntiCollisionRadar"]
        self.assertEqual((spec["major"], spec["minor"]), (5356, 7))
        response = bytearray(19)
        response[17] = 3
        response.extend((1, 0, 1))
        self.assertEqual(
            Command(1, spec).parse_response(response),
            {"available": 1, "enabled": 0, "useAtBoundary": 1},
        )
        for enabled in (False, True):
            request = Command(
                1, protocol["SetAntiCollisionRadarEnabled"]
            ).generate_request(enabled=enabled)
            self.assertEqual(request[12:14], (5356).to_bytes(2, "little"))
            self.assertEqual(request[14:16], (3).to_bytes(2, "little"))
            self.assertEqual(request[-3], int(enabled))

    def test_zone_protect_is_separate_from_radar(self):
        spec = SETTINGS.corrected_protocol({})["GetZoneProtectSettings"]
        self.assertEqual((spec["major"], spec["minor"]), (6050, 4))
        response = bytearray(19)
        response[17] = 2
        response.extend((2, 1))
        self.assertEqual(
            Command(1, spec).parse_response(response), {"enabled": 2, "available": 1}
        )

    def test_unsafe_aliases_are_removed_without_mutating_upstream(self):
        base = {"GenerateLoopSignalLegacy": {}, "GetSupportedAccessories": {}}
        self.assertEqual(len(base), 2)
        corrected = SETTINGS.corrected_protocol(base)
        self.assertEqual(len(base), 2)
        for name in base:
            self.assertNotIn(name, corrected)

    def test_sensitivity_labels_match_minimo_app_choices(self):
        tree = ast.parse((COMPONENT / "select.py").read_text())
        assignment = next(
            node
            for node in tree.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(t, ast.Name)
                and t.id == "SENSOR_CONTROL_SENSITIVITY_OPTIONS_BY_ID"
                for t in node.targets
            )
        )
        self.assertEqual(
            ast.literal_eval(assignment.value),
            {1: "Low", 2: "Medium", 3: "High"},
        )

    def test_minimo_distance_bounds_and_wire_scales(self):
        tree = ast.parse((COMPONENT / "number.py").read_text())
        for key, bounds in (
            ("DrivePastWire", (20, 35)),
            ("ReversingDistance", (60, 300)),
        ):
            descriptor = next(
                node
                for node in ast.walk(tree)
                if isinstance(node, ast.Call)
                and any(
                    kw.arg == "key"
                    and isinstance(kw.value, ast.Constant)
                    and kw.value.value == key
                    for kw in node.keywords
                )
            )
            values = {kw.arg: kw.value for kw in descriptor.keywords}
            self.assertEqual(
                tuple(
                    ast.literal_eval(values[name])
                    for name in ("native_min_value", "native_max_value")
                ),
                bounds,
            )
        scales = {
            node.targets[0].id: ast.literal_eval(node.value)
            for node in tree.body
            if isinstance(node, ast.Assign)
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id.endswith("_SCALE")
        }
        self.assertEqual(
            scales, {"DRIVE_PAST_WIRE_SCALE": 10, "REVERSING_DISTANCE_SCALE": 10}
        )

    async def test_generate_loop_does_not_send_unrelated_fallback(self):
        tree = ast.parse((COMPONENT / "button.py").read_text())
        descriptor = next(
            n
            for n in ast.walk(tree)
            if isinstance(n, ast.Call)
            and any(
                k.arg == "key"
                and isinstance(k.value, ast.Constant)
                and k.value.value == "generate_loop_signal"
                for k in n.keywords
            )
        )
        self.assertNotIn("fallback_commands", [k.arg for k in descriptor.keywords])
        for result in SETTINGS.UNSUPPORTED:
            entity = SimpleNamespace(
                entity_description=SimpleNamespace(
                    command="GenerateLoopSignal",
                    command_kwargs={},
                    fallback_commands=(),
                ),
                coordinator=SimpleNamespace(
                    mower=SimpleNamespace(
                        command_response=AsyncMock(return_value=(result, None))
                    )
                ),
            )
            press = method(
                "button.py",
                "GardenaMowerBleCommandButton",
                "_async_press_with_fallbacks",
                {"ResponseResult": ResponseResult},
            )
            self.assertEqual(await press(entity), result)
            entity.coordinator.mower.command_response.assert_awaited_once_with(
                "GenerateLoopSignal"
            )

    async def test_minimo_sensitivity_writes_and_rejects_unoffered_choices(self):
        setter = method(
            "select.py",
            "GardenaMowerBleSelect",
            "async_select_option",
            {"HomeAssistantError": ValueError},
        )
        entity = SimpleNamespace(
            entity_description=SimpleNamespace(
                key="SensorControlSensitivity",
                name="SensorControl Sensitivity",
                ids_by_option={"Low": 1, "Medium": 2, "High": 3},
                set_command="SetSensorControlSensitivity",
                value_parameter="sensitivity",
                starting_point_id=None,
            ),
            _async_setting_command_response=AsyncMock(),
            coordinator=SimpleNamespace(
                update_cached_data=Mock(),
                schedule_settings_refresh=Mock(),
            ),
        )
        for label, value in (("Low", 1), ("Medium", 2), ("High", 3)):
            await setter(entity, label)
            entity._async_setting_command_response.assert_awaited_with(
                "SetSensorControlSensitivity",
                human_name="SensorControl Sensitivity",
                sensitivity=value,
            )
            entity.coordinator.update_cached_data.assert_called_with(
                {"SensorControlSensitivity": value}
            )
        entity._async_setting_command_response.reset_mock()
        for label in ("Very low", "Very high", "unknown"):
            with self.assertRaises(ValueError):
                await setter(entity, label)
        entity._async_setting_command_response.assert_not_awaited()

    async def test_zone_poll_uses_availability_not_enabled_or_collision_bits(self):
        tree = ast.parse((COMPONENT / "coordinator.py").read_text())
        blocks = [
            n
            for n in ast.walk(tree)
            if isinstance(n, ast.If)
            and isinstance(n.test, ast.BoolOp)
            and any(
                isinstance(t, ast.Attribute) and t.attr == "_zone_protect_supported"
                for t in n.test.values
            )
        ]
        self.assertEqual(len(blocks), 1)
        wrapper = ast.parse(
            "async def poll(self):\n    data = {'garageSupported': True}\n    poll_diagnostics = True\n    return data\n"
        )
        wrapper.body[0].body[2:2] = blocks
        namespace = dict(vars(SETTINGS), LOGGER=logging.getLogger(__name__))
        exec(
            compile(ast.fix_missing_locations(wrapper), "coordinator.py", "exec"),
            namespace,
        )
        for result, value, expected, retryable in (
            (ResponseResult.OK, {"enabled": 0, "available": 1}, True, True),
            (ResponseResult.OK, {"enabled": 1, "available": 0}, False, True),
            (ResponseResult.OK, {"enabled": 1, "available": 3}, None, True),
            (ResponseResult.DEVICE_BUSY, None, None, True),
            (ResponseResult.INVALID_GROUP, None, None, False),
        ):
            coordinator = SimpleNamespace(
                _zone_protect_supported=True,
                mower=SimpleNamespace(
                    command_response=AsyncMock(return_value=(result, value))
                ),
            )
            data = await namespace["poll"](coordinator)
            self.assertIs(data["zoneProtectSupported"], expected)
            self.assertTrue(data["garageSupported"])
            self.assertNotIn("supportedAccessories", data)
            self.assertEqual(coordinator._zone_protect_supported, retryable)
            coordinator.mower.command_response.assert_awaited_once_with(
                "GetZoneProtectSettings", warn_on_error=False
            )
