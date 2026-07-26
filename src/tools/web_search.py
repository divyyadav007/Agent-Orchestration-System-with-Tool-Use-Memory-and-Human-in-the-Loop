import logging
import os
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from .registry import registry
from tavily import TavilyClient

load_dotenv()
logger = logging.getLogger(__name__)

# Global lazy-initialized TavilyClient instance
_tavily_client: Optional[TavilyClient] = None


def get_tavily_client() -> TavilyClient:
    """Returns a shared, lazily initialized TavilyClient instance.

    Why lazy initialization: Prevents crashing app startup if TAVILY_API_KEY
    is missing until a web search is actually requested.
    """
    global _tavily_client
    if _tavily_client is None:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            logger.error("TAVILY_API_KEY environment variable is missing.")
            raise ValueError("TAVILY_API_KEY not found in .env file.")
        _tavily_client = TavilyClient(api_key=api_key)
        logger.debug("TavilyClient initialized successfully.")
    return _tavily_client


@registry.register(
    name="web_search",
    description="Search the web for up-to-date information. Returns list of results with title, url, and snippet.",
    parameter_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query string"},
            "max_results": {"type": "integer", "description": "Maximum results to return (max 5, default 5)", "default": 5},
        },
        "required": ["query"],
    },
)
def web_search(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """Performs a web search using the Tavily Search API.

    Why Tavily: Unlike standard search engines, Tavily provides clean, LLM-optimized
    text snippets directly, avoiding complex HTML scraping and page parsing.
    """
    logger.info(f"Searching web for query='{query}', max_results={max_results}")
    try:
        client = get_tavily_client()
        response = client.search(query=query, max_results=max_results)

        results = [
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": (
                    item.get("content", "")[:1000] + "..." if len(item.get("content", "")) > 1000 else item.get("content", "")
                ),
            }
            for item in response.get("results", [])
        ]

        logger.debug(f"Retrieved {len(results)} search results.")
        return results
    except Exception as e:
        logger.error(f"Error executing web search for '{query}': {e}", exc_info=True)
        raise
