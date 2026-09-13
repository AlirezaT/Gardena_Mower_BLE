"""Human guidance remains separate from control commands."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo
import unittest

from test_model_capabilities import model
from gardena_connection_tests.error_help import TITLES, HELP, error_guidance, error_title
from gardena_connection_tests.model_capabilities import identify_model
from gardena_connection_tests.presentation import describe_error, model_label
from gardena_connection_tests.timestamps import message_time_attributes


class ErrorHelpTests(unittest.TestCase):
    def test_catalog_and_all_profiles(self):
        self.assertEqual(len(TITLES), 97)
        for kind in (14, 18, 22, 25, 29, 30, 43, 34, 35, 36, 37):
            caps = model(kind)
            for code in TITLES.keys() | HELP.keys():
                with self.subTest(kind=kind, code=code):
                    self.assertTrue(describe_error(code, caps.platform, caps))
                    self.assertTrue(error_guidance(code, caps))
                    self.assertLess(len(' '.join(error_guidance(code, caps))), 1800)
        self.assertEqual(error_guidance(0, model(29)), ())
        self.assertEqual(error_guidance(None, model(29)), ())
        self.assertIn('unrecognised', error_guidance(2, model(999))[0])

    def test_acknowledgement_and_local_safety_are_generation_specific(self):
        self.assertIn('acknowledge', error_guidance(9, model(14))[-1])
        self.assertIn('STOP', error_guidance(9, model(29))[-1])
        self.assertEqual(len(error_guidance(12, model(14))), 2)
        self.assertEqual(len(error_guidance(12, model(29))), 3)
        self.assertIn('symbol sequence', error_guidance(1000001, model(29))[0])
        self.assertIn('Play', error_guidance(1000002, model(14))[0])
        self.assertNotIn('Play', error_guidance(1000002, model(29))[0])
        self.assertIn('stop using', ' '.join(error_guidance(127, model(29))).lower())

    def test_guides_and_family_labels_do_not_guess_brand_or_capacity(self):
        unknown = model(34)
        gardena = identify_model({'deviceType': 34, 'deviceVariant': 1}, '41.00', 'gardena')
        flymo = identify_model({'deviceType': 34, 'deviceVariant': 1}, '41.00', 'flymo')
        self.assertEqual(error_title(51, unknown), 'Guide wire not found')
        self.assertEqual(error_title(51, gardena), 'Guide wire 2 not found')
        self.assertEqual(error_title(51, flymo), 'Guide wire not found')
        self.assertEqual(model_label('Unknown Model', gardena), 'SILENO pro (type 34, variant 1)')
        self.assertEqual(model_label('Unknown Model', unknown), 'P14 (type 34, variant 1)')
        self.assertEqual(model_label('Unknown Model', model(29)), 'SILENO minimo (type 29, variant 1)')
        self.assertEqual(model_label('Known model 250', gardena), 'Known model 250')

    def test_message_display_matches_apps_separate_date_and_time_paths(self):
        value = int(datetime(2026, 9, 12, 23, 30, tzinfo=UTC).timestamp())
        result = message_time_attributes(value, ZoneInfo('Europe/Brussels'))
        self.assertEqual(result['app_date'], '2026-09-13')
        self.assertEqual(result['app_time_24h'], '23:30')
        self.assertIn('unverified', result['clock_semantics'])
        for invalid in (None, 0, -1, True, 0xFFFFFFFF, '1'):
            self.assertNotIn('app_date', message_time_attributes(invalid, ZoneInfo('UTC')))
        self.assertNotIn('app_date', message_time_attributes(value, None))
