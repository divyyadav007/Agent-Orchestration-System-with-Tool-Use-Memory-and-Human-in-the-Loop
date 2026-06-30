import logging
from typing import Dict, Any, Optional
from src.core.specialists.base import SpecialistBase
from src.utils.llm import get_llm, invoke_with_retry
from langchain_core.messages import SystemMessage, HumanMessage
from src.tools import registry

# Initialize module logger
logger = logging.getLogger(__name__)

RESEARCH_SYSTEM_PROMPT = """You are a research specialist. You have access to a 'web_search' tool that returns web search results with titles, URLs, and content snippets.

Your task is to find recent news articles based on the user's request.

You must:
- Use the web_search tool to find relevant articles.
- STRICT TOPIC FILTERING: Extract information that is DIRECTLY relevant to the specific topic requested. If the search results contain general daily news wraps or summary pages with multiple unrelated headlines (e.g., world news, sports, earthquakes, other political issues), you MUST ignore the unrelated topics and ONLY extract the elements concerning the requested topic.
- For each relevant article, extract the URL, title, and a brief excerpt or summary focusing ONLY on the requested topic.
- Output a valid JSON array of objects, where each object has the keys "url", "title", and "excerpt".
- Example format:
  [
    {"url": "https://example.com/article1", "title": "Article Title 1", "excerpt": "A brief summary of the article..."},
    {"url": "https://example.com/article2", "title": "Article Title 2", "excerpt": "Another brief summary..."}
  ]
- Do NOT include any other text, markdown, or explanation before or after the JSON array.
- If the search tool returns no relevant results for the requested topic, output an empty array: []
"""

class ResearchSpecialist(SpecialistBase):
    """Specialist agent specialized in querying the web and parsing findings into structured JSON."""
    
    def __init__(self) -> None:
        super().__init__(
            name="research",
            system_prompt=RESEARCH_SYSTEM_PROMPT,
            tools=["web_search"]
        )

    def execute_task(self, task_description: str, previous_outputs: Optional[Dict[str, Any]] = None) -> str:
        """Executes the research subtask.
        
        Generates a targeted web search query, invokes the search engine,
        and requests formatting of the outcomes into a JSON array structure.

        Args:
            task_description (str): Description detailing search topics.
            previous_outputs (Optional[Dict[str, Any]]): Outputs from previous task executions.

        Returns:
            str: Valid JSON array representation of search results.
        """
        logger.info(f"[{self.name}] Initiating research: '{task_description[:80]}...'")
        
        # Step 1: Generate a targeted search query from the task description
        query_gen_messages = [
            SystemMessage(content="You are an expert at creating web search queries."),
            HumanMessage(content=f"Generate a concise, effective search query for the following task. Output ONLY the query string. Task: {task_description}")
        ]
        query_gen_llm = get_llm(temperature=0)
        query_response = invoke_with_retry(query_gen_llm, query_gen_messages)
        query = query_response.content.strip().strip('"')
        logger.debug(f"[{self.name}] Generated search query: '{query}'")

        # Step 2: Directly execute the web search tool
        try:
            search_result = registry.execute("web_search", {"query": query, "max_results": 5})
        except Exception as e:
            logger.error(f"[{self.name}] Web search tool failure: {e}", exc_info=True)
            return f"Error executing web search: {e}"

        # Step 3: Pass the results to the LLM to format into the required JSON
        formatting_messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"Please process the following search results and format them into the specified JSON format.Search Results:{search_result}")
        ]
        
        formatting_llm = get_llm(temperature=0).bind_tools([], tool_choice="none")
        final_response = invoke_with_retry(formatting_llm, formatting_messages)
        
        logger.info(f"[{self.name}] Research formatting completed.")
        return final_response.content
