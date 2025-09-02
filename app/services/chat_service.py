# app/services/chat_service.py
"""Chat service with in-memory storage."""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from app.infra.llms.openai_llm import OpenAILLM
from app.infra.storage.json_storage import JSONChatStorage
from app.schemas.chat import ChatRequest, ChatResponse, Message, SessionInfo
from app.utils.io import load_json

logger = logging.getLogger(__name__)


class ChatService:
    """Service xử lý logic chat với in-memory storage."""

    def __init__(
        self,
        llm_client: Optional[OpenAILLM] = None,
        storage: Optional[JSONChatStorage] = None,
    ) -> None:
        self.llm = llm_client or OpenAILLM()
        self.storage = storage or JSONChatStorage()
        # Load existing sessions from storage
        self.session_info: Dict[UUID, SessionInfo] = load_json("storage/sessions.json")

    async def chat(self, request: ChatRequest) -> ChatResponse:
        # 1. Tạo hoặc lấy session
        session_id = request.session_id or uuid4()
        if session_id not in self.session_info:
            await self._create_session(session_id)

        # 2. Lấy conversation history
        history = await self.get_conversation_history(session_id)

        # 3. Thêm user message vào history
        user_msg = Message(
            role="user",
            content=request.message,
            timestamp=datetime.now(),
        )

        # 4. Prepare messages cho OpenAI (chỉ role + content)
        openai_messages = [
            {"role": msg.role, "content": msg.content} for msg in history
        ]
        openai_messages.append({"role": "user", "content": request.message})

        try:
            # 5. Call OpenAI
            assistant_content = await self.llm.complete(
                messages=openai_messages,
                model_id=request.model,
            )

            # 6. Tạo assistant response
            assistant_msg = Message(
                role="assistant",
                content=assistant_content,
                timestamp=datetime.now(),
                model_used=request.model,
            )

            # 7. Lưu messages
            await self.save_messages(session_id, [user_msg, assistant_msg])

            # 8. Update session info
            await self._update_session(session_id)

            # 9. Return response
            updated_history = await self.get_conversation_history(session_id)
            return ChatResponse(
                session_id=session_id,
                message=assistant_msg,
                conversation_history=updated_history,
                model_used=request.model,
            )

        except Exception:
            logger.exception("Chat failed")
            # Vẫn lưu user message ngay cả khi AI fail
            await self.save_messages(session_id, [user_msg])
            raise

    async def get_conversation_history(self, session_id: UUID) -> List[Message]:
        """Lấy conversation history."""
        return self.storage.load_messages(session_id, max_conversation_length=10)

    async def save_messages(self, session_id: UUID, messages: List[Message]) -> None:
        """Lưu messages vào storage."""
        self.storage.append_messages(session_id, messages)

    async def _create_session(self, session_id: UUID) -> None:
        """Tạo session mới."""
        self.session_info[session_id] = SessionInfo(
            session_id=session_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            message_count=0,
        )

    async def _update_session(self, session_id: UUID) -> None:
        """Update session info."""
        if session_id in self.session_info:
            session = self.session_info[session_id]
            session.updated_at = datetime.now()

            # Get current message count
            messages = await self.get_conversation_history(session_id)
            session.message_count = len(messages)

            # Auto-generate title từ first user message
            if not session.title and session.message_count > 0:
                first_msg = messages[0]
                if first_msg.role == "user":
                    # Lấy 50 ký tự đầu làm title
                    session.title = first_msg.content[:50] + (
                        "..." if len(first_msg.content) > 50 else ""
                    )

            # Save updated session info
            self.storage.save_sessions(self.session_info)

    def get_available_models(self) -> List[str]:
        """Lấy danh sách models available."""
        return ["gpt-5", "gpt-5-mini", "gpt-5-nano"]
