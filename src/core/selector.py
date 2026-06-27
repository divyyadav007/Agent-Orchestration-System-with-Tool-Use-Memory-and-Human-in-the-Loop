from src.core.state import WorkflowState

SPECIALIST_NODE_MAP = {
    "research": "research_specialist",
    "data": "data_specialist",
    "writing": "writing_specialist",
    "code": "code_specialist"
}

def selector_node(state: WorkflowState) -> dict:
    """Pick the next ready subtask and set current task info. If none, set current_task_id=None."""
    plan = state["plan"]
    if plan is None:
        return {"current_task_id": None}
    
    completed = state.get("completed_tasks", {})
    
    # Sort subtasks by critical path order if possible, else by id
    subtask_order = {task_id: idx for idx, task_id in enumerate(plan.critical_path)}
    sorted_subtasks = sorted(plan.subtasks, key=lambda st: subtask_order.get(st.id, 999))
    
    for subtask in sorted_subtasks:
        if subtask.id in completed:
            continue
        # Check dependencies
        deps_met = all(dep in completed for dep in subtask.dependencies)
        if deps_met:
            return {
                "current_task_id": subtask.id,
                "current_task_description": subtask.description,
                "current_task_assigned_to": subtask.assigned_to
            }
    
    # All tasks completed
    return {"current_task_id": None}