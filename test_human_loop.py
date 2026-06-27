from src.core.graph import build_graph
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3

conn = sqlite3.connect("agent_checkpoints.db", check_same_thread=False)
checkpointer = SqliteSaver(conn)
app = build_graph(checkpointer=checkpointer)

config = {"configurable": {"thread_id": "test_1"}}

initial_state = {
    # ... all fields ...
}

# First run - will pause at escalation if any
for event in app.stream(initial_state, config):
    print(event)

# Streamlit se human decide karega
# Then resume:
# for event in app.stream(None, config):  # resume from checkpoint
#     print(event)