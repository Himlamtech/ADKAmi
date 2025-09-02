from google.adk.agents import LlmAgent
from .prompt import general_instruction
from dotenv import load_dotenv

load_dotenv()
general_agent = LlmAgent(
    name = 'general_agent',
    model = 'gemini-2.5-flash',
    description= "Tác nhân tổng quát, có chức năng xử lý các yêu cầu chung.",
    instruction = general_instruction,
    disallow_transfer_to_parent= True
)