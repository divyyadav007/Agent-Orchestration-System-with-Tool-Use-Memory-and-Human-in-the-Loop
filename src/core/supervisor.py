from typing import Optional
from langchain_core.messages import SystemMessage, HumanMessage
from src.utils.llm import get_llm
from src.core.models import ExecutionPlan, SubTask
from src.core.state import WorkflowState
from src.memory.manager import memory_manager
from src.utils.llm import invoke_with_retry



SUPERVISOR_SYSTEM_PROMPT = """You are a task planning supervisor. Given a user request, you will create an execution plan in structured JSON format. You have the following specialists available:
- research: Can search the web, fetch pages, extract information.
- data: Can query databases, process data, perform calculations.
- writing: Can draft text, summaries, reports, emails.
- code: Can write and execute Python code in a sandbox.

Rules:
1. Break the task into concrete, independent subtasks where possible.
2. Assign each subtask to the most appropriate specialist.
3. Mark dependencies: if a subtask needs the output of another, list its ID in dependencies.
4. For each subtask, clearly describe the expected output type.
5. Include a critical path: sequence of subtask IDs that are sequential bottlenecks.
"""

def validate_plan(plan: ExecutionPlan) -> tuple[bool, Optional[str]]:
    """
    Returns (is_valid, error_message).
    If valid, error_message is None.
    """
    subtask_ids = {st.id for st in plan.subtasks}
    
    # Check for duplicate IDs
    if len(subtask_ids) != len(plan.subtasks):
        return False, "Duplicate subtask IDs found."
    
    # Check that all dependency IDs exist in plan
    for st in plan.subtasks:
        for dep_id in st.dependencies:
            if dep_id not in subtask_ids:
                return False, f"Subtask '{st.id}' depends on nonexistent ID '{dep_id}'."
    
    # Check critical path IDs exist
    for cp_id in plan.critical_path:
        if cp_id not in subtask_ids:
            return False, f"Critical path ID '{cp_id}' not found in subtasks."
    
    # Check that assigned_to is a valid specialist
    valid_specialists = {"research", "data", "writing", "code"}
    for st in plan.subtasks:
        if st.assigned_to not in valid_specialists:
            return False, f"Subtask '{st.id}' assigned to unknown specialist '{st.assigned_to}'."
    
    return True, None


def supervisor_node(state: WorkflowState) -> dict:
    llm = get_llm(temperature=0)
    structured_llm = llm.with_structured_output(ExecutionPlan)
    
    # Fetch similar past tasks from long-term memory
    user_request = state["user_request"]
    similar_tasks = memory_manager.get_context_for_planning(user_request)
    
    # Build context string
    memory_context = ""
    if similar_tasks:
        memory_context = "Similar past tasks and their results:\n"
        for i, task in enumerate(similar_tasks):
            doc = task['document'][:150] + "..."   # 150 chars max
            memory_context += f"{i+1}. {doc}\n"
    
    messages = [
        SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT),
        HumanMessage(content=f"User request: {user_request}\n{memory_context}")
    ]
    
    if state.get("validation_errors"):
        feedback = HumanMessage(content=f"Previous plan had errors: {state['validation_errors']}. Please fix the plan.")
        messages.append(feedback)
    
    # ... inside supervisor_node ...
    plan = invoke_with_retry(structured_llm, messages)
    return {"plan": plan, "retry_count": state.get("retry_count", 0) + 1}

def validation_node(state: WorkflowState) -> dict:
    plan = state["plan"]
    is_valid, error = validate_plan(plan)
    if is_valid:
        return {"validation_errors": None}
    else:
        return {"validation_errors": error}