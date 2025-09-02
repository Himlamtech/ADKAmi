from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.planners import BuiltInPlanner
from .sub_agents.coding_agent import coding_agent
from .sub_agents.learning_agent import learning_agent
from .sub_agents.admission_agent import admission_agent
from .sub_agents.general_agent import general_agent
from .sub_agents.qa_agent import qa_agent
from dotenv import load_dotenv

# from ...core.config import settings
from google.genai import types

from .prompt import root_agent_instruction

load_dotenv()
root_agent = Agent(
    name="root_agent",
    model="gemini-2.5-flash",  # Use settings.THINKING_CHAT_MODEL_ID later because we cannot test with adk web
    description="Tác nhân gốc, có chức năng phân tích và định tuyến yêu cầu đến tác nhân phù hợp.",
    instruction=root_agent_instruction,
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            include_thoughts=True, thinking_budget=1024
        )
    ),
    sub_agents= [coding_agent, learning_agent, admission_agent, general_agent, qa_agent]
)