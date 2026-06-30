import logging
from typing import Dict, Any
from langgraph.types import interrupt
from src.core.state import WorkflowState

# Initialize module logger
logger = logging.getLogger(__name__)

def escalation_node(state: WorkflowState) -> Dict[str, Any]:
    """LangGraph node representing the human-in-the-loop validation checkpoint.

    If a specialist's output fails review multiple times, this node pauses the
    workflow using LangGraph `interrupt`, waiting for external approval or rejection.

    Args:
        state (WorkflowState): Current global graph state.

    Returns:
        Dict[str, Any]: State updates with the resolved decision and completed task index.
    """
    task_id = state["current_task_id"]
    if not task_id:
        logger.warning("Escalation node executed but no active task_id was found.")
        return {}

    if not state.get("human_decision"):
        retry_count = state.get("current_task_retry_count", 0)
        reason = (
            f"Task {task_id} failed after {retry_count} retries. "
            f"Output snippet: {state.get('current_task_output', '')[:200]}..."
        )
        logger.info(f"Escalating task '{task_id}' to human loop. Reason: {reason}")
        
        # This function call halts execution and yields back to client/checkpointer
        interrupt({
            "awaiting_human": True,
            "escalation_reason": reason
        })
    
    decision = state.get("human_decision")
    logger.info(f"Escalation node: Human decision received: '{decision}' for task '{task_id}'")
    
    new_completed = dict(state.get("completed_tasks", {}))
    if decision == "approve":
        new_completed[task_id] = {
            "output": state.get("current_task_output", ""),
            "assigned_to": state["current_task_assigned_to"],
            "review_score": 1.0,
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
        logger.warning(f"Escalation node: Unknown or empty human decision: '{decision}'")
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