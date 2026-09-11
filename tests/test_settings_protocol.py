"""App-verified mappings, module selection and actual HA switch commands."""

import ast
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from automower_ble.protocol import BLEClient, Command, ResponseResult

from test_connection import Mower
from test_release_fixes import COMPONENT, method
from gardena_connection_tests.settings_protocol import (
    UNSUPPORTED,
    corrected_protocol,
    read_frost_setting,
    setting_bool,
)


class SettingsTests(unittest.IsolatedAsyncioTestCase):
    async def poll_settings(self, responses):
        """Execute the real coordinator's two setting-poll blocks."""
        tree = ast.parse((COMPONENT / "coordinator.py").read_text())
        blocks = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.If)
            and isinstance(node.test, ast.BoolOp)
            and any(
                isinstance(term, ast.Attribute)
                and term.attr in ("_frost_sensor_supported", "_eco_mode_supported")
                for term in node.test.values
            )
        ]
        self.assertEqual(len(blocks), 2)
        wrapper = ast.parse(
            "async def poll(self):\n    data = {}\n    poll_settings = True\n    return data\n"
        )
        wrapper.body[0].body[2:2] = blocks
        namespace = {
            "ResponseResult": ResponseResult,
            "UNSUPPORTED": UNSUPPORTED,
            "read_frost_setting": read_frost_setting,
            "setting_bool": setting_bool,
        }
        exec(
            compile(ast.fix_missing_locations(wrapper), "coordinator.py", "exec"),
            namespace,
        )
        coordinator = SimpleNamespace(
            _frost_sensor_supported=True,
            _eco_mode_supported=True,
            mower=SimpleNamespace(command_response=AsyncMock(side_effect=responses)),
        )
        return await namespace["poll"](coordinator), coordinator

    async def test_actual_polling_keeps_eco_and_frost_independent(self):
        for frost, eco in ((0, 1), (1, 0), (0, 0), (1, 1)):
            data, coordinator = await self.poll_settings(
                [(ResponseResult.OK, frost), (ResponseResult.OK, eco)]
            )
            self.assertEqual(data["EcoMode"], bool(eco))
            self.assertEqual(data["FrostSensorEnabled"], bool(frost))
            self.assertEqual(data["FrostSensorSetCommand"], "SetFrostSensorEnabled")
            self.assertNotIn("ChargingStationLoopSignalGeneration", data)
            self.assertEqual(
                [
                    call.args[0]
                    for call in coordinator.mower.command_response.await_args_list
                ],
                ["GetFrostSensorEnabled", "GetEcoModeEnabled"],
            )

    async def test_actual_polling_keeps_transient_errors_retryable(self):
        data, coordinator = await self.poll_settings(
            [(ResponseResult.UNKNOWN_ERROR, None)] * 2
        )
        self.assertIsNone(data["EcoMode"])
        self.assertIsNone(data["FrostSensorEnabled"])
        self.assertIsNone(data["FrostSensorSetCommand"])
        self.assertTrue(coordinator._frost_sensor_supported)
        self.assertTrue(coordinator._eco_mode_supported)

    async def test_overlay_is_instance_local_and_keeps_other_commands(self):
        base = {"Other": {"major": 42}, "GetFrostSensorEnabledLegacy": {"major": 4476}}
        mower = Mower(1, "00:00:00:00:00:00")
        with patch.object(BLEClient, "get_protocol", AsyncMock(return_value=base)):
            result = await mower.get_protocol()
        self.assertNotIn("GetEcoModeEnabled", base)
        self.assertEqual(result["Other"], base["Other"])
        self.assertNotIn("GetFrostSensorEnabledLegacy", result)

    async def test_wire_requests_use_verified_ids_and_uninverted_values(self):
        protocol = corrected_protocol({})
        for name, major, minor in (
            ("EcoMode", 4692, 5),
            ("FrostSensor", 5370, 2),
            ("FrostSensorV1", 5412, 2),
        ):
            for enabled in (False, True):
                request = Command(1, protocol[f"Set{name}Enabled"]).generate_request(
                    enabled=enabled
                )
                # HCP command identity and Boolean payload, before CRC/ETX.
                self.assertEqual(request[12:14], major.to_bytes(2, "little"))
                self.assertEqual(request[14:16], minor.to_bytes(2, "little"))
                self.assertEqual(request[-3], int(enabled))

    async def test_new_module_read_selects_matching_setter(self):
        mower = SimpleNamespace(
            command_response=AsyncMock(return_value=(ResponseResult.OK, 0))
        )
        self.assertEqual(
            await read_frost_setting(mower),
            (ResponseResult.OK, False, "SetFrostSensorEnabled"),
        )
        mower.command_response.assert_awaited_once_with(
            "GetFrostSensorEnabled", warn_on_error=False
        )

    async def test_unsupported_new_module_falls_back_to_5412_read_only(self):
        mower = SimpleNamespace(
            command_response=AsyncMock(
                side_effect=[
                    (ResponseResult.INVALID_GROUP, None),
                    (ResponseResult.OK, 1),
                ]
            )
        )
        self.assertEqual(
            await read_frost_setting(mower),
            (ResponseResult.OK, True, "SetFrostSensorV1Enabled"),
        )
        self.assertEqual(
            [call.args[0] for call in mower.command_response.await_args_list],
            ["GetFrostSensorEnabled", "GetFrostSensorV1Enabled"],
        )

    async def test_transient_or_auth_failure_does_not_select_another_module(self):
        for result in (
            ResponseResult.UNKNOWN_ERROR,
            ResponseResult.DEVICE_BUSY,
            ResponseResult.INVALID_PIN,
            ResponseResult.NOT_ALLOWED,
        ):
            mower = SimpleNamespace(
                command_response=AsyncMock(return_value=(result, None))
            )
            self.assertEqual(await read_frost_setting(mower), (result, None, None))
            self.assertEqual(mower.command_response.await_count, 1)

    async def test_both_modules_unsupported_do_not_offer_a_setter(self):
        mower = SimpleNamespace(
            command_response=AsyncMock(
                return_value=(ResponseResult.NOT_AVAILABLE, None)
            )
        )
        self.assertEqual(
            await read_frost_setting(mower), (ResponseResult.NOT_AVAILABLE, None, None)
        )

    async def test_invalid_boolean_is_not_mistaken_for_enabled(self):
        for value in (None, "1", {}, 2, -1, 1.0):
            self.assertIsNone(setting_bool(value))
            mower = SimpleNamespace(
                command_response=AsyncMock(return_value=(ResponseResult.OK, value))
            )
            self.assertEqual(
                await read_frost_setting(mower),
                (ResponseResult.UNKNOWN_ERROR, None, None),
            )
        for value in (0, 1, False, True):
            self.assertEqual(setting_bool(value), bool(value))

    def switch(self, key, setter=None):
        tree = ast.parse((COMPONENT / "switch.py").read_text())
        call = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "GardenaMowerBleSwitchEntityDescription"
            and any(
                k.arg == "key"
                and isinstance(k.value, ast.Constant)
                and k.value.value == key
                for k in node.keywords
            )
        )
        fields = {
            k.arg: ast.literal_eval(k.value)
            for k in call.keywords
            if isinstance(k.value, ast.Constant)
        }
        description = SimpleNamespace(
            **({"invert_value": False, "starting_point_id": None} | fields)
        )
        return SimpleNamespace(
            entity_description=description,
            coordinator=SimpleNamespace(
                data={"FrostSensorSetCommand": setter},
                update_cached_data=Mock(),
                schedule_settings_refresh=Mock(),
            ),
            _async_setting_command_response=AsyncMock(),
        )

    async def set_switch(self, entity, enabled):
        setter = method(
            "switch.py",
            "GardenaMowerBleSwitch",
            "_async_set_enabled",
            {"HomeAssistantError": RuntimeError},
        )
        await setter(entity, enabled)

    async def test_eco_switch_sends_same_boolean_and_preserves_entity_key(self):
        for enabled in (False, True):
            entity = self.switch("EcoMode")
            await self.set_switch(entity, enabled)
            entity._async_setting_command_response.assert_awaited_once_with(
                "SetEcoModeEnabled", human_name="Eco Mode", enabled=enabled
            )
            self.assertEqual(
                entity.coordinator.update_cached_data.call_args.args[0],
                {"EcoMode": enabled},
            )

    async def test_frost_switch_uses_selected_module_without_inversion(self):
        for command in ("SetFrostSensorEnabled", "SetFrostSensorV1Enabled"):
            for enabled in (False, True):
                entity = self.switch("FrostSensorEnabled", command)
                await self.set_switch(entity, enabled)
                entity._async_setting_command_response.assert_awaited_once_with(
                    command, human_name="Frost Sensor", enabled=enabled
                )

    async def test_unconfirmed_or_unsafe_frost_setter_never_writes(self):
        for command in (None, "SetFrostSensorEnabledLegacy", "SetEcoModeEnabled"):
            entity = self.switch("FrostSensorEnabled", command)
            with self.assertRaises(RuntimeError):
                await self.set_switch(entity, True)
            entity._async_setting_command_response.assert_not_called()

    async def test_failed_write_does_not_update_optimistic_state(self):
        entity = self.switch("EcoMode")
        entity._async_setting_command_response.side_effect = RuntimeError(
            "write rejected"
        )
        with self.assertRaises(RuntimeError):
            await self.set_switch(entity, True)
        entity.coordinator.update_cached_data.assert_not_called()
