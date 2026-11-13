from yoyo.domain.state import DialogueState
from yoyo.task.action.base import ActionResult
from yoyo.task.action.registry import ActionRegistry

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ActionCall:
    action_name: str
    action_kwargs: dict[str, Any] = field(
        default_factory=dict
    )


class ActionRunner:

    def __init__(self, registry: ActionRegistry):
        self.registry = registry

    async def run(self, action_call: ActionCall, state: DialogueState) -> ActionResult:
        action = self.registry.get(action_call.action_name)
        return await action.run(state, action_call.action_kwargs)
