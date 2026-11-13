import json
from dataclasses import asdict

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from yoyo.clients.llm_client import llm
from yoyo.domain.message import BotMessage, UserMessage
from yoyo.domain.state import DialogueState
from yoyo.plan.models import ClarifyReason
from yoyo.prompts.history_builder import HistoryBuilder
from yoyo.prompts.loader import load_prompt


class ClarifyResponder:

    async def respond(self, reason: ClarifyReason, state: DialogueState, user_message: UserMessage) -> list[BotMessage]:
        # 根据原因生成基础回复
        base_response = self.build_clarify_message(reason, state)

        # 使用LLM进行改写
        prompt_text = load_prompt("clarify_respond")
        prompt = PromptTemplate.from_template(
            prompt_text,
            template_format="jinja2",
        )
        chain = prompt | llm | StrOutputParser()

        focused_object = state.shared_state.focused_object

        result = await chain.ainvoke(input={
            'reason': reason.value,
            'clarify_message': base_response,
            'focused_object': json.dumps(asdict(focused_object), ensure_ascii=False, indent=2) if focused_object else '',
            'history': HistoryBuilder.build(state.shared_state.current_session().turns),
            'user_message': HistoryBuilder.render_user_message(user_message)
        })

        return [BotMessage(text=result)]

    def build_clarify_message(
            self,
            reason: ClarifyReason,
            state: DialogueState,
    ) -> str:
        if reason is ClarifyReason.MULTIPLE_TRACKS:
            return (
                "你这次同时提到了多个方向。我们先处理一个，"
                "你想先办业务还是先咨询信息呢？"
            )

        if reason is ClarifyReason.MISSING_FOCUSED_OBJECT:
            return "请先发送你想咨询的对象，我再继续帮你看。"

        if reason is ClarifyReason.MISSING_KNOWLEDGE_INTENT:
            return (
                "你是想了解实验室信息、预约条信息，"
                "还是预约规则和实验室使用规范呢？"
            )

        if reason is ClarifyReason.MISSING_TRACK:
            return "你是想先办理预约业务，还是先咨询信息呢？"

        if reason is ClarifyReason.MISSING_TASK_COMMANDS:
            return (
                "你这次是想办理什么业务呢？"
                "比如预约实验室、查预约状态、取消预约，或者查实验室信息。"
            )

        if reason is ClarifyReason.INVALID_TASK_COMMAND:
            return (
                "当前任务状态不支持这个操作，"
                "请告诉我你想开始、继续还是取消哪个任务。"
            )

        if reason is ClarifyReason.UNKNOWN_KNOWLEDGE_INTENT:
            return (
                "我暂时无法识别这个咨询方向，"
                "你可以具体说说想了解哪间实验室，或者哪条预约。"
            )

        if reason is ClarifyReason.OBJECT_REQUIRES_INTENT:
            focused_object = state.shared_state.focused_object
            if (
                    focused_object is not None
                    and focused_object.type == "booking"
            ):
                return (
                    "我已经收到这条预约了。你想查它的预约状态，"
                    "还是直接取消这条预约呢？"
                )
            if (
                    focused_object is not None
                    and focused_object.type == "lab"
            ):
                return (
                    "我已经收到这间实验室了。你想了解它的位置、"
                    "容纳人数和开放时间，还是直接预约它呢？"
                )

        return (
            "我还需要再确认一下你的意思，"
            "你可以换个更具体的说法告诉我。"
        )
