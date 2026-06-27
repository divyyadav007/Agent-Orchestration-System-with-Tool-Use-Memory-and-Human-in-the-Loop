from langgraph.types import interrupt
from src.core.state import WorkflowState

def escalation_node(state: WorkflowState) -> dict:
    # If human hasn't decided yet, pause the graph
    if not state.get("human_decision"):
        retry_count = state.get("current_task_retry_count", 0)
        reason = f"Task {state['current_task_id']} failed after {retry_count} retries. Output: {state.get('current_task_output', '')[:200]}..."
        # Pause execution and wait for resume (human input)
        interrupt({
            "awaiting_human": True,
            "escalation_reason": reason
        })
        # Code after interrupt runs only after resume
        # At this point, state will have human_decision updated by the Streamlit UI
    
    # Now process human decision (after resume)
    decision = state.get("human_decision")
    task_id = state["current_task_id"]
    new_completed = dict(state.get("completed_tasks", {}))
    
    if decision == "approve":
        new_completed[task_id] = {
            "output": state.get("current_task_output", ""),
            "assigned_to": state["current_task_assigned_to"],
            "review_score": 0.0,
            "passed": True,
            "human_approved": True
        }
    elif decision == "reject":
        new_completed[task_id] = {
            "output": "REJECTED BY HUMAN",
            "assigned_to": state["current_task_assigned_to"],
            "passed": False,
            "human_rejected": True
        }
    # If modify or other, you can handle accordingly (for now, treat as reject)
    
    return {
        "completed_tasks": new_completed,
        "current_task_id": None,        # clear to move to next task
        "current_task_output": None,
        "review_feedback": None,
        "current_task_retry_count": 0,
        "awaiting_human": False,
        "human_decision": None,         # reset for next escalation
        "messages": [{"role": "system", "content": f"Human decision '{decision}' applied to task {task_id}"}]
    }