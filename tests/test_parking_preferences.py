"""Parking preferences are local, persistent and independent from mowing duration."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from test_connection import Mower  # noqa: F401 - establishes lightweight integration package
from test_release_fixes import method
from gardena_connection_tests import parking


class ParkingPreferenceTests(unittest.TestCase):
    def test_defaults_and_invalid_saved_values(self):
        self.assertEqual(parking.saved_parking({}), (parking.INDEFINITE, 3))
        self.assertEqual(parking.saved_parking({"parking_mode": "bad", "parking_duration_hours": True}), (parking.INDEFINITE, 3))
        self.assertEqual(parking.saved_parking({"parking_mode": parking.TIMED, "parking_duration_hours": 1.5}), (parking.TIMED, 1.5))

    def test_changes_persist_without_any_mower_object_or_command(self):
        entry = SimpleNamespace(options={"manual_mowing_duration_hours": 2, "other": "keep"})

        def update(target, *, options):
            target.options = options

        coordinator = SimpleNamespace(
            config_entry=entry, parking_mode=parking.INDEFINITE, parking_duration_hours=3,
            hass=SimpleNamespace(config_entries=SimpleNamespace(async_update_entry=update)),
            update_cached_data=Mock(),
        )
        setter = method("coordinator.py", "GardenaCoordinator", "set_parking_preference", vars(parking).copy())
        setter(coordinator, mode=parking.TIMED)
        setter(coordinator, duration=1.5)
        self.assertEqual(parking.saved_parking(entry.options), (parking.TIMED, 1.5))
        self.assertEqual(entry.options["manual_mowing_duration_hours"], 2)
        self.assertEqual(entry.options["other"], "keep")
        before = entry.options.copy()
        for value in (True, -1, 25, float("inf"), 0.6):
            with self.assertRaises(ValueError):
                setter(coordinator, duration=value)
            self.assertEqual(entry.options, before)
