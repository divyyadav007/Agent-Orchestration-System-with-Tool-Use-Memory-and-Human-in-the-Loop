import os
from dotenv import load_dotenv
from .registry import registry
from tavily import TavilyClient

load_dotenv()

# Initialize Tavily client (lazy, will be created on first call)
tavily_client = None

def get_tavily_client():
    global tavily_client
    if tavily_client is None:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise ValueError("TAVILY_API_KEY not found in .env")
        tavily_client = TavilyClient(api_key=api_key)
    return tavily_client

@registry.register(
    name="web_search",
    description="Search the web for up-to-date information. Returns list of results with title, url, and content snippet.",
    parameter_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query string"},
            "max_results": {"type": "integer", "description": "Maximum results (max 5, default 3)", "default": 5}
        },
        "required": ["query"]
    }
)
def web_search(query: str, max_results: int = 5) -> list:
    """
    Search the web using Tavily API and return a list of result dicts.
    """
    client = get_tavily_client()
    response = client.search(query=query, max_results=max_results)
    # Tavily returns a list of results with 'title', 'url', 'content'
    results = []
    for result in response.get("results", []):
        snippet = result.get("content", "")
        if len(snippet) > 1000:
            snippet = snippet[:1000] + "..."
        results.append({
            "title": result.get("title", ""),
            "url": result.get("url", ""),
            "snippet": snippet # snippet as content
        })
    return results