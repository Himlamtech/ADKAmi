from google.adk.agents import LlmAgent
from ..prompt import general_instruction

import os
from dotenv import load_dotenv

general_agent = LlmAgent(
    name = 'general_agent',
    model = 'gemini-2.5-flash',
    instruction = general_instruction
)

root_agent = general_agent