import rootutils

rootutils.setup_root(__file__, indicator=".env", pythonpath=True)

import time
from datetime import datetime
from uuid import UUID

from app.core.config import get_config
from app.infra.llms.openai_llm import OpenAILLM
from app.infra.storage.chroma_vector_store import ChromaVectorStore
from app.infra.storage.json_storage import JSONChatStorage
from app.schemas.chat import Message


# ---- RAG Service ----------------------------------------------------------
class RAGService:
    """Compact RAG service using ChromaDB vector store and OpenAI client."""

    def __init__(self):
        self.config = get_config()
        self.vector_store = ChromaVectorStore()
        self.storage = JSONChatStorage()
        self.llm = OpenAILLM()

    def _create_prompt(self, question: str, context: list[str]) -> list[dict[str, str]]:
        """Create simple prompt for RAG."""
        context_text = "\n\n".join(context)
        prompt = f"""Bạn là trợ lý AI thông minh của Học viện PTIT. Hãy trả lời câu hỏi dựa trên thông tin được cung cấp.

Thông tin tham khảo:
{context_text}

Câu hỏi: {question}

Hãy trả lời một cách chính xác, súc tích và hữu ích. Nếu không tìm thấy thông tin liên quan, hãy nói rằng bạn không có đủ thông tin để trả lời."""

        return [{"role": "user", "content": prompt}]

    async def generate_response(self, question: str, session_id: str) -> str:
        """Generate response using ChromaDB vector search and OpenAI."""
        # Tìm kiếm tài liệu liên quan
        start_time = time.time()
        relevant_docs = self.vector_store.similarity_search(question, k=5)
        search_time = time.time() - start_time
        print(f"Vector search time: {search_time:.3f}s")

        # Sinh câu trả lời
        start_time = time.time()
        messages = self._create_prompt(question, relevant_docs)
        response = await self.llm.complete(
            messages, model_id=self.config.DEFAULT_CHAT_MODEL_ID.value
        )
        llm_time = time.time() - start_time
        print(f"LLM response time: {llm_time:.3f}s")

        # Lưu lịch sử chat
        chat_messages = [
            Message(role="user", content=question, timestamp=datetime.now()),
            Message(role="assistant", content=response, timestamp=datetime.now()),
        ]
        try:
            session_uuid = UUID(session_id)
        except ValueError:
            # If session_id is not a valid UUID, create a new one
            import uuid

            session_uuid = uuid.uuid4()

        self.storage.append_messages(session_uuid, chat_messages)

        return response


# Usage example:
# import asyncio
#
# async def demo():
#     rag_service = RAGService()
#     # Load data first
#     rag_service.vector_store.load_from_csv()
#
#     # Generate response
#     response = await rag_service.generate_response(
#         "Giám đốc học viện là ai?",
#         "550e8400-e29b-41d4-a716-446655440000"
#     )
#     print(response)
#
# # asyncio.run(demo())
