import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.graph import build_graph

app = build_graph()

if __name__ == "__main__":
    initial_state = {
        "messages": [],
        "user_request": "I need a summary of recent news about AI regulations, then write a 200-word brief for my CEO, and save it to a file.",
        "plan": None,
        "validation_errors": None,
        "retry_count": 0,
    }

    final_state = app.invoke(initial_state)

    print("Final plan valid:", final_state["validation_errors"] is None)
    if final_state["plan"]:
        print("Plan subtasks:")
        for st in final_state["plan"].subtasks:
            print(f"  {st.id}: {st.description} (assigned to {st.assigned_to})")
        print("Critical path:", final_state["plan"].critical_path)
    print("Retry count:", final_state["retry_count"])
