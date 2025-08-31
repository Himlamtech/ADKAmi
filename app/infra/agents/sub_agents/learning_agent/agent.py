from google.adk.agents import LlmAgent, Agent, SequentialAgent
from pymongo import MongoClient
from dotenv import load_dotenv
import os
from google import genai
from concurrent.futures import ThreadPoolExecutor, as_completed
from .prompt import learning_agent_instruction
from typing import List, Dict, Any

from .tools.search_from_database import find_similar_documents_by_hybrid_search
from .tools.reranking import rerank_documents

from .connection import mongo_client
from .connection import client

from .sub_agents.rag_agent import RAG_Agent


load_dotenv()

rag_agent_instance = RAG_Agent(
    name="rag_agent",
    answer_generator=LlmAgent(
        name="rag_llm",
        model="gemini-2.5-flash"
    )
)

learning_agent = Agent(
    name = "learning_agent",
    description = "Tác nhân sử dụng rag_agent_instance để trả lời câu hỏi của người dùng",
    instruction = learning_agent_instruction,
    sub_agents = [rag_agent_instance],
    disallow_transfer_to_parent= True
)

