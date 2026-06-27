from .registry import registry  # relative import instead of absolute
import httpx

# ... baaki code wahi ...import httpx

# We'll use a free mock for now (or you can use a real API)
@registry.register(
    name="web_search",
    description="Search the web for recent information. Returns list of results with title, url, snippet.",
    parameter_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "num_results": {"type": "integer", "description": "Number of results to return", "default": 5}
        },
        "required": ["query"]
    }
)
def web_search(query: str, num_results: int = 5) -> list:
    """
    Mock web search function. In production, replace with Serper.dev or Tavily API.
    """
    # For now, return mock data
    return [
        {
            "title": f"Result {i+1} for '{query}'",
            "url": f"https://example.com/result-{i+1}",
            "snippet": f"This is a mock snippet for result {i+1} about {query}."
        }
        for i in range(num_results)
    ]