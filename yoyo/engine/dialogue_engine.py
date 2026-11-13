import re
import time
import uuid
from dataclasses import asdict

from yoyo.chitchat.handler import ChitChatHandler
from yoyo.clarify.clarify_responder import ClarifyResponder
from yoyo.domain.message import UserMessage, ProcessResult, MessageType, BotMessage
from yoyo.domain.state import DialogueState, Turn, FocusedObject
from yoyo.knowledge.handler import KnowledgeHandler
from yoyo.plan.models import TurnPlan, TurnPlanValidationResult, ClarifyReason
from yoyo.plan.turn_planner import TurnPlanner
from yoyo.plan.validator import TurnPlanValidator
from yoyo.task.command.models import SetSlotsCommand, StartFlowCommand
from yoyo.task.flow.models import Flow
from yoyo.task.flow.steps import FlowStep, CollectSlotStep
from yoyo.task.handler import TaskHandler

# 业务对象类型 -> 对应可填充的 slot
SLOT_NAME_BY_OBJECT_TYPE = {
    'booking': 'booking_no',
    'lab': 'lab_code',
}

# 文本里出现的实验室编号 / 预约号，用于兜底纠正路由
LAB_CODE_PATTERN = re.compile(r'(LAB[-_\s]?\d{2,4})', re.IGNORECASE)
BOOKING_NO_PATTERN = re.compile(r'\b(B\d{11,13})\b', re.IGNORECASE)

# 对象类型 -> (兜底流程, 流程要收集的 slot)
FALLBACK_FLOW_BY_OBJECT_TYPE = {
    'lab': ('lab_info_query', 'lab_code'),
    'booking': ('booking_status_query', 'booking_no'),
}


class DialogueEngine:

    def __init__(self,
                 turn_planner: TurnPlanner,
                 turn_plan_validator: TurnPlanValidator,
                 task_handler: TaskHandler,
                 knowledge_handler: KnowledgeHandler,
                 chitchat_handler: ChitChatHandler,
                 clarify_responder: ClarifyResponder
                 ):
        self.turn_planner = turn_planner
        self.turn_plan_validator = turn_plan_validator
        self.task_handler = task_handler
        self.knowledge_handler = knowledge_handler
        self.chitchat_handler = chitchat_handler
        self.clarify_responder = clarify_responder

    async def process_message(self, state: DialogueState, user_message: UserMessage) -> ProcessResult:
        # 准备会话（Session）
        self._prepare_session(state)

        # 准备Turn
        turn = Turn(turn_id=str(uuid.uuid4()), user_message=user_message)

        if user_message.type == MessageType.TEXT:
            messages: list[BotMessage] = await self._handle_text_message(user_message, state)
        else:
            messages: list[BotMessage] = await self._handle_object_message(user_message, state)

        # 组装turn
        turn.bot_messages.extend(messages)

        # 将turn提交到current_session
        state.shared_state.current_session().turns.append(turn)

        # 返回结果
        return ProcessResult(
            sender_id=user_message.sender_id,
            message_id=user_message.message_id,
            messages=messages
        )

    def _prepare_session(self, state: DialogueState):
        now = time.time()
        if not state.shared_state.sessions:
            state.shared_state.start_session()
        else:
            if now - state.shared_state.current_session().last_activity_at > 60 * 60:
                state.shared_state.close_current_session()
                state.clear_context_for_new_session()
                state.shared_state.start_session()
            else:
                state.shared_state.current_session().last_activity_at = now

    async def _handle_text_message(self, user_message: UserMessage, state: DialogueState) -> list[BotMessage]:
        turn_plan: TurnPlan = await self.turn_planner.plan(state, user_message, self.task_handler.flow_catalog,
                                                           self.knowledge_handler.knowledge_intents)
        validation_result: TurnPlanValidationResult = self.turn_plan_validator.validate(turn_plan, state,
                                                                                        self.task_handler.flow_catalog,
                                                                                        self.knowledge_handler.knowledge_intents)
        if not validation_result.valid:
            # 用户文字里已经给了实验室编号 / 预约号，就别再让用户补对象，直接进对应流程
            if validation_result.reason is ClarifyReason.MISSING_FOCUSED_OBJECT:
                fallback_messages = await self._route_with_text_reference(user_message, state)
                if fallback_messages:
                    return fallback_messages
            return await self.clarify_responder.respond(validation_result.reason, state, user_message)

        if turn_plan.task:
            return await self.task_handler.handle(turn_plan.task.commands, state, user_message)

        if turn_plan.knowledge:
            return await self.knowledge_handler.handle(turn_plan.knowledge.intents, state, user_message)

        return await self.chitchat_handler.handle(user_message, state)

    async def _route_with_text_reference(self, user_message: UserMessage,
                                         state: DialogueState) -> list[BotMessage] | None:
        """从文本中识别预约号或实验室编号，直接按对应流程处理"""
        if not user_message.text:
            return None

        object_type = None
        object_id = None

        booking_match = BOOKING_NO_PATTERN.search(user_message.text)
        if booking_match:
            object_type, object_id = 'booking', booking_match.group(1).upper()
        else:
            lab_match = LAB_CODE_PATTERN.search(user_message.text)
            if lab_match:
                object_type, object_id = 'lab', lab_match.group(1).upper().replace('_', '-').replace(' ', '-')

        if object_type is None:
            return None

        flow_id, slot_name = FALLBACK_FLOW_BY_OBJECT_TYPE[object_type]
        state.shared_state.focused_object = FocusedObject(type=object_type, id=object_id)
        commands = [
            StartFlowCommand(command='start_flow', flow=flow_id),
            SetSlotsCommand(command='set_slots', slots={slot_name: object_id}),
        ]
        return await self.task_handler.handle(commands, state, user_message)

    async def _handle_object_message(self, user_message: UserMessage, state: DialogueState) -> list[BotMessage]:

        state.shared_state.focused_object = FocusedObject(**asdict(user_message.object))

        if self._can_fill_slot(state):
            # 用户发来的预约条 / 实验室正好是当前流程要收集的字段
            slot_name = SLOT_NAME_BY_OBJECT_TYPE[user_message.object.type]
            command = SetSlotsCommand(command='set_slots', slots={slot_name: user_message.object.id})
            return await self.task_handler.handle([command], state, user_message)

        if state.task_state.active is None:
            # 没有正在办理的业务时，直接按对象类型介绍预约条 / 实验室
            intent_id = 'lab_info' if user_message.object.type == 'lab' else 'booking_info'
            return await self.knowledge_handler.handle([intent_id], state, user_message)

        # clarify_responder
        return await self.clarify_responder.respond(ClarifyReason.OBJECT_REQUIRES_INTENT, state, user_message)

    def _can_fill_slot(self, state: DialogueState) -> bool:
        active_task = state.task_state.active
        if not active_task:
            return False

        flow: Flow = self.task_handler.flow_catalog.get_flow_by_id(active_task.flow_id)
        step: FlowStep = flow.get_step_by_id(active_task.step_id)

        if not isinstance(step, CollectSlotStep):
            return False

        focused_object = state.shared_state.focused_object
        if focused_object is None:
            return False

        return step.slot_name == SLOT_NAME_BY_OBJECT_TYPE.get(focused_object.type)
