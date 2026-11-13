from yoyo.domain.message import UserMessage, ProcessResult
from yoyo.domain.state import DialogueState, Session
from yoyo.engine.dialogue_engine import DialogueEngine
from yoyo.repository.dialogue_state_repository import DialogueStateRepository


class DialogueService:

    def __init__(self,
                 dialogue_state_repository: DialogueStateRepository,
                 dialogue_engine: DialogueEngine):
        self.dialogue_state_repository = dialogue_state_repository
        self.dialogue_engine = dialogue_engine

    async def process_message(self, user_message: UserMessage) -> ProcessResult:
        # 根据sender_id 获取对话状态
        state: DialogueState = await self.dialogue_state_repository.load_state(user_message.sender_id)

        # 将对话状态和最新消息交给DialogueEngine去处理
        process_result: ProcessResult = await self.dialogue_engine.process_message(state, user_message)

        # 保存最新的对话状态
        await self.dialogue_state_repository.save_state(state)

        # 返回处理结果
        return process_result

    async def get_sessions_by_id(self, sender_id: str) -> list[Session]:
        state: DialogueState = await self.dialogue_state_repository.load_state(sender_id=sender_id)
        return state.shared_state.sessions
