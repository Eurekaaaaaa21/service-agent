from jinja2 import Template
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from yoyo.clients.llm_client import llm
from yoyo.domain.message import UserMessage, BotMessage, MessageObject
from yoyo.domain.state import DialogueState
from yoyo.prompts.history_builder import HistoryBuilder
from yoyo.task.response.models import ResponseTemplate, ResponseMode


class ResponseRenderer:

    async def render(self, template: ResponseTemplate, state: DialogueState, user_message: UserMessage) -> BotMessage:
        slots = state.task_state.active.slots if state.task_state.active else {}
        message_object = self._render_object(template.object, slots)

        if template.mode == ResponseMode.STATIC:
            rendered_text = Template(template.text).render(slots=slots)
            return BotMessage(text=rendered_text, object=message_object)

        if template.mode == ResponseMode.REPHRASE:
            rendered_text = Template(template.text).render(slots=slots)

            prompt = PromptTemplate.from_template(template.prompt, template_format='jinja2')

            parser = StrOutputParser()

            chain = prompt | llm | parser

            response = await chain.ainvoke({
                'history': HistoryBuilder.build(state.shared_state.current_session().turns),
                'user_message': HistoryBuilder.render_user_message(user_message),
                'current_response': rendered_text
            })
            return BotMessage(text=response, object=message_object)

        if template.mode == ResponseMode.GENERATE:
            prompt = PromptTemplate.from_template(template.prompt, template_format='jinja2')

            parser = StrOutputParser()

            chain = prompt | llm | parser

            response = await chain.ainvoke({
                'history': HistoryBuilder.build(state.shared_state.current_session().turns),
                'user_message': HistoryBuilder.render_user_message(user_message)
            })
            return BotMessage(text=response, object=message_object)

    def _render_object(self, object_config: dict | None, slots: dict) -> MessageObject | None:
        """把模板里声明的业务对象渲染成消息对象（预约条 / 实验室）"""
        if not object_config:
            return None

        def render_value(value):
            if isinstance(value, str):
                return Template(value).render(slots=slots).strip()
            return value

        attributes = {
            key: render_value(value)
            for key, value in (object_config.get('attributes') or {}).items()
        }

        title = object_config.get('title')

        return MessageObject(
            type=str(object_config.get('type', '')),
            id=render_value(object_config.get('id', '')),
            title=render_value(title) if title else None,
            attributes=attributes
        )
