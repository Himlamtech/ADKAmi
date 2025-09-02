from google import genai
from typing import List
from ..connection import client
from dotenv import load_dotenv
from ..config import DEFAULT_EMBEDDING_MODEL

load_dotenv()


def get_embedding(text: str, model: str = DEFAULT_EMBEDDING_MODEL) -> List[float]:
    """
    Lấy embedding cho một chuỗi văn bản.
    """
    result = client.models.embed_content(model=model, contents=text)
    # Extract the actual float values from ContentEmbedding object
    embedding_obj = result.embeddings[0]  # Get first embedding
    embedding_values = embedding_obj.values  # Extract float values
    return embedding_values
