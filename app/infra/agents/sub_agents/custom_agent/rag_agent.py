import os 
from dotenv import load_dotenv
load_dotenv()

from google.adk.agents import BaseAgent, LlmAgent
from typing_extensions import override
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from typing import AsyncGenerator
from pymongo import MongoClient
from google import genai
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAG_Agent(BaseAgent):
    answer_generator : LlmAgent
    top_k : int = 5
    mongodb_uri : str
    mongodb_database : str
    mongodb_collection : str

    
    
    def vector_query(self, query_vector: list)-> list:
        client = MongoClient(self.mongodb_uri)
        db = client.get_database(self.mongodb_database)
        collection = db[self.mongodb_collection]
        if query_vector is None:
            return {
                "retrival-status": "failed", 
                "error": "No embedded query found in state."
            }
        
        results = collection.aggregate([
            {
                "$vectorSearch": {
                    "index": "vector_index",  # tên index bạn đã tạo
                    "queryVector": query_vector,
                    "path": "embedding",
                    "numCandidates": 100,
                    "limit": self.top_k,
                }
            }
        ])
        docs = []
        for doc in results:
            docs.append(doc['information'])
        return docs

    def embedding(self, text : str) -> list:
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        embedded_query = client.models.embed_content(
            model="gemini-embedding-001",
            contents=text,
        ).embeddings[0].values
        return embedded_query
    
    def __init__(self, 
        name: str, 
        answer_generator: LlmAgent,
        mongodb_uri: str,
        mongodb_database: str,
        mongodb_collection: str,
        ):
        super().__init__(
            name = name,
            answer_generator = answer_generator,
            mongodb_uri = mongodb_uri,
            mongodb_database = mongodb_database,
            mongodb_collection = mongodb_collection,
        )
        
        
    @override
    async def _run_async_impl(self, ctx : InvocationContext) -> AsyncGenerator[Event, None]:
        query = ctx.session.state.get("user_input", "")
        
        # query transform 
        
        # embed
        embedded_query = self.embedding(text = query)
        logger.info(f"Embedded query: {embedded_query}")
        ctx.session.state['embedded_query'] = embedded_query
        
        # retrieve
        retrieved_docs = self.vector_query(query_vector = embedded_query)
        logger.info(f"Retrieved documents: {retrieved_docs}")
        ctx.session.state['retrieved_docs'] = retrieved_docs
        
        # rerank
        
        
        async for event in self.answer_generator.run_async(ctx):
            if (event.is_final_response() and event.content and event.content.parts):
                logger.info(f"Final response from answer generator: {event.content.parts[0].text}")
            yield event
        
        






        
    
        
    
    