import uuid
from dataclasses import asdict

from fastapi import APIRouter, HTTPException
from fastapi.params import Depends

from yoyo.app.dependencies import get_dialogue_service, get_lab_booking_repository
from yoyo.app.schemas import ChatRequest, ChatResponse, ChatMessage, HistoryResponse, HistoryMessage, ChatObject
from yoyo.domain.message import UserMessage, ProcessResult, MessageType, MessageObject
from yoyo.repository.lab_booking_repository import LabBookingRepository
from yoyo.service.dialogue_service import DialogueService

chat_router = APIRouter()


@chat_router.post("/api/chat")
async def chat(chat_request: ChatRequest,
               dialogue_service: DialogueService = Depends(get_dialogue_service)) -> ChatResponse:
    process_result = await dialogue_service.process_message(_build_user_message(chat_request))
    return _build_chat_response(process_result)


@chat_router.get("/api/labs")
async def labs(status: str | None = None,
               repository: LabBookingRepository = Depends(get_lab_booking_repository)) -> list[ChatObject]:
    """实验室列表，供前端渲染实验室卡片；status 可传 可预约/已满/维护中"""
    return [ChatObject(**repository.to_lab_object(lab)) for lab in await repository.list_labs(status)]


@chat_router.get("/api/labs/{lab_code}")
async def lab_detail(lab_code: str,
                     repository: LabBookingRepository = Depends(get_lab_booking_repository)) -> ChatObject:
    """单个实验室详情"""
    lab = await repository.get_lab(lab_code)
    if lab is None:
        raise HTTPException(status_code=404, detail=f"没有编号为 {lab_code} 的实验室")
    return ChatObject(**repository.to_lab_object(lab))


@chat_router.get("/api/users/{student_no}/bookings")
async def user_bookings(student_no: str,
                        repository: LabBookingRepository = Depends(get_lab_booking_repository)) -> list[ChatObject]:
    """某个学号的预约条列表，供前端展示「我的预约」"""
    bookings = await repository.list_bookings_by_student(student_no)
    return [ChatObject(**repository.to_booking_object(booking)) for booking in bookings]


@chat_router.get("/api/chat/history")
async def history(sender_id: str, dialogue_service: DialogueService = Depends(get_dialogue_service)) -> HistoryResponse:
    sessions = await dialogue_service.get_sessions_by_id(sender_id)

    messages: list[HistoryMessage] = []
    for session in sessions:
        for turn in session.turns:
            messages.append(
                HistoryMessage(role='user',
                               text=turn.user_message.text,
                               object=ChatObject(
                                   **asdict(turn.user_message.object)) if turn.user_message.object else None
                               )
            )

            messages.extend([HistoryMessage(role='bot', text=bot_message.text,
                                            object=ChatObject(
                                                **asdict(bot_message.object)) if bot_message.object else None)
                             for bot_message in
                             turn.bot_messages])

    return HistoryResponse(sender_id=sender_id, messages=messages)


def _build_user_message(chat_request: ChatRequest) -> UserMessage:
    return UserMessage(
        sender_id=chat_request.sender_id,
        message_id=chat_request.message_id if chat_request.message_id else str(uuid.uuid4()),
        type=MessageType.TEXT if chat_request.text else MessageType.OBJECT,
        text=chat_request.text,
        object=MessageObject(
            type=chat_request.object.type,
            id=chat_request.object.id,
            title=chat_request.object.title,
            attributes=chat_request.object.attributes
        ) if chat_request.object else None
    )


def _build_chat_response(process_result: ProcessResult) -> ChatResponse:
    return ChatResponse(
        sender_id=process_result.sender_id,
        message_id=process_result.message_id,
        messages=[ChatMessage(
            text=message.text,
            object=ChatObject(**asdict(message.object)) if message.object else None
        ) for message in process_result.messages]
    )
