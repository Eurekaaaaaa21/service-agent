from dataclasses import dataclass
from typing import Any


@dataclass
class Command:
    command: str

    @classmethod
    def from_dict(cls, command_data: dict) -> "Command":
        clz = COMMAND_TO_CLASS[command_data['command']]
        return clz(**command_data)


@dataclass
class StartFlowCommand(Command):
    flow: str


@dataclass
class SetSlotsCommand(Command):
    slots: dict[str, Any]


@dataclass
class CancelTaskCommand(Command):
    task_id: str


@dataclass
class ResumeTaskCommand(Command):
    task_id: str


COMMAND_TO_CLASS = {
    'start_flow': StartFlowCommand,
    'set_slots': SetSlotsCommand,
    'cancel_task': CancelTaskCommand,
    'resume_task': ResumeTaskCommand
}

if __name__ == '__main__':
    commands = [
        {"command": "start_flow", "flow": "booking_status_query"},
        {"command": "set_slots", "slots": {"booking_no": "B20261114001"}}
    ]
    print([Command.from_dict(command) for command in commands])