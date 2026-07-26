import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.errors import GraphInterrupt
from rich import print as rprint

from src.core.graph import build_graph
from src.observability.tracer import GraphTracer
from src.tools import registry

# Connect to SQLite checkpoint DB
conn = sqlite3.connect("agent_checkpoints.db", check_same_thread=False)
checkpointer = SqliteSaver(conn)
app = build_graph(checkpointer=checkpointer)

config = {"configurable": {"thread_id": "test_run_fresh_unique_12"}}  # fresh thread id
initial_state = {
    "messages": [],
    "user_request": "I need a summary of recent news about AI regulations, then write a 200-word brief for my CEO, and save it to a file.",
    "plan": None,
    "validation_errors": None,
    "retry_count": 0,
    "completed_tasks": {},
    "current_task_id": None,
    "current_task_description": None,
    "current_task_assigned_to": None,
    "current_task_output": None,
    "review_feedback": None,
    "current_task_retry_count": 0,
    "awaiting_human": False,
    "escalation_reason": None,
    "human_decision": None,
    "human_feedback": None,
}

if __name__ == "__main__":
    try:
        final_state = app.invoke(initial_state, config)
        print("Graph completed. Final state:")
        print("Completed tasks:", list(final_state["completed_tasks"].keys()))
    except GraphInterrupt:
        print("Graph paused for human approval! Run the Streamlit UI and then resume.")
        final_state = app.get_state(config).values
        # To resume later, run:
        # app.invoke(None, config)

    print("\n=== DEBUG INFO ===")
    print("Plan:", final_state.get("plan"))
    print("Plan subtasks count:", len(final_state["plan"].subtasks) if final_state.get("plan") else 0)
    print("Messages count:", len(final_state.get("messages", [])))
    print("Last 3 messages:")
    for msg in final_state.get("messages", [])[-3:]:
        print(msg)
    print("Current task ID:", final_state.get("current_task_id"))
    print("Current task output:", final_state.get("current_task_output"))
    print("Completed tasks:")
    for k, v in final_state.get("completed_tasks", {}).items():
        print(f"Task {k}: {str(v.get('output'))[:100]}...")

    # Create tracer and attach to registry
    tracer = GraphTracer()
    registry.set_tracer(tracer)

    # Config with callbacks
    config = {"configurable": {"thread_id": "test_run_obs_fresh_12"}, "callbacks": [tracer]}

    # Run graph
    try:
        final_state = app.invoke(initial_state, config)
    except GraphInterrupt:
        print("Graph paused for human approval during traced execution!")
        final_state = app.get_state(config).values

    # Print final state info...
    # Then print trace tree:
    rprint(tracer.get_tree())

    print("Full final state keys:", final_state.keys())
    print("Completed tasks:", final_state.get("completed_tasks"))
