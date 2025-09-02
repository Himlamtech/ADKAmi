# app/infra/llms/openai_llm.py
"""Clean OpenAI wrapper."""

import asyncio
import logging
from typing import Any, AsyncIterator

import rootutils  # type: ignore
from openai import OpenAI

rootutils.setup_root(__file__, indicator=".env", pythonpath=True)

from app.core.config import settings  # noqa: E402

logger = logging.getLogger(__name__)


class OpenAILLM:
    """Simple OpenAI wrapper."""

    def __init__(self, client: Any = None) -> None:
        self._client = client

    @property
    def client(self) -> Any:
        """Get OpenAI client."""
        if self._client is None:
            api_key = settings.OPENAI_API_KEY
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY not configured")
            key = (
                api_key.get_secret_value()
                if hasattr(api_key, "get_secret_value")
                else str(api_key)
            )
            self._client = OpenAI(api_key=key)
        return self._client

    async def complete(
        self,
        messages: list[dict[str, Any]],
        model_id: str = "gpt-5-nano",
        **kwargs: Any,
    ) -> str:
        """Get completion."""
        payload = {"model": model_id, "messages": messages, **kwargs}
        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create, **payload
            )
            content = response.choices[0].message.content
            if content is None:
                logger.warning(f"Got None content from OpenAI: {response}")
                return ""
            return content
        except Exception:
            logger.exception(f"OpenAI failed: model={model_id}")
            raise

    async def stream_complete(
        self,
        messages: list[dict[str, Any]],
        model_id: str = "gpt-5-nano",
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """Get streaming completion."""
        payload = self._clean_params(model_id, messages=messages, stream=True, **kwargs)
        try:
            stream = await asyncio.to_thread(
                self.client.chat.completions.create, **payload
            )
            for chunk in stream:
                content = getattr(
                    getattr(chunk.choices[0], "delta", None), "content", None
                )
                if content:
                    yield content
        except Exception:
            logger.exception(f"Streaming failed: model={model_id}")
            raise


# Usage
# if __name__ == "__main__":

#     async def demo() -> None:
#         llm = OpenAILLM()
#         messages = [{"role": "user", "content": "Hello!"}]
#         # Basic
#         result = await llm.complete(messages)
#         print(f"Result: {result}")
#         # Streaming
#         print("Stream: ", end="")
#         async for chunk in llm.stream_complete(messages):
#             print(chunk, end="")
#         print()

#     asyncio.run(demo())
