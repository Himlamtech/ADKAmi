# app/api/v1/rag_api.py
"""RAG Chat API endpoints."""

from fastapi import APIRouter, HTTPException

from app.infra.features.rag.rag import RAGService
from app.schemas.chat import RAGChatRequest, RAGChatResponse

router = APIRouter()
rag_service = RAGService()


@router.post("/rag/chat", response_model=RAGChatResponse)
async def rag_chat(request: RAGChatRequest) -> RAGChatResponse:
    """Chat với RAG service."""
    try:
        answer = await rag_service.generate_response(
            request.question, request.session_id
        )
        return RAGChatResponse(answer=answer, session_id=request.session_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
