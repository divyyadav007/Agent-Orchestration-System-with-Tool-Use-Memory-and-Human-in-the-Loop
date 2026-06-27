# src/core/specialists/research.py
from src.core.specialists.base import SpecialistBase

RESEARCH_SYSTEM_PROMPT = """You are a research specialist. You have access to a 'web_search' tool that searches the web and returns a list of results (title, url, snippet). 
You do NOT have any other tools (no page fetching, no file access, no code execution). 
If you need detailed content from a specific URL, you cannot fetch it directly. Instead, craft a more specific search query to find the needed information, or note that you only have snippet-level access.

Always provide accurate and concise information. Cite sources when possible.

IMPORTANT: Only call the 'web_search' tool. Do not call any other function."""

class ResearchSpecialist(SpecialistBase):
    def __init__(self):
        super().__init__(
            name="research",
            system_prompt=RESEARCH_SYSTEM_PROMPT,
            tools=["web_search"]  # only web_search tool for now
        )