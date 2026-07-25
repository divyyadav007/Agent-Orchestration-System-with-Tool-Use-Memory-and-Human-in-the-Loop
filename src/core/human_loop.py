import logging
from typing import Dict, Any
from langgraph.types import interrupt
from src.core.state import WorkflowState

logger = logging.getLogger(__name__)


def escalation_node(state: WorkflowState) -> Dict[str, Any]:
    """LangGraph Escalation Node: Human-in-the-Loop (HITL) Checkpoint.
    
    Why interrupt() is used: When a task fails automated quality review 2+ times, 
    LangGraph's interrupt() function halts graph execution, saves state to the database, 
    and returns control to the UI. The UI presents an Approve/Reject form to the human operator.
    When the human submits a decision, execution resumes from this exact checkpoint.
    """
    task_id = state.get("current_task_id")
    if not task_id:
        logger.warning("Escalation node: No active task_id found.")
        return {}

    # Step 1: If no decision has been provided by the human yet, trigger LangGraph interrupt
    if not state.get("human_decision"):
        retry_count = state.get("current_task_retry_count", 0)
        output_snippet = str(state.get("current_task_output", ""))[:200]
        reason = f"Task {task_id} failed after {retry_count} retries. Snippet: {output_snippet}..."
        logger.info(f"Escalating task '{task_id}' to Human-in-the-Loop. Reason: {reason}")

        # Yield execution interrupt payload back to Streamlit dashboard
        interrupt({
            "awaiting_human": True,
            "escalation_reason": reason
        })

    # Step 2: Human decision has been submitted, process decision
    decision = state.get("human_decision")
    logger.info(f"Escalation node: Applying human decision '{decision}' for subtask '{task_id}'")

    completed = dict(state.get("completed_tasks", {}))
    if decision == "approve":
        completed[task_id] = {
            "output": state.get("current_task_output", ""),
            "assigned_to": state.get("current_task_assigned_to"),
            "review_score": 1.0,
            "passed": True,
            "human_approved": True
        }
    elif decision == "reject":
        completed[task_id] = {
            "output": "REJECTED BY HUMAN",
            "assigned_to": state.get("current_task_assigned_to"),
            "passed": False,
            "human_rejected": True
        }
    else:
        logger.warning(f"Escalation node: Unrecognized decision '{decision}'.")

    return {
        "completed_tasks": completed,
        "current_task_id": None,
        "current_task_output": None,
        "review_feedback": None,
        "current_task_retry_count": 0,
        "awaiting_human": False,
        "human_decision": None,
        "messages": [{"role": "system", "content": f"Human decision '{decision}' applied to task {task_id}"}]
    }