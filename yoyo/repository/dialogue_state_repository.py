import asyncio

from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from yoyo.clients import database_client
from yoyo.clients.database_client import init_database, close_database
from yoyo.domain.state import DialogueState
from yoyo.models.dialogue_state import DialogueStateRecord

DIALOGUE_STATE_ADAPTER = TypeAdapter(DialogueState)


class DialogueStateRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def load_state(self, sender_id: str) -> DialogueState:
        sql = select(DialogueStateRecord).where(DialogueStateRecord.sender_id == sender_id)
        result = await self.session.execute(sql)
        record = result.scalar_one_or_none()
        if record:
            state = DIALOGUE_STATE_ADAPTER.validate_json(record.state_json)
            return state
        else:
            return DialogueState(sender_id=sender_id)

    async def save_state(self, state: DialogueState):
        state_json = DIALOGUE_STATE_ADAPTER.dump_json(state).decode(encoding="utf-8")
        insert_stmt = insert(DialogueStateRecord).values(
            sender_id=state.sender_id, state_json=state_json
        )
        on_duplicate_key_stmt = insert_stmt.on_duplicate_key_update(
            state_json=state_json
        )
        await self.session.execute(on_duplicate_key_stmt)
        await self.session.commit()


if __name__ == '__main__':
    init_database()


    async def test():
        async with database_client.session_factory() as session:
            repository = DialogueStateRepository(session)
            # await repository.save_state(DialogueState(sender_id="1"))

            state = await repository.load_state(sender_id='1')
            print(state)

        await close_database()


    asyncio.run(test())
