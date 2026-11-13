from yoyo.domain.message import BotMessage
from yoyo.task.lifecycle.models import (
    TaskCanceled,
    TaskEvent,
    TaskResumed,
    TaskStarted,
    TaskSwitched,
)
from yoyo.task.flow.models import FlowCatalog


class TaskLifecycleResponder:
    def __init__(self, flows: FlowCatalog) -> None:
        self.flows = flows

    async def respond(
            self,
            events: list[TaskEvent],
    ) -> list[BotMessage]:
        messages: list[BotMessage] = []
        for event in events:
            messages.append(self._message_for(event))
        return messages

    def _message_for(
            self,
            event: TaskEvent,
    ) -> BotMessage:
        if isinstance(event, TaskStarted):
            flow_name = self._flow_name(event.task.flow_id)
            return BotMessage(
                text=f"好的，我们先处理{flow_name}。"
            )

        if isinstance(event, TaskSwitched):
            previous_name = self._flow_name(
                event.previous.flow_id
            )
            current_name = self._flow_name(event.current.flow_id)
            return BotMessage(
                text=(
                    f"好的，我们先把{previous_name}放一放，"
                    f"先处理{current_name}。"
                )
            )

        if isinstance(event, TaskResumed):
            flow_name = self._flow_name(event.task.flow_id)
            return BotMessage(
                text=f"好的，我们继续刚才的{flow_name}。"
            )

        if isinstance(event, TaskCanceled):
            flow_name = self._flow_name(event.task.flow_id)
            return BotMessage(
                text=f"好的，{flow_name}先帮你取消。"
            )

        raise TypeError(
            f"Unsupported task event: {type(event).__name__}"
        )

    def _flow_name(self, flow_id: str) -> str:
        return self.flows.get_flow_by_id(flow_id).name
