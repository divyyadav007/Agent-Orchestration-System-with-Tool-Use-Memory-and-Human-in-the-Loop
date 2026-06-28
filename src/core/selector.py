from src.core.state import WorkflowState

SPECIALIST_NODE_MAP = {
    "research": "research_specialist",
    "data": "data_specialist",
    "writing": "writing_specialist",
    "code": "code_specialist"
}

def selector_node(state: WorkflowState) -> dict:
    plan = state["plan"]
    if plan is None:
        print("DEBUG selector: no plan")
        return {"current_task_id": None}

    completed = state.get("completed_tasks", {})
    subtask_order = {task_id: idx for idx, task_id in enumerate(plan.critical_path)}
    sorted_subtasks = sorted(plan.subtasks, key=lambda st: subtask_order.get(st.id, 999))

    for subtask in sorted_subtasks:
        if subtask.id in completed:
            continue
        deps_met = all(dep in completed for dep in subtask.dependencies)
        if deps_met:
            print(f"DEBUG selector: next task {subtask.id} ({subtask.assigned_to})")
            return {
                "current_task_id": subtask.id,
                "current_task_description": subtask.description,
                "current_task_assigned_to": subtask.assigned_to,
                "current_task_retry_count": 0,
                "review_feedback": None
            }

    print("DEBUG selector: all tasks done")
    return {"current_task_id": None}