"""Serialized, result-checked model-dependent actions."""

from automower_ble.protocol import ModeOfOperation, ResponseResult


class ActionMixin:
    async def _spot_cut_available(self):
        if self.capabilities.platform in ("P0", "P005"):
            return True
        if self.capabilities.platform not in ("P005GA", "P14"):
            return False
        result, available = await self.command_response(
            "GetSpotCutAvailable", warn_on_error=False
        )
        return (
            result is ResponseResult.OK
            and type(available) in (bool, int)
            and available == 1
        )

    async def mower_spot_cut(self):
        async with self.lock:
            if not await self._spot_cut_available():
                return ResponseResult.NOT_AVAILABLE
            if self.capabilities.platform == "P005":
                # Preserve the owner's physically tested Minimo command sequence.
                return await super().mower_spot_cut()
            commands = [("Pause", {}), ("SetMode", {"mode": ModeOfOperation.AUTO})]
            if self.capabilities.generation == 3:
                commands.extend(
                    [("SetOverrideMow", {"duration": 300}), ("StartSpotCutting", {})]
                )
            else:
                commands.append(("PrepareSpotCutting", {}))
            commands.append(("StartTrigger", {}))
            return await self._action_sequence(commands)

    async def mower_stop_spot_cut(self):
        async with self.lock:
            if not await self._spot_cut_available():
                return ResponseResult.NOT_AVAILABLE
            if self.capabilities.platform == "P005":
                return await super().mower_stop_spot_cut()
            command = (
                "StopSpotCutting"
                if self.capabilities.generation == 3
                else "AbortSpotCutting"
            )
            return await self._action_sequence([(command, {})])

    async def _action_sequence(self, commands):
        async with self.lock:
            for command, values in commands:
                result, _ = await self.command_response(command, **values)
                if result is not ResponseResult.OK:
                    return result
        return ResponseResult.OK

    async def mower_park_permanently(self):
        generation = self.capabilities.generation
        if generation not in (3, 4):
            return ResponseResult.NOT_AVAILABLE
        commands = [("SetMode", {"mode": ModeOfOperation.HOME})]
        if generation == 4:
            commands.append(("ClearOverride", {}))
        commands.append(("StartTrigger", {}))
        return await self._action_sequence(commands)

    async def mower_resume(self):
        return await self._action_sequence([("StartTrigger", {})])

    async def mower_resume_schedule(self):
        return await self._action_sequence(
            [
                ("ClearOverride", {}),
                ("SetMode", {"mode": ModeOfOperation.AUTO}),
            ]
        )
