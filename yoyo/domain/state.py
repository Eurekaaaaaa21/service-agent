import time
import uuid
from dataclasses import dataclass, field
from itertools import takewhile

from yoyo.domain.message import UserMessage, BotMessage
from yoyo.task.lifecycle.models import TaskEvent, TaskSwitched, TaskRef, TaskStarted, TaskCanceled, TaskResumed


@dataclass
class Turn:
    turn_id: str
    user_message: UserMessage
    bot_messages: list[BotMessage] = field(default_factory=list)


@dataclass
class Session:
    session_id: str
    started_at: float
    last_activity_at: float
    closed_at: float | None = None
    turns: list[Turn] = field(default_factory=list)


@dataclass
class FocusedObject:
    type: str  # "booking" 预约条 | "lab" 实验室
    id: str  # 对象的id：预约号 或 实验室编号
    title: str | None = None  # 对象的标题
    attributes: dict = field(default_factory=dict)  # 对象的属性


@dataclass
class SharedState:
    focused_object: FocusedObject | None = None
    sessions: list[Session] = field(default_factory=list)

    def current_session(self) -> Session:
        return self.sessions[-1]

    def start_session(self):
        now = time.time()
        session = Session(
            session_id=str(uuid.uuid4()),
            started_at=now,
            last_activity_at=now
        )
        self.sessions.append(session)

    def close_current_session(self):
        self.current_session().closed_at = time.time()


@dataclass
class TaskInstance:
    flow_id: str
    step_id: str | None
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    slots: dict = field(default_factory=dict)

    def to_ref(self) -> TaskRef:
        return TaskRef(self.task_id, self.flow_id)


@dataclass
class TaskState:
    active: TaskInstance | None = None
    paused: list[TaskInstance] = field(default_factory=list)

    def start(self, task: TaskInstance) -> TaskEvent:
        if self.active:
            previous = self.active.to_ref()
            self.paused.append(self.active)
            self.active = task
            current = self.active.to_ref()
            return TaskSwitched(previous=previous, current=current)
        else:
            self.active = task
            return TaskStarted(task=self.active.to_ref())

    def cancel(self, task_id: str) -> TaskEvent:
        if self.active.task_id == task_id:
            target_task = self.active.to_ref()
            self.active = None
            return TaskCanceled(task=target_task)
        else:
            for task in self.paused:
                if task.task_id == task_id:
                    target_task = task.to_ref()
                    self.paused.remove(task)
                    return TaskCanceled(task=target_task)
            raise ValueError(f"task {task_id} not found")

    def resume(self, task_id: str) -> TaskEvent:
        target_task_ref = None
        target_task = None
        for index, task in enumerate(self.paused):
            if task.task_id == task_id:
                target_task_ref = task.to_ref()
                target_task = self.paused.pop(index)
                break

        if target_task is None:
            raise ValueError(f"task {task_id} not found")

        if self.active:
            previous_task_ref = self.active.to_ref()
            self.paused.append(self.active)
            self.active = target_task
            return TaskSwitched(previous=previous_task_ref, current=target_task_ref)
        else:
            self.active = target_task
            return TaskResumed(task=target_task_ref)


@dataclass
class DialogueState:
    sender_id: str
    shared_state: SharedState = field(default_factory=SharedState)
    task_state: TaskState = field(default_factory=TaskState)

    def clear_context_for_new_session(self):
        self.shared_state.focused_object = None
        self.task_state.active = None
        self.task_state.paused.clear()
