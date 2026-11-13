from yoyo.domain.state import DialogueState, TaskInstance
from yoyo.task.command.models import Command, StartFlowCommand, SetSlotsCommand, CancelTaskCommand, ResumeTaskCommand
from yoyo.task.flow.models import FlowCatalog, Flow
from yoyo.task.flow.steps import StartFlowStep
from yoyo.task.lifecycle.models import TaskEvent


class CommandProcessor:

    async def process(self, commands: list[Command], state: DialogueState, flow_catalog: FlowCatalog) -> list[
        TaskEvent]:
        events: list[TaskEvent] = []
        for command in commands:
            event = await self._apply(command, state, flow_catalog)
            if event:
                events.append(event)
        return events

    async def _apply(self, command: Command, state: DialogueState, flow_catalog: FlowCatalog) -> TaskEvent | None:
        if isinstance(command, StartFlowCommand):
            flow: Flow = flow_catalog.get_flow_by_id(command.flow)
            start_step: StartFlowStep = flow.get_start_step()

            task = TaskInstance(
                flow_id=command.flow,
                step_id=start_step.id
            )

            event: TaskEvent = state.task_state.start(task)
            return event

        if isinstance(command, SetSlotsCommand):
            state.task_state.active.slots.update(command.slots)
            return None

        if isinstance(command, CancelTaskCommand):
            event: TaskEvent = state.task_state.cancel(command.task_id)
            return event

        if isinstance(command, ResumeTaskCommand):
            event: TaskEvent = state.task_state.resume(command.task_id)
            return event
