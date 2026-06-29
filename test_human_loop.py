from src.core.graph import build_graph
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3

conn = sqlite3.connect("agent_checkpoints.db", check_same_thread=False)
checkpointer = SqliteSaver(conn)
app = build_graph(checkpointer=checkpointer)

config = {"configurable": {"thread_id": "test_1"}}

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
    "human_feedback": None
}

if __name__ == "__main__":
    # First run - will pause at escalation if any
    for event in app.stream(initial_state, config):
        print(event)

    # Streamlit se human decide karega
    # Then resume:
    # for event in app.stream(None, config):  # resume from checkpoint
    #     print(event)