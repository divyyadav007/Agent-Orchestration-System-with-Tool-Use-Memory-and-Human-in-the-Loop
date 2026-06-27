from src.core.graph import build_graph
from src.memory.manager import memory_manager

app = build_graph()

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
    "current_task_retry_count": 0
}

final_state = app.invoke(initial_state)

print("\n=== Final Plan ===")
if final_state["plan"]:
    print("Goal:", final_state["plan"].overall_goal)
    for st in final_state["plan"].subtasks:
        status = "✅" if st.id in final_state["completed_tasks"] else "❌"
        print(f"{status} {st.id}: {st.description} ({st.assigned_to})")

print("\n=== Completed Tasks ===")
for task_id, task_data in final_state["completed_tasks"].items():
    print(f"Task {task_id}:")
    print(task_data["output"][:200], "...")  # first 200 chars

print("\nMessages count:", len(final_state["messages"]))
print("Retry count:", final_state["retry_count"])

# After graph invocation in test_orchestration.py:
if final_state["plan"] and not final_state["validation_errors"]:
    memory_manager.complete_task(
        task_id="demo_task_1",  # generate a unique id
        user_request=initial_state["user_request"],
        plan_summary=str(final_state["plan"].overall_goal),
        tools_used=["web_search"],
        outcome="All tasks completed",
        metadata={"retry_count": final_state["retry_count"]}
    )