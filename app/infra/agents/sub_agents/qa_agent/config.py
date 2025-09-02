"""
Configuration settings for the RAG Agent.

These settings are used by the various RAG tools.
Vertex AI initialization is performed in the package's __init__.py
"""

import os

from dotenv import load_dotenv

load_dotenv()



DEFAULT_CHUNK_SIZE = 512
DEFAULT_CHUNK_OVERLAP = 100
DEFAULT_TOP_K = 10
DEFAULT_CANDIDATES = 50
DEFAULT_VECTOR_SEARCH_INDEX = "vector_index"
DEFAULT_ATLAS_SEARCH_INDEX = "text_search"
DEFAULT_DISTANCE_THRESHOLD = 0.5
DEFAULT_EMBEDDING_MODEL = "gemini-embedding-exp-03-07"