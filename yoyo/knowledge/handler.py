import asyncio

from yoyo.domain.message import UserMessage, BotMessage
from yoyo.domain.state import DialogueState
from yoyo.knowledge.intents import KnowledgeIntent
from yoyo.knowledge.providers import KnowledgeChunk
from yoyo.knowledge.registry import KnowledgeProviderRegistry
from yoyo.knowledge.responder import KnowledgeResponder


class KnowledgeHandler:

    def __init__(self,
                 knowledge_intents: dict[str, KnowledgeIntent],
                 provider_registry: KnowledgeProviderRegistry,
                 knowledge_responder: KnowledgeResponder):
        self.knowledge_intents = knowledge_intents
        self.provider_registry = provider_registry
        self.knowledge_responder = knowledge_responder

    async def handle(self, intents: list[str], state: DialogueState, user_message: UserMessage) -> list[BotMessage]:
        knowledge_intents: list[KnowledgeIntent] = [self.knowledge_intents[intent] for intent in intents]
        unique_provider_ids = set()
        for knowledge_intent in knowledge_intents:
            unique_provider_ids.update(knowledge_intent.provider_ids)

        provider_ids = list(unique_provider_ids)

        chunks_list = await asyncio.gather(
            *[self.provider_registry.get(provider_id).retrieve(user_message, state) for provider_id in provider_ids])

        chunks: list[KnowledgeChunk] = [chunk for chunks in chunks_list for chunk in chunks]

        bot_message = await self.knowledge_responder.respond(user_message, state.shared_state.current_session().turns,
                                                             chunks)
        return [bot_message]
