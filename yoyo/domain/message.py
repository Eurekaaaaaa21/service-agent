from dataclasses import dataclass, field
from enum import Enum


@dataclass
class MessageObject:
    type: str
    id: str
    title: str | None = None
    attributes: dict = field(default_factory=dict)


class MessageType(Enum):
    TEXT = "text"
    OBJECT = "object"


@dataclass
class UserMessage:
    sender_id: str
    message_id: str
    type: MessageType
    text: str | None = None
    object: MessageObject | None = None


@dataclass
class BotMessage:
    text: str | None = None
    object: MessageObject | None = None


@dataclass
class ProcessResult:
    sender_id: str
    message_id: str
    messages: list[BotMessage]
