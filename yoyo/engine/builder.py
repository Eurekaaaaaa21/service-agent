from pathlib import Path

from yoyo.chitchat.handler import ChitChatHandler
from yoyo.chitchat.responder import ChitChatResponder
from yoyo.clarify.clarify_responder import ClarifyResponder
from yoyo.engine.dialogue_engine import DialogueEngine
from yoyo.knowledge.handler import KnowledgeHandler
from yoyo.knowledge.intents import KNOWLEDGE_INTENTS
from yoyo.knowledge.providers import (
    APIBookingProvider,
    APILabListProvider,
    APILabProvider,
    FAQProvider,
    RAGProvider,
)
from yoyo.knowledge.registry import KnowledgeProviderRegistry
from yoyo.knowledge.responder import KnowledgeResponder
from yoyo.plan.turn_planner import TurnPlanner
from yoyo.plan.validator import TurnPlanValidator
from yoyo.task.action.builder import register_custom_actions
from yoyo.task.action.registry import ActionRegistry
from yoyo.task.action.runner import ActionRunner
from yoyo.task.command.processor import CommandProcessor
from yoyo.task.flow.conditions import ConditionEvaluator
from yoyo.task.flow.executor import FlowExecutor
from yoyo.task.flow.loader import FlowLoader
from yoyo.task.handler import TaskHandler
from yoyo.task.lifecycle.responder import TaskLifecycleResponder
from yoyo.task.response.renderer import ResponseRenderer


def build_dialogue_engine() -> DialogueEngine:
    flow_config_path = Path(__file__).parents[2] / 'flow_config' / 'user_flows.yml'
    flow_catalog = FlowLoader().load(flow_config_path)

    turn_planner = TurnPlanner()

    turn_plan_validator = TurnPlanValidator()

    command_processor = CommandProcessor()
    task_lifecycle_responder = TaskLifecycleResponder(flow_catalog)

    condition_evaluator = ConditionEvaluator()
    response_renderer = ResponseRenderer()
    registry = ActionRegistry()
    register_custom_actions(registry)
    action_runner = ActionRunner(registry=registry)
    flow_executor = FlowExecutor(
        condition_evaluator=condition_evaluator,
        response_renderer=response_renderer,
        action_runner=action_runner
    )
    task_handler = TaskHandler(
        command_processor=command_processor,
        task_lifecycle_responder=task_lifecycle_responder,
        flow_executor=flow_executor,
        flow_catalog=flow_catalog
    )

    provider_registry = KnowledgeProviderRegistry([
        APILabProvider(),
        APILabListProvider(),
        APIBookingProvider(),
        RAGProvider(),
        FAQProvider()
    ])
    knowledge_responder = KnowledgeResponder()
    knowledge_handler = KnowledgeHandler(
        knowledge_intents=KNOWLEDGE_INTENTS,
        provider_registry=provider_registry,
        knowledge_responder=knowledge_responder
    )

    chitchat_handler = ChitChatHandler(ChitChatResponder())

    clarify_responder = ClarifyResponder()
    return DialogueEngine(
        turn_planner=turn_planner,
        turn_plan_validator=turn_plan_validator,
        task_handler=task_handler,
        knowledge_handler=knowledge_handler,
        chitchat_handler=chitchat_handler,
        clarify_responder=clarify_responder
    )
