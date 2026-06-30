import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.tools import registry

if __name__ == "__main__":
    # Check registered tools
    print("Registered tools:", list(registry.tools.keys()))

    # Test web_search
    try:
        results = registry.execute("web_search", {"query": "AI regulations", "max_results": 3})
        print("Search results:", results)
    except Exception as e:
        print("Error:", e)

    # Print invocation log
    print("\nInvocation log:")
    for inv in registry.invocation_log:
        print(f"  Tool: {inv.tool_name}, Params: {inv.params}, Result: {inv.result}, Error: {inv.error}")