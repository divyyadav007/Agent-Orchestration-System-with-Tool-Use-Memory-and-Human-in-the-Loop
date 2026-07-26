import logging
from typing import Dict, Any
from src.core.state import WorkflowState

logger = logging.getLogger(__name__)

# Canonical mapping connecting planner specialist names to graph node identifiers
SPECIALIST_NODE_MAP: Dict[str, str] = {
    "research": "research_specialist",
    "data": "data_specialist",
    "writing": "writing_specialist",
    "code": "code_specialist",
}


def selector_node(state: WorkflowState) -> Dict[str, Any]:
    """LangGraph Selector Node: Chooses the next eligible subtask to execute.

    Why this exists: In a directed acyclic graph (DAG) of subtasks, some tasks depend
    on previous outputs. The Selector checks completed tasks and finds the next
    subtask whose prerequisite dependencies are fully satisfied.
    """
    plan = state.get("plan")
    if not plan:
        logger.warning("Selector node: No execution plan found in state.")
        return {"current_task_id": None}

    completed = state.get("completed_tasks", {})

    # Priority sort subtasks according to critical path ordering
    critical_path_rank = {task_id: idx for idx, task_id in enumerate(plan.critical_path)}
    ordered_subtasks = sorted(plan.subtasks, key=lambda st: critical_path_rank.get(st.id, 999))

    for subtask in ordered_subtasks:
        if subtask.id in completed:
            continue

        # Check if all dependency subtasks are finished
        dependencies_ready = all(dep_id in completed for dep_id in subtask.dependencies)
        if dependencies_ready:
            logger.info(f"Selector node: Selected subtask '{subtask.id}' for specialist '{subtask.assigned_to}'")
            return {
                "current_task_id": subtask.id,
                "current_task_description": subtask.description,
                "current_task_assigned_to": subtask.assigned_to,
                "current_task_retry_count": 0,
                "review_feedback": None,
            }

    logger.info("Selector node: All subtasks completed successfully.")
    return {"current_task_id": None}
