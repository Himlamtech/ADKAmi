import os 
from dotenv import load_dotenv
from google.adk.agents import BaseAgent, LlmAgent
from typing_extensions import override
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from typing import AsyncGenerator
from pymongo import MongoClient
from google import genai
from ..config import DEFAULT_TOP_K, DEFAULT_CANDIDATES, DEFAULT_VECTOR_SEARCH_INDEX, DEFAULT_ATLAS_SEARCH_INDEX
from ..tools.reranking import rerank_documents
from ..tools.search_from_database import find_similar_documents_by_hybrid_search
from ..tools.embedding import get_embedding
import logging

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
class RAG_Agent(BaseAgent):
    answer_generator : LlmAgent
    top_k : int = 10
    candidates : int = 50
    vector_search_index : str = "vector_index"
    atlas_search_index : str = "text_search"
    disallow_transfer_to_parent: bool = True

    def __init__(self, 
        name: str, 
        answer_generator: LlmAgent,
        top_k: int = DEFAULT_TOP_K,
        candidates: int = DEFAULT_CANDIDATES,
        vector_search_index: str = DEFAULT_VECTOR_SEARCH_INDEX,
        atlas_search_index: str = DEFAULT_ATLAS_SEARCH_INDEX,
        ):
        super().__init__(
            name = name,
            answer_generator = answer_generator,
            top_k = top_k,
            candidates = candidates,
            vector_search_index = vector_search_index,
            atlas_search_index = atlas_search_index,
        )
        
        
    @override
    async def _run_async_impl(self, ctx : InvocationContext) -> AsyncGenerator[Event, None]:
        # Get user input from session state
        query = ctx.session.state.get("user_input", "")
        
        # query transform 
        logger.info(f"🔍 Query: {query}")
        # embed
        embedded_query = get_embedding(text = query)
        logger.info(f"Embedded query: {embedded_query}")
        ctx.session.state['embedded_query'] = embedded_query
        
        # retrieve
        retrieved_docs = find_similar_documents_by_hybrid_search(query = query, limit = self.top_k, candidates = self.candidates, vector_search_index = self.vector_search_index, atlas_search_index = self.atlas_search_index)
        logger.info(f"Retrieved documents: {retrieved_docs}")
        ctx.session.state['retrieved_docs'] = retrieved_docs
        
        # rerank
        # reranked_docs = rerank_documents(query, retrieved_docs['data'])
        # logger.info(f"Reranked documents: {reranked_docs}")
        # ctx.session.state['reranked_docs'] = reranked_docs
        
        async for event in self.answer_generator.run_async(ctx):
            if (event.is_final_response() and event.content and event.content.parts):
                # Process final response if needed
                logger.info(f"Final response from answer generator: {event.content.parts[0].text}")
            yield event
        
        






        
    
        
    
    