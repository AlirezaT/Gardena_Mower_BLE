"""Known model labels and raw diagnostic timestamps must not imply guesses."""

import unittest
from test_model_capabilities import model
from gardena_connection_tests.presentation import describe_error, model_label


class PresentationTests(unittest.TestCase):
    def test_platform_error_title_and_unknown_code(self):
        self.assertEqual(describe_error(38, "P14"), "Connection to MCU lost")
        self.assertNotEqual(describe_error(38, "P005"), "Connection to MCU lost")
        self.assertEqual(describe_error(99999, "P14"), "Unknown error (99999)")
        self.assertEqual(describe_error(None), "Unknown error")

    def test_model_fallback_preserves_identity_without_inventing_capacity(self):
        self.assertEqual(
            model_label("SILENO Minimo 250", model(29)), "SILENO Minimo 250"
        )
        self.assertEqual(
            model_label("Unknown Model (34, 1)", model(34)), "P14 (type 34, variant 1)"
        )
        self.assertEqual(
            model_label("Unknown Model (99, 1)", model(99)), "Unknown Model (99, 1)"
        )
