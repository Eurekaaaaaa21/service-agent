from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from yoyo.clients.llm_client import llm
from yoyo.domain.message import UserMessage, BotMessage
from yoyo.domain.state import Turn
from yoyo.prompts.history_builder import HistoryBuilder
from yoyo.prompts.loader import load_prompt


class ChitChatResponder:

    async def respond(self, user_message: UserMessage, turns: list[Turn]) -> BotMessage:
        prompt_text = load_prompt('chitchat_respond')
        prompt = PromptTemplate.from_template(prompt_text, template_format='jinja2')

        parser = StrOutputParser()

        chain = prompt | llm | parser

        result = await chain.ainvoke(input={
            'user_message': HistoryBuilder.render_user_message(user_message),
            'history': HistoryBuilder.build(turns)
        })

        return BotMessage(text=result)
