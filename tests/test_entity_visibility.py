"""Model visibility and registry migration, without live HA or mower writes."""

import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import test_connection  # noqa: F401 - load the isolated integration package
from gardena_connection_tests.model_capabilities import identify_model


def model(kind, brand=None, firmware=None):
    return identify_model({"deviceType": kind, "deviceVariant": 1}, firmware, brand)


class VisibilityTests(unittest.TestCase):
    def test_minimo_hides_radar_extra_points_and_guides(self):
        caps = model(29)
        for key in ("AntiCollisionRadarEnabled", "AntiCollisionRadarAvailable",
                    "StartingPoint4Enabled", "StartingPoint5Distance",
                    "StartingPoint4Wire", "guide2Signal", "guide3Signal"):
            self.assertTrue(caps.entity_is_model_excluded(key), key)
        for key in ("collision", "GarageEnabled", "garageSupported", "FrostSensorEnabled",
                    "ZoneProtectEnabled", "zoneProtectSupported", "spotCutting",
                    "StartingPoint3CorridorCut", "guide1Signal"):
            self.assertFalse(caps.entity_is_model_excluded(key), key)

    def test_other_models_and_unknown_evidence(self):
        for kind in (14, 18, 22, 25, 30, 43):
            self.assertTrue(model(kind).entity_is_model_excluded("AntiCollisionRadarEnabled"))
        self.assertFalse(model(43).entity_is_model_excluded("StartingPoint5Enabled"))
        self.assertFalse(model(43).entity_is_model_excluded("guide2Signal"))
        self.assertTrue(model(22).entity_is_model_excluded("FrostSensorEnabled"))
        self.assertFalse(model(14).entity_is_model_excluded("FrostSensorEnabled"))
        for brand in (None, "gardena", "flymo"):
            caps = model(34, brand)
            self.assertFalse(caps.entity_is_model_excluded("AntiCollisionRadarEnabled"))
            self.assertTrue(caps.entity_is_model_excluded("GarageEnabled"))
            self.assertEqual(caps.entity_is_model_excluded("guide2Signal"), brand == "flymo")
        for key in ("AntiCollisionRadarEnabled", "StartingPoint5Enabled", "guide3Signal"):
            self.assertFalse(model(999).entity_is_model_excluded(key))

    def test_registry_preserves_user_choices_and_only_changes_this_mower(self):
        path = Path(__file__).parents[1] / "custom_components/gardena_mower_ble/entity_visibility.py"
        tree = ast.parse(path.read_text())
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef))
        registry = Mock()
        def entity(name, hidden=None, prefix="test_1_", platform="gardena_mower_ble"):
            return SimpleNamespace(entity_id=name, unique_id=prefix+name,
                                   hidden_by=hidden, platform=platform)
        entries = [entity("AntiCollisionRadarEnabled"),
                   entity("AntiCollisionRadarAvailable", "user"),
                   entity("GarageEnabled", "integration"),
                   entity("guide2Signal", prefix="other_1_"),
                   entity("guide3Signal", platform="other")]
        er = SimpleNamespace(async_get=lambda hass: registry,
                             async_entries_for_config_entry=lambda registry, entry_id: entries,
                             RegistryEntryHider=SimpleNamespace(INTEGRATION="integration"))
        scope = {"er": er}
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), "exec"), scope)
        entry = SimpleNamespace(entry_id="entry", runtime_data=SimpleNamespace(
            address="test", channel_id=1, capabilities=model(29)))
        scope[function.name](None, entry)
        self.assertEqual(registry.async_update_entity.call_count, 2)
        registry.async_update_entity.assert_any_call("AntiCollisionRadarEnabled", hidden_by="integration")
        registry.async_update_entity.assert_any_call("GarageEnabled", hidden_by=None)
        registry.reset_mock()
        entry.runtime_data.capabilities = model(999)
        scope[function.name](None, entry)
        registry.async_update_entity.assert_not_called()
