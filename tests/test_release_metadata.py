"""Validate versions with the same strategies used by Home Assistant's loader."""

import json
import os
from pathlib import Path
import unittest

from awesomeversion import (
    AwesomeVersion,
    AwesomeVersionException,
    AwesomeVersionStrategy,
)

STRATEGIES = [
    AwesomeVersionStrategy.CALVER,
    AwesomeVersionStrategy.SEMVER,
    AwesomeVersionStrategy.SIMPLEVER,
    AwesomeVersionStrategy.BUILDVER,
    AwesomeVersionStrategy.PEP440,
]


class ReleaseMetadataTests(unittest.TestCase):
    def test_manifest_is_accepted_by_ha(self):
        manifest = json.loads(
            (
                Path(__file__).parents[1]
                / "custom_components/gardena_mower_ble/manifest.json"
            ).read_text()
        )
        version = manifest["version"]
        AwesomeVersion(version, ensure_strategy=STRATEGIES)
        tag = os.environ.get("GARDENA_RELEASE_TAG")
        if tag:
            self.assertEqual(tag.removeprefix("v"), version)

    def test_reject_previous_broken_beta_notation(self):
        for version in ("3.09b1", "3.09-beta.2"):
            with self.assertRaises(AwesomeVersionException):
                AwesomeVersion(version, ensure_strategy=STRATEGIES)
