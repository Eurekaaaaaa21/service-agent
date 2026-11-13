from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from yoyo.app.chat_router import chat_router
from yoyo.app.dependencies import init_dialogue_engine
from yoyo.clients.database_client import init_database, close_database
from yoyo.clients.http_client import init_http_client, close_http_client
from yoyo.repository.lab_booking_repository import ensure_schema_and_seed

INDEX_PAGE = Path(__file__).parent / "index.html"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_http_client()
    init_database()
    await ensure_schema_and_seed()
    init_dialogue_engine()
    yield
    await close_database()
    await close_http_client()


app = FastAPI(title="实验室预约客服", lifespan=lifespan)

app.include_router(chat_router)


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    """客服聊天页，直接打开根路径即可对话"""
    return FileResponse(INDEX_PAGE, media_type="text/html")


@app.get("/health", include_in_schema=False)
async def health() -> dict:
    return {"status": "ok", "service": "lab-booking-assistant"}
