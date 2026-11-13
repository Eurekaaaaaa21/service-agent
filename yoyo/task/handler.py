from yoyo.domain.message import UserMessage, BotMessage
from yoyo.domain.state import DialogueState
from yoyo.task.command.models import Command
from yoyo.task.command.processor import CommandProcessor
from yoyo.task.flow.executor import FlowExecutor
from yoyo.task.flow.models import FlowCatalog
from yoyo.task.lifecycle.models import TaskEvent
from yoyo.task.lifecycle.responder import TaskLifecycleResponder


class TaskHandler:

    def __init__(self,
                 command_processor: CommandProcessor,
                 task_lifecycle_responder: TaskLifecycleResponder,
                 flow_executor: FlowExecutor,
                 flow_catalog: FlowCatalog):
        self.command_processor = command_processor
        self.task_lifecycle_responder = task_lifecycle_responder
        self.flow_executor = flow_executor
        self.flow_catalog = flow_catalog

    async def handle(self, commands: list[Command], state: DialogueState, user_message: UserMessage) -> list[
        BotMessage]:
        task_events: list[TaskEvent] = await self.command_processor.process(commands, state, self.flow_catalog)
        messages: list[BotMessage] = await self.task_lifecycle_responder.respond(task_events)
        messages.extend(await self.flow_executor.run_task(state, self.flow_catalog, user_message))
        return messages
