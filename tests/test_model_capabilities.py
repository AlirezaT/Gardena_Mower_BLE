"""Model rules and HA setup/wire paths without actuating any mower."""

import ast
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from automower_ble.protocol import ResponseResult

from test_connection import Mower
from test_release_fixes import COMPONENT, method
from gardena_connection_tests.model_capabilities import identify_model
from gardena_connection_tests.settings_protocol import (
    corrected_protocol,
    read_frost_setting,
    read_starting_point,
)


def model(device_type, firmware="41.00.00"):
    return identify_model({"deviceType": device_type, "deviceVariant": 1}, firmware)


class ModelCapabilityTests(unittest.IsolatedAsyncioTestCase):
    def test_numeric_identity_and_variant(self):
        for device_type in (14, 18, 22, 25):
            self.assertEqual(
                (model(device_type).platform, model(device_type).generation), ("P0", 3)
            )
        for device_type in (29, 30):
            self.assertEqual(
                (model(device_type).platform, model(device_type).generation),
                ("P005", 4),
            )
        self.assertEqual(model(43).platform, "P005GA")
        for variant in (1, 2, 3, 9):
            caps = identify_model({"deviceType": 29, "deviceVariant": variant})
            self.assertEqual(caps.variant, variant)
            self.assertEqual(caps.sensitivity_ids, (1, 2, 3))

    def test_starting_point_distance_editor_bounds_and_write_guard(self):
        for device_type, maximum in ((14, 300), (29, 100), (43, 500), (34, 500)):
            caps = model(device_type)
            self.assertEqual(caps.point_distance_bounds, (1, maximum))
            for value in (1, maximum):
                caps.validate_setting(
                    "SetStartingPointDistance",
                    {"startingPointId": 1, "distance": value},
                )
            for value in (0, maximum + 1, True, 1.5):
                with self.assertRaises(ValueError):
                    caps.validate_setting(
                        "SetStartingPointDistance",
                        {"startingPointId": 1, "distance": value},
                    )

    def test_unknown_is_not_p14(self):
        for identity in (
            None,
            {},
            {"deviceType": "29", "deviceVariant": 1},
            {"deviceType": True, "deviceVariant": 1},
            {"deviceType": 47, "deviceVariant": 1},
            {"deviceType": 23, "deviceVariant": 1},
        ):
            caps = identify_model(identity)
            self.assertEqual(caps.platform, "unknown")
            self.assertEqual(caps.point_count, 0)
            self.assertFalse(caps.radar)
            self.assertIsNone(caps.drive_bounds)
            self.assertEqual(caps.sensitivity_ids, ())

    def test_p14_requires_verified_catalog_variant(self):
        for device_type, variants in {
            34: (1, 2, 4),
            35: (1, 2, 3, 7, 8, 9),
            36: (1,),
            37: (1, 2, 3),
        }.items():
            for variant in variants:
                caps = identify_model(
                    {"deviceType": device_type, "deviceVariant": variant}
                )
                self.assertEqual(caps.platform, "P14")
                self.assertEqual(caps.point_count, 5)
                self.assertEqual(caps.drive_bounds, (25, 40))
                self.assertTrue(caps.radar)
                self.assertFalse(caps.garage)
            self.assertEqual(
                identify_model(
                    {"deviceType": device_type, "deviceVariant": 255}
                ).platform,
                "unknown",
            )

    def test_ranges_points_and_guides(self):
        identity = {"deviceType": 34, "deviceVariant": 1}
        for brand, wires in (
            (None, ()),
            ("unknown", ()),
            ("gardena", (0, 1, 2, 3)),
            ("flymo", (0, 1, 2)),
        ):
            caps = identify_model(identity, brand=brand)
            self.assertEqual(caps.wire_ids, wires)
            for wire in range(5):
                if wire in wires:
                    caps.validate_setting(
                        "SetStartingPointWire", {"startingPointId": 1, "wire": wire}
                    )
                else:
                    with self.assertRaises(ValueError):
                        caps.validate_setting(
                            "SetStartingPointWire", {"startingPointId": 1, "wire": wire}
                        )
        self.assertEqual(
            identify_model(
                {"deviceType": 99, "deviceVariant": 1}, brand="gardena"
            ).wire_ids,
            (),
        )
        for device_type, count, drive, reverse, wires in (
            (14, 3, (20, 40), (20, 300), (2,)),
            (29, 3, (20, 35), (60, 300), (2,)),
            (43, 5, (20, 35), (60, 300), (2, 3)),
        ):
            caps = model(device_type)
            self.assertEqual(
                (
                    caps.point_count,
                    caps.drive_bounds,
                    caps.reversing_bounds,
                    caps.wire_ids,
                ),
                (count, drive, reverse, wires),
            )
        self.assertEqual(model(43).sensitivity_ids, (0, 1, 2, 3, 4))

    def test_firmware_boundaries(self):
        for version, frost, zone, corridor in (
            ("19.99", 5412, 6050, 26),
            ("20.28", 5412, 6050, 26),
            ("20.29", 5370, 6050, 26),
            ("40.99.00", 5370, 6050, 26),
            ("41.00.00", 5370, 5926, 24),
            ("42.00", 5370, 5926, 24),
        ):
            caps = model(14, version)
            self.assertEqual(
                (caps.frost_group, caps.zone_group, caps.corridor_read),
                (frost, zone, corridor),
            )
            overlay = corrected_protocol({}, caps)
            self.assertEqual(overlay["GetZoneProtectSettings"]["major"], zone)
            self.assertEqual(overlay["SetZoneProtectEnabled"]["major"], zone)
            self.assertEqual(overlay["GetStartingPointCorridorCut"]["minor"], corridor)
            self.assertEqual(
                overlay["SetStartingPointCorridorCut"]["minor"], corridor + 1
            )

    def test_unknown_firmware_does_not_guess_on_p0(self):
        for value in (None, "", "4", "41", "41.xx", "v41.00", "41.00 extra", 4100):
            caps = model(14, value)
            self.assertIsNone(caps.frost_group)
            self.assertIsNone(caps.zone_group)
            self.assertIsNone(caps.corridor_read)
            self.assertEqual(model(29, value).frost_group, 5370)
        self.assertIsNone(model(22).frost_group)

    def test_stale_entities_cannot_bypass_model_limits(self):
        caps = model(29)
        for command, kwargs in (
            ("SetSensorControlSensitivity", {"sensitivity": 0}),
            ("SetAntiCollisionRadarEnabled", {"enabled": True}),
            ("SetStartingPointWire", {"startingPointId": 1, "wire": 3}),
            ("SetStartingPointEnabled", {"startingPointId": 4, "enabled": True}),
            ("SetDrivePastWire", {"distance": 199}),
            ("SetDrivePastWire", {"distance": 351}),
            ("SetReversingDistance", {"distance": 3001}),
            ("SetFrostSensorV1Enabled", {"enabled": True}),
        ):
            with self.assertRaises(ValueError):
                caps.validate_setting(command, kwargs)
        for distance in (200, 350):
            caps.validate_setting("SetDrivePastWire", {"distance": distance})
        caps.validate_setting("SetZoneProtectEnabled", {"enabled": False})
        model(14).validate_setting(
            "SetStartingPointEnabled", {"startingPointId": 1, "enabled": True}
        )

    async def test_frost_only_reads_selected_group(self):
        for device_type, version, command in (
            (14, "20.28", "GetFrostSensorV1Enabled"),
            (14, "20.29", "GetFrostSensorEnabled"),
            (29, None, "GetFrostSensorEnabled"),
        ):
            mower = SimpleNamespace(
                capabilities=model(device_type, version),
                command_response=AsyncMock(return_value=(ResponseResult.OK, 1)),
            )
            result, value, setter = await read_frost_setting(mower)
            self.assertIs(result, ResponseResult.OK)
            self.assertTrue(value)
            self.assertEqual(setter, command.replace("Get", "Set", 1))
            mower.command_response.assert_awaited_once_with(
                command, warn_on_error=False
            )
        mower = SimpleNamespace(
            capabilities=model(14, None), command_response=AsyncMock()
        )
        self.assertEqual(
            await read_frost_setting(mower), (ResponseResult.NOT_AVAILABLE, None, None)
        )
        mower.command_response.assert_not_awaited()

    async def test_g3_individual_reads_and_g4_combined_reads(self):
        mower = SimpleNamespace(
            capabilities=model(14),
            command_response=AsyncMock(
                side_effect=[
                    (ResponseResult.OK, 1),
                    (ResponseResult.OK, 30),
                    (ResponseResult.OK, 17),
                    (ResponseResult.OK, 2),
                ]
            ),
        )
        result, value = await read_starting_point(mower, 2)
        self.assertIs(result, ResponseResult.OK)
        self.assertEqual(
            value, {"enabled": 1, "proportion": 30, "distance": 17, "wire": 2}
        )
        self.assertEqual(
            [call.args[0] for call in mower.command_response.await_args_list],
            [
                "GetStartingPointEnabled",
                "GetStartingPointProportion",
                "GetStartingPointDistance",
                "GetStartingPointWire",
            ],
        )
        mower.command_response = AsyncMock(
            return_value=(ResponseResult.DEVICE_BUSY, None)
        )
        self.assertEqual(
            await read_starting_point(mower, 2), (ResponseResult.DEVICE_BUSY, None)
        )
        mower.command_response.assert_awaited_once()
        mower.capabilities = model(43)
        mower.command_response = AsyncMock(return_value=(ResponseResult.OK, value))
        await read_starting_point(mower, 5)
        mower.command_response.assert_awaited_once_with(
            "GetStartingPoint", warn_on_error=False, startingPointId=5
        )

    def test_station_share_counts_all_five_points_and_unknown(self):
        calculate = method(
            "coordinator.py",
            "GardenaCoordinator",
            "_update_starting_point_charging_station_share",
            {"Any": object},
        )
        data = {"startingPointCount": 5}
        for point in range(1, 6):
            data[f"StartingPoint{point}Enabled"] = True
            data[f"StartingPoint{point}Proportion"] = 10
        calculate(data)
        self.assertEqual(data["StartingPointChargingStationProportion"], 50)
        data["StartingPoint5Enabled"] = None
        calculate(data)
        self.assertIsNone(data["StartingPointChargingStationProportion"])

    async def test_identity_setup_uses_reads_only_and_instance_overlay(self):
        mower = Mower(1, "00:00:00:00:00:00", 1234)
        base = {"GetZoneProtectSettings": {"major": 6050}}
        with (
            patch.object(
                mower,
                "command",
                AsyncMock(
                    side_effect=[{"deviceType": 14, "deviceVariant": 2}, "41.00.00"]
                ),
            ) as command,
            patch.object(mower, "get_protocol", AsyncMock(return_value=base)),
        ):
            await mower.initialize_capabilities()
        self.assertEqual(
            [call.args[0] for call in command.await_args_list],
            ["GetModel", "GetSwVersionStringAppl"],
        )
        self.assertEqual(mower.protocol["SetZoneProtectEnabled"]["major"], 5926)
        self.assertEqual(base, {"GetZoneProtectSettings": {"major": 6050}})

    async def test_select_setup_filters_real_descriptors(self):
        # Execute the actual setup function with lightweight HA stand-ins.
        tree = ast.parse((COMPONENT / "select.py").read_text())
        namespace = {
            "HomeAssistant": object,
            "GardenaConfigEntry": object,
            "AddConfigEntryEntitiesCallback": object,
        }
        for node in tree.body:
            if isinstance(node, ast.Assign):
                if any(
                    isinstance(t, ast.Name) and t.id == "DESCRIPTIONS"
                    for t in node.targets
                ):
                    continue
                exec(
                    compile(
                        ast.Module(body=[node], type_ignores=[]), "select.py", "exec"
                    ),
                    namespace,
                )
        namespace.update(
            GardenaMowerBleSelectEntityDescription=lambda **kw: SimpleNamespace(
                **({"starting_point_id": None} | kw)
            ),
            EntityCategory=SimpleNamespace(CONFIG="config"),
        )
        descriptors = next(
            node
            for node in tree.body
            if isinstance(node, ast.Assign)
            and any(
                isinstance(t, ast.Name) and t.id == "DESCRIPTIONS" for t in node.targets
            )
        )
        exec(
            compile(
                ast.Module(body=[descriptors], type_ignores=[]), "select.py", "exec"
            ),
            namespace,
        )
        namespace["GardenaMowerBleSelect"] = lambda coordinator, description: (
            description
        )
        namespace["replace"] = lambda obj, **kw: SimpleNamespace(**(vars(obj) | kw))
        setup = next(
            n
            for n in tree.body
            if isinstance(n, ast.AsyncFunctionDef) and n.name == "async_setup_entry"
        )
        exec(
            compile(ast.Module(body=[setup], type_ignores=[]), "select.py", "exec"),
            namespace,
        )
        for device_type, expected in (
            (29, ["Low", "Medium", "High"]),
            (43, ["Very low", "Low", "Medium", "High", "Very high"]),
            (99, []),
        ):
            created = []
            coordinator = SimpleNamespace(
                capabilities=model(device_type),
                data={
                    "SensorControlSensitivity": 3,
                    **{f"StartingPoint{point}Wire": 2 for point in range(1, 6)},
                },
            )
            await namespace["async_setup_entry"](
                None,
                SimpleNamespace(runtime_data=coordinator),
                lambda entities: created.extend(entities),
            )
            self.assertEqual(created[0].options if created else [], expected)
            self.assertEqual(
                len(created), model(device_type).point_count + bool(expected)
            )
            for description in created[1:]:
                self.assertEqual(
                    tuple(description.options_by_id), model(device_type).wire_ids
                )

    async def test_entity_write_guard_runs_before_ble_connection(self):
        write = method(
            "entity.py",
            "GardenaMowerBleDescriptorEntity",
            "_async_setting_command_response",
            {
                "ResponseResult": ResponseResult,
                "Any": object,
                "HomeAssistantError": ValueError,
                "WRITE_RETRY_ATTEMPTS": 2,
                "WRITE_RETRY_DELAY": 0,
            },
        )
        entity = SimpleNamespace(
            coordinator=SimpleNamespace(capabilities=model(29)),
            _async_ensure_connected=AsyncMock(),
        )
        with self.assertRaises(ValueError):
            await write(
                entity,
                "SetStartingPointWire",
                human_name="Wire",
                startingPointId=1,
                wire=3,
            )
        entity._async_ensure_connected.assert_not_awaited()
