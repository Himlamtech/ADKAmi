# app/infra/storage/json_storage.py
"""JSON file storage for chat sessions."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from uuid import UUID

from app.schemas.chat import Message, SessionInfo
from app.utils.io import load_json, save_json

logger = logging.getLogger(__name__)


class JSONChatStorage:
    """JSON file-based storage for chat sessions."""

    def __init__(self, storage_dir: str = "storage") -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.sessions_file = self.storage_dir / "sessions.json"
        self.messages_dir = self.storage_dir / "messages"
        self.messages_dir.mkdir(exist_ok=True)

    def _serialize_message(self, message: Message) -> Dict[str, Any]:
        """Convert Message to JSON-serializable dict."""
        return {
            "role": message.role,
            "content": message.content,
            "timestamp": message.timestamp.isoformat(),
            "model_used": message.model_used,
        }

    def _deserialize_message(self, data: Dict[str, Any]) -> Message:
        """Convert dict back to Message."""
        return Message(
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            model_used=data.get("model_used"),
        )

    def _serialize_session_info(self, session: SessionInfo) -> Dict[str, Any]:
        """Convert SessionInfo to JSON-serializable dict."""
        return {
            "session_id": str(session.session_id),
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "message_count": session.message_count,
            "title": session.title,
        }

    def _deserialize_session_info(self, data: Dict[str, Any]) -> SessionInfo:
        """Convert dict back to SessionInfo."""
        return SessionInfo(
            session_id=UUID(data["session_id"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            message_count=data["message_count"],
            title=data.get("title"),
        )

    def load_sessions(self) -> Dict[UUID, SessionInfo]:
        """Load all sessions from JSON file."""
        if not self.sessions_file.exists():
            logger.warning(f"Sessions file not found: {self.sessions_file}")
            return {}

        data = load_json(str(self.sessions_file))

        sessions = {}
        for session_data in data.get("sessions", []):
            session = self._deserialize_session_info(session_data)
            sessions[session.session_id] = session

        logger.info(f"Loaded {len(sessions)} sessions from storage")
        return sessions

    def save_sessions(self, sessions: Dict[UUID, SessionInfo]) -> None:
        """Save all sessions to JSON file."""
        try:
            data = {
                "sessions": [
                    self._serialize_session_info(session)
                    for session in sessions.values()
                ],
                "last_updated": datetime.now().isoformat(),
            }

            save_json(str(self.sessions_file), data)

            logger.info(f"Saved {len(sessions)} sessions to storage")

        except Exception as e:
            logger.error(f"Failed to save sessions: {e}")

    def load_messages(
        self, session_id: UUID, max_conversation_length: int
    ) -> List[Message]:
        """Load messages for a specific session."""
        try:
            messages_file = self.messages_dir / f"{session_id}.json"
            if not messages_file.exists():
                return []

            data = load_json(str(messages_file))

            messages = []

            for id, message_data in enumerate(data.get("messages", [])):
                if id >= max_conversation_length:
                    break
                message = self._deserialize_message(message_data)
                messages.append(message)

            logger.debug(f"Loaded {len(messages)} messages for session {session_id}")
            return messages

        except Exception as e:
            logger.error(f"Failed to load messages for {session_id}: {e}")
            return []

    def save_messages(self, session_id: UUID, messages: List[Message]) -> None:
        """Save messages for a specific session."""
        try:
            messages_file = self.messages_dir / f"{session_id}.json"

            data = {
                "session_id": str(session_id),
                "messages": [self._serialize_message(msg) for msg in messages],
                "last_updated": datetime.now().isoformat(),
                "message_count": len(messages),
            }

            save_json(str(messages_file), data)

            logger.debug(f"Saved {len(messages)} messages for session {session_id}")

        except Exception as e:
            logger.error(f"Failed to save messages for {session_id}: {e}")

    def append_messages(
        self,
        session_id: UUID,
        new_messages: List[Message],
        max_conversation_length: int = 10,
    ) -> None:
        """Append new messages to existing session."""
        try:
            existing_messages = self.load_messages(
                session_id, max_conversation_length=max_conversation_length
            )
            all_messages = existing_messages + new_messages
            self.save_messages(session_id, all_messages)

        except Exception as e:
            logger.error(f"Failed to append messages for {session_id}: {e}")

    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        try:
            sessions = self.load_sessions()
            message_files = list(self.messages_dir.glob("*.json"))
            total_messages = 0

            for file in message_files:
                try:
                    with open(file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        total_messages += data.get("message_count", 0)
                except Exception:
                    continue

            return {
                "total_sessions": len(sessions),
                "total_message_files": len(message_files),
                "total_messages": total_messages,
                "storage_dir": str(self.storage_dir),
            }

        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")
            return {}
