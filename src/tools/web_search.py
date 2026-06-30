import logging
import os
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
from .registry import registry
from tavily import TavilyClient

# Load environment variables
load_dotenv()

# Initialize module logger
logger = logging.getLogger(__name__)

# Global TavilyClient instance (lazily initialized on first call)
_tavily_client: Optional[TavilyClient] = None

def get_tavily_client() -> TavilyClient:
    """Returns a globally shared, lazily initialized TavilyClient instance.

    Raises:
        ValueError: If TAVILY_API_KEY environment variable is not defined.

    Returns:
        TavilyClient: An authenticated TavilyClient instance.
    """
    global _tavily_client
    if _tavily_client is None:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            logger.error("TAVILY_API_KEY environment variable is missing.")
            raise ValueError("TAVILY_API_KEY not found in .env")
        _tavily_client = TavilyClient(api_key=api_key)
        logger.debug("Successfully initialized TavilyClient.")
    return _tavily_client

@registry.register(
    name="web_search",
    description="Search the web for up-to-date information. Returns list of results with title, url, and content snippet.",
    parameter_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query string"},
            "max_results": {
                "type": "integer", 
                "description": "Maximum results (max 5, default 5)", 
                "default": 5
            }
        },
        "required": ["query"]
    }
)
def web_search(query: str, max_results: int = 5) -> List[Dict[str, str]]:
    """Performs a web search via the Tavily Search API.

    Args:
        query (str): The search query keywords/phrase.
        max_results (int): The maximum number of search results to return (capped at 5).

    Returns:
        List[Dict[str, str]]: A list of dictionaries representing search result records,
            each containing keys 'title', 'url', and 'snippet'.
    """
    logger.info(f"Querying Tavily search with query='{query}', max_results={max_results}")
    try:
        client = get_tavily_client()
        response = client.search(query=query, max_results=max_results)
        
        results: List[Dict[str, str]] = []
        for result in response.get("results", []):
            snippet = result.get("content", "")
            # Truncate overly long content snippets to save LLM context space
            if len(snippet) > 1000:
                snippet = snippet[:1000] + "..."
            results.append({
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "snippet": snippet
            })
            
        logger.debug(f"Retrieved {len(results)} search results from Tavily.")
        return results
    except Exception as e:
        logger.error(f"Error executing web search for query '{query}': {e}", exc_info=True)
        raise