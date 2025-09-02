from google.adk.agents import LlmAgent, Agent, SequentialAgent
from pymongo import MongoClient
from dotenv import load_dotenv
import os
from google import genai
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any

from .config import MONGODB_URI, MONGODB_DATABASE, MONGODB_COLLECTION
from .sub_agents.rag_agent import RAG_Agent
from .prompt import qa_agent_instruction

from google.adk.tools import google_search

load_dotenv()

answer_generator = LlmAgent(
    name="qa_answer_generator",
    model = "gemnini-2.5-flash",
    instruction = qa_agent_instruction,
)
    

qa_agent = RAG_Agent(
    name="qa_agent",
    answer_generator=answer_generator,
)

    