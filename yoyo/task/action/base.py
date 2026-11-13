from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from yoyo.domain.state import DialogueState


@dataclass
class ActionResult:
    slot_updates: dict[str, Any] = field(default_factory=dict)


class Action(ABC):
    name: str

    @abstractmethod
    async def run(
            self,
            state: DialogueState,
            action_kwargs: dict[str, Any],
    ) -> ActionResult:
        pass
