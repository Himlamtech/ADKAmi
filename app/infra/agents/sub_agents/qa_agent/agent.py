from google.adk.agents import LlmAgent, Agent, SequentialAgent
from pymongo import MongoClient
from dotenv import load_dotenv
import os
from google import genai
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any
from .sub_agents.rag_agent import RAG_Agent
from .prompt import qa_agent_instruction

from google.adk.tools import google_search

load_dotenv()

qa_agent = RAG_Agent(
    name="qa_agent",
    answer_generator=LlmAgent(
        name="rag_llm",
        model="gemini-2.5-flash",
        instruction=qa_agent_instruction
    )
)