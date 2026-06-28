# src/core/specialists/research.py
from src.core.specialists.base import SpecialistBase
from src.utils.llm import get_llm, invoke_with_retry
from langchain_core.messages import SystemMessage, HumanMessage
from src.tools import registry

RESEARCH_SYSTEM_PROMPT = """You are a research specialist. You have access to a 'web_search' tool that returns web search results with titles, URLs, and content snippets.

Your task is to find recent news articles based on the user's request.

You must:
- Use the web_search tool to find relevant articles.
- For each article, extract the URL, title, and a brief excerpt or summary.
- Output a valid JSON array of objects, where each object has the keys "url", "title", and "excerpt".
- Example format:
  [
    {"url": "https://example.com/article1", "title": "Article Title 1", "excerpt": "A brief summary of the article..."},
    {"url": "https://example.com/article2", "title": "Article Title 2", "excerpt": "Another brief summary..."}
  ]
- Do NOT include any other text, markdown, or explanation before or after the JSON array.
- If the search tool returns no relevant results, output an empty array: []
"""

class ResearchSpecialist(SpecialistBase):
    def __init__(self):
        super().__init__(
            name="research",
            system_prompt=RESEARCH_SYSTEM_PROMPT,
            tools=["web_search"]  # only web_search tool for now
        )

    def execute_task(self, task_description: str, previous_outputs: dict = None) -> str:
        # Step 1: Generate a targeted search query from the task description
        query_gen_messages = [
            SystemMessage(content="You are an expert at creating web search queries."),
            HumanMessage(content=f"Generate a concise, effective search query for the following task. Output ONLY the query string. Task: {task_description}")
        ]
        query_gen_llm = get_llm(temperature=0)
        query_response = invoke_with_retry(query_gen_llm, query_gen_messages)
        query = query_response.content.strip().strip('"')
        print(f"DEBUG researcher: generated query: '{query}'")

        # Step 2: Directly execute the web search tool
        try:
            search_result = registry.execute("web_search", {"query": query})
        except Exception as e:
            return f"Error executing web search: {e}"

        # Step 3: Pass the results to the LLM to format into the required JSON
        formatting_messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=f"Please process the following search results and format them into the specified JSON format.Search Results:{search_result}")
        ]
        
        formatting_llm = get_llm(temperature=0).bind_tools([], tool_choice="none")
        final_response = invoke_with_retry(formatting_llm, formatting_messages)
        
        return final_response.content
