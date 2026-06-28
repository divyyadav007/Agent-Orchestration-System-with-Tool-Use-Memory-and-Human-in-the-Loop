from langgraph.types import interrupt
from src.core.state import WorkflowState

def escalation_node(state: WorkflowState) -> dict:
    if not state.get("human_decision"):
        retry_count = state.get("current_task_retry_count", 0)
        reason = f"Task {state['current_task_id']} failed after {retry_count} retries. Output: {state.get('current_task_output', '')[:200]}..."
        interrupt({
            "awaiting_human": True,
            "escalation_reason": reason
        })
    
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
    else:
        # If unknown or still waiting, shouldn't happen after resume
        pass
    
    return {
        "completed_tasks": new_completed,
        "current_task_id": None,
        "current_task_output": None,
        "review_feedback": None,
        "current_task_retry_count": 0,
        "awaiting_human": False,
        "human_decision": None,
        "messages": [{"role": "system", "content": f"Human decision '{decision}' applied to task {task_id}"}]
    }