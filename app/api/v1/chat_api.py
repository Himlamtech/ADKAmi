# app/api/v1/chat_api.py
"""Chat API endpoints."""

import logging
from functools import lru_cache
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import ChatService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@lru_cache()
def get_chat_service() -> ChatService:
    """Dependency injection cho ChatService với caching."""
    return ChatService()


@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    chat_service: ChatService = Depends(get_chat_service),
) -> ChatResponse:
    """Chat với AI."""
    try:
        response = await chat_service.chat(request)
        logger.info(f"Chat successful: session_id={response.session_id}")
        return response
    except Exception as e:
        logger.exception("Chat endpoint failed")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@router.get("/storage/stats")
async def get_storage_stats(
    chat_service: ChatService = Depends(get_chat_service),
) -> dict[str, Any]:
    """Lấy thống kê storage."""
    return chat_service.storage.get_storage_stats()
