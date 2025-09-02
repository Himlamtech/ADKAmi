# app/infra/embeddings/openai_embeddings.py
"""Clean OpenAI embeddings wrapper."""

import asyncio
import logging
from typing import Any

import rootutils  # type: ignore
from openai import OpenAI

rootutils.setup_root(__file__, indicator=".env", pythonpath=True)

from app.core.config import settings  # noqa: E402

logger = logging.getLogger(__name__)


class OpenAIEmbeddings:
    """Simple OpenAI embeddings wrapper."""

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

    async def embed(
        self,
        text: str | list[str],
        model_id: str = "text-embedding-3-small",
        **kwargs: Any,
    ) -> list[list[float]]:
        """Get embeddings for text(s)."""
        texts = [text] if isinstance(text, str) else text
        payload = {"model": model_id, "input": texts, **kwargs}

        try:
            response = await asyncio.to_thread(self.client.embeddings.create, **payload)
            return [item.embedding for item in response.data]
        except Exception:
            logger.exception(f"Embeddings failed: model={model_id}")
            raise

    async def embed_single(
        self,
        text: str,
        model_id: str = "text-embedding-3-small",
        **kwargs: Any,
    ) -> list[float]:
        """Get embedding for single text."""
        result = await self.embed(text, model_id, **kwargs)
        return result[0]


# Usage
if __name__ == "__main__":

    async def demo() -> None:
        embeddings = OpenAIEmbeddings()
        # Single text
        vector = await embeddings.embed_single("Hello world!")
        print(f"Single: {len(vector)} dims")
        # Multiple texts
        vectors = await embeddings.embed(["Hello", "World", "AI"])
        print(f"Batch: {len(vectors)} vectors")

    asyncio.run(demo())
