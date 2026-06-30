import logging
from typing import Dict, Any
from src.core.state import WorkflowState

# Initialize module logger
logger = logging.getLogger(__name__)

SPECIALIST_NODE_MAP: Dict[str, str] = {
    "research": "research_specialist",
    "data": "data_specialist",
    "writing": "writing_specialist",
    "code": "code_specialist"
}

def selector_node(state: WorkflowState) -> Dict[str, Any]:
    """LangGraph node that determines the next subtask to execute based on dependencies.

    Scans the execution plan to find the first uncompleted subtask whose 
    dependencies have all been successfully completed.

    Args:
        state (WorkflowState): Current global graph state.

    Returns:
        Dict[str, Any]: State updates indicating the selected subtask's details
            (ID, description, assigned specialist, and reset retry/feedback counters),
            or a cleared current_task_id if all tasks are finished.
    """
    plan = state["plan"]
    if plan is None:
        logger.warning("Selector node: No execution plan found in state.")
        return {"current_task_id": None}

    completed = state.get("completed_tasks", {})
    
    # Sort subtasks by their ordering in the critical path to maintain execution sequence
    subtask_order = {task_id: idx for idx, task_id in enumerate(plan.critical_path)}
    sorted_subtasks = sorted(plan.subtasks, key=lambda st: subtask_order.get(st.id, 999))

    for subtask in sorted_subtasks:
        if subtask.id in completed:
            continue
            
        # Check if all dependency tasks have been completed successfully
        deps_met = all(dep in completed for dep in subtask.dependencies)
        if deps_met:
            logger.info(f"Selector node: Next subtask selected is '{subtask.id}' (assigned to specialist: '{subtask.assigned_to}')")
            return {
                "current_task_id": subtask.id,
                "current_task_description": subtask.description,
                "current_task_assigned_to": subtask.assigned_to,
                "current_task_retry_count": 0,
                "review_feedback": None
            }

    logger.info("Selector node: All planned subtasks have been completed successfully.")
    return {"current_task_id": None}