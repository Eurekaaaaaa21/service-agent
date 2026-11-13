import json
from dataclasses import asdict
from datetime import datetime

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate

from yoyo.clients.llm_client import llm
from yoyo.domain.message import UserMessage
from yoyo.domain.state import DialogueState
from yoyo.knowledge.intents import KnowledgeIntent
from yoyo.plan.models import TurnPlan
from yoyo.prompts.history_builder import HistoryBuilder
from yoyo.prompts.loader import load_prompt
from yoyo.task.flow.models import FlowCatalog


class TurnPlanner:

    async def plan(self,
                   state: DialogueState,
                   user_message: UserMessage,
                   flow_catalog: FlowCatalog,
                   knowledge_intents: dict[str, KnowledgeIntent]) -> TurnPlan:
        # 准备一个chain
        prompt_text = load_prompt('turn_plan')
        prompt = PromptTemplate.from_template(prompt_text, template_format='jinja2')
        parser = JsonOutputParser()

        chain = prompt | llm | parser

        # 准备提示词变量
        user_message = HistoryBuilder.render_user_message(user_message)
        conversation_history = HistoryBuilder.build(state.shared_state.current_session().turns)
        focused_object_json = json.dumps(
            asdict(state.shared_state.focused_object) if state.shared_state.focused_object else None,
            ensure_ascii=False, indent=2)
        task_state_json = json.dumps(asdict(state.task_state), ensure_ascii=False, indent=2)
        knowledge_intents_json = json.dumps([{'id': intent.id, 'description': intent.description} for intent in
                                             knowledge_intents.values()], ensure_ascii=False, indent=2)
        flows = [{k: v for k, v in asdict(flow).items() if k != 'steps'} for flow in flow_catalog.flows.values()]

        result = await chain.ainvoke(input={
            'user_message': user_message,
            'conversation_history': conversation_history,
            'focused_object_json': focused_object_json,
            'task_state_json': task_state_json,
            'knowledge_intents_json': knowledge_intents_json,
            'flows_json': flows,
            'current_time': datetime.now().strftime('%Y-%m-%d %H:%M %A')
        })
        print('=' * 50)
        print(result)
        print('=' * 50)

        return TurnPlan.from_dict(result)
