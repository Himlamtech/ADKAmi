"""RAG API schemas."""

from typing import List

from pydantic import BaseModel, Field


class RAGChatRequest(BaseModel):
    """Request schema for RAG chat."""

    question: str = Field(..., description="User question")
    session_id: str = Field(..., description="Chat session ID")


class RAGChatResponse(BaseModel):
    """Response schema for RAG chat."""

    answer: str = Field(..., description="Generated answer")
    session_id: str = Field(..., description="Chat session ID")


class RAGRequest(BaseModel):
    """Request schema for RAG queries."""

    query: str = Field(..., description="User question to answer using RAG")
    top_k: int = Field(
        default=3, description="Number of relevant documents to retrieve"
    )


class RAGDocument(BaseModel):
    """Schema for retrieved documents."""

    content: str = Field(..., description="Document content")
    score: float = Field(..., description="Similarity score")
    metadata: dict = Field(default_factory=dict, description="Document metadata")


class RAGResponse(BaseModel):
    """Response schema for RAG queries."""

    answer: str = Field(..., description="Generated answer")
    query: str = Field(..., description="Original query")
    documents: List[RAGDocument] = Field(..., description="Retrieved documents")
    total_documents: int = Field(..., description="Total number of documents retrieved")
