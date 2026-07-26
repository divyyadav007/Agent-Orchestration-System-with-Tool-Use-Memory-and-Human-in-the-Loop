import logging
from typing import Any, Dict, Optional

from langchain_core.messages import HumanMessage, SystemMessage

from src.core.specialists.base import SpecialistBase
from src.tools import registry
from src.utils.llm import get_llm, invoke_with_retry

logger = logging.getLogger(__name__)

RESEARCH_SYSTEM_PROMPT = """You are a research specialist. You have access to a 'web_search' tool.
Your task is to find recent news articles based on the user's request.

Rules:
- Extract information DIRECTLY relevant to the topic requested.
- For each relevant article, extract the URL, title, and a brief excerpt.
- Output ONLY a valid JSON array of objects: [{"url": "...", "title": "...", "excerpt": "..."}, ...]
- Do NOT include any markdown or text around the JSON array.
- If no relevant results are found, output an empty JSON array: []
"""


class ResearchSpecialist(SpecialistBase):
    """Research Specialist Agent: Queries web search and formats structured JSON results.

    Why a 3-step pipeline is used:
    1. Query Generation: Refines complex task prompts into crisp search query terms.
    2. Tool Execution: Directly calls Tavily web search.
    3. JSON Formatting: Filters and structures raw search results into standard JSON.
    """

    def __init__(self) -> None:
        super().__init__(name="research", system_prompt=RESEARCH_SYSTEM_PROMPT, tools=["web_search"])

    def execute_task(self, task_description: str, previous_outputs: Optional[Dict[str, Any]] = None) -> str:
        logger.info(f"[{self.name}] Researching: '{task_description[:80]}...'")

        # Step 1: Generate concise search query keywords
        llm = get_llm(temperature=0)
        query_prompt = [
            SystemMessage(content="You are an expert at creating web search queries."),
            HumanMessage(
                content=f"Generate a concise search query for this task. Output ONLY the query text.\nTask: {task_description}"
            ),
        ]
        query = invoke_with_retry(llm, query_prompt).content.strip().strip('"')

        # Step 2: Execute Tavily search tool directly
        try:
            raw_results = registry.execute("web_search", {"query": query, "max_results": 5})
        except Exception as e:
            logger.error(f"[{self.name}] Search failed: {e}", exc_info=True)
            return f"Error executing web search: {e}"

        # Step 3: Format search results into requested JSON array
        format_prompt = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"Format search results into the required JSON array format.\nSearch Results: {raw_results}"),
        ]
        formatting_llm = get_llm(temperature=0).bind_tools([], tool_choice="none")
        return invoke_with_retry(formatting_llm, format_prompt).content
