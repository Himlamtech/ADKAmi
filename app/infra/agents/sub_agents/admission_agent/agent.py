from google.adk.agents import LlmAgent, Agent, SequentialAgent
from pymongo import MongoClient
from dotenv import load_dotenv
import os
from google import genai
from concurrent.futures import ThreadPoolExecutor, as_completed
from .prompt import admission_agent_instruction
from typing import List, Dict, Any

from .tools.search_from_database import find_similar_information_by_hybrid_search

from .connection import mongo_client as admission_mongo_client
from .connection import client as admission_client

from .sub_agents.rag_agent import RAG_Agent_admission

from google.adk.tools import google_search

load_dotenv()

admission_agent = RAG_Agent_admission(
    name="admission_rag_agent",
    answer_generator=LlmAgent(
        name="admission_rag_llm",
        instruction=admission_agent_instruction,
        model="gemini-2.5-flash"
    )
)


# admission_agent = Agent(
#     name = "admission_agent",
#     description = "Tác nhân sử dụng rag_agent_admission để trả lời câu hỏi của người dùng về thông tin tuyển sinh và thông tin các ngành học của công nghệ bưu chính viễn thông Viễn thông PTIT",
#     instruction = admission_agent_instruction,
#     sub_agents = [admission_rag_agent]
# )

