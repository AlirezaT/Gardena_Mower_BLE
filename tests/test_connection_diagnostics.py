"""Exercise the HA diagnostic entry point without requiring a running HA server."""

import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock


class DiagnosticsTests(unittest.IsolatedAsyncioTestCase):
    async def test_diagnostics_never_export_config_or_source_identity(self):
        path = Path(__file__).parents[1] / "custom_components/gardena_mower_ble/diagnostics.py"
        tree = ast.parse(path.read_text())
        node = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef))
        redact = Mock(side_effect=lambda data, keys: {
            k: "**REDACTED**" if k in keys else v for k, v in data.items()
        })
        namespace = {"async_redact_data": redact}
        exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), namespace)
        diagnostic = namespace["async_get_config_entry_diagnostics"]
        mower = SimpleNamespace(
            connection_diagnostics={"source": "private source", "source_name": "private name", "outcome": "OK"},
            is_connected=lambda: True,
        )
        entry = SimpleNamespace(data={"pin": "secret"}, runtime_data=SimpleNamespace(mower=mower))
        result = await diagnostic(None, entry)
        self.assertEqual(result["connection"]["source"], "**REDACTED**")
        self.assertEqual(result["connection"]["source_name"], "**REDACTED**")
        self.assertTrue(result["connection"]["connected"])
        self.assertNotIn("secret", str(result))
        self.assertEqual(mower.connection_diagnostics["source"], "private source")
        self.assertEqual(await diagnostic(None, SimpleNamespace()), {"connection": {"outcome": "not_loaded"}})
