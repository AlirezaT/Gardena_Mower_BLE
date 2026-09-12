"""Brand confirmation preserves duration preferences and does not guess identities."""

import ast
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from test_release_fixes import COMPONENT, method


class OptionsTests(unittest.IsolatedAsyncioTestCase):
    async def test_save_preserves_other_options(self):
        save = method(
            "config_flow.py", "GardenaModelOptionsFlow", "async_step_init", {}
        )
        flow = SimpleNamespace(
            current_entry=SimpleNamespace(options={"manual_mowing_duration": 6.5}),
            async_create_entry=Mock(),
        )
        await save(flow, {"mower_brand": "gardena"})
        flow.async_create_entry.assert_called_once_with(
            title="", data={"manual_mowing_duration": 6.5, "mower_brand": "gardena"}
        )
        with self.assertRaises(ValueError):
            await save(flow, {"mower_brand": "invented"})

    async def test_only_brand_change_reloads(self):
        tree = ast.parse((COMPONENT / "__init__.py").read_text())
        node = next(
            n
            for n in tree.body
            if isinstance(n, ast.AsyncFunctionDef)
            and n.name == "_async_options_updated"
        )
        scope = {"HomeAssistant": object, "GardenaConfigEntry": object}
        exec(
            compile(ast.Module(body=[node], type_ignores=[]), "__init__.py", "exec"),
            scope,
        )
        reload = AsyncMock()
        hass = SimpleNamespace(config_entries=SimpleNamespace(async_reload=reload))
        entry = SimpleNamespace(
            entry_id="test",
            options={"mower_brand": "unknown", "duration": 5},
            runtime_data=SimpleNamespace(
                mower=SimpleNamespace(capabilities=SimpleNamespace(brand=None))
            ),
        )
        await scope["_async_options_updated"](hass, entry)
        reload.assert_not_awaited()
        entry.options["mower_brand"] = "flymo"
        await scope["_async_options_updated"](hass, entry)
        reload.assert_awaited_once_with("test")
