import logging

from fastapi import FastAPI

from app.api import chat, health

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

app = FastAPI(
    title="Education Admin Copilot",
    description="교육행정 RAG Copilot API",
    version="1.0.0",
)

app.include_router(health.router)
app.include_router(chat.router)
