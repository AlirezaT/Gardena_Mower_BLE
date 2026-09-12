"""Local mower timestamps are not UTC and ambiguous DST times stay unknown."""

import unittest
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import test_connection  # noqa: F401 - initialize integration test package
from gardena_connection_tests.timestamps import local_timestamp


class TimestampTests(unittest.TestCase):
    def test_seasonal_offsets_use_target_date(self):
        for month, offset in ((1, 1), (7, 2)):
            raw = int(datetime(2026, month, 15, 12, tzinfo=UTC).timestamp())
            value = local_timestamp(raw, ZoneInfo("Europe/Brussels"))
            self.assertEqual(value.hour, 12)
            self.assertEqual(value.utcoffset().total_seconds(), offset * 3600)

    def test_gap_and_fold_are_not_invented_instants(self):
        for month, day in ((3, 29), (10, 25)):
            raw = int(datetime(2026, month, day, 2, 30, tzinfo=UTC).timestamp())
            self.assertIsNone(local_timestamp(raw, ZoneInfo("Europe/Brussels")))

    def test_sentinel_missing_timezone_and_invalid_types(self):
        for value in (0, -1, 0xFFFFFFFF, None, True, "100"):
            self.assertIsNone(local_timestamp(value, UTC))
        self.assertIsNone(local_timestamp(100, None))
