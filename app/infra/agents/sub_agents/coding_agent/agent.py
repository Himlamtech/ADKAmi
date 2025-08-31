from google.adk.agents import Agent
from dotenv import load_dotenv
from .tools import query_github_code_db, code_generation
from .prompt import coding_agent_instruction, code_debugger_agent_instruction, code_generation_agent_instruction

load_dotenv()
code_debugger_agent = Agent(
    name = "debugger_agent",
    model = "gemini-2.5-flash",
    description= "Tác nhân phân tích và gỡ lỗi mã: xác định lỗi, đề xuất sửa lỗi, và cung cấp bản vá ngắn gọn (chỉ code).",
    instruction = code_debugger_agent_instruction,
    disallow_transfer_to_parent=True
)

code_generation_agent = Agent(
    name = "code_generation_agent",
    model = "gemini-2.5-flash",
    description= "Tác nhân tạo mã: sinh mã hoàn chỉnh theo yêu cầu, trả về CHỈ MÃ (không có giải thích). Hỗ trợ nhiều ngôn ngữ, ưu tiên Python khi không rõ.",
    instruction = code_generation_agent_instruction,
    tools = [query_github_code_db, code_generation],
    disallow_transfer_to_parent=True
)

coding_agent = Agent(
    name = "coding_agent",
    model = "gemini-2.5-flash",
    description= "Tác nhân điều phối mã: phân tích yêu cầu liên quan đến mã và phân luồng, điều phối các sub-agent (sinh mã, gỡ lỗi) để giải quyết nhiệm vụ liên quan đến code.",
    instruction = coding_agent_instruction,
    disallow_transfer_to_parent=True,
    sub_agents=[code_generation_agent, code_debugger_agent]
)