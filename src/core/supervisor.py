import logging
from typing import Any, Dict, Optional, Tuple

from langchain_core.messages import HumanMessage, SystemMessage

from src.core.models import ExecutionPlan
from src.core.state import WorkflowState
from src.memory.manager import memory_manager
from src.utils.llm import get_llm, invoke_with_retry

logger = logging.getLogger(__name__)

SUPERVISOR_SYSTEM_PROMPT = """You are a task planning supervisor. Create a structured execution plan in JSON format.
Specialists available:
- research: Search the web for up-to-date information, news, or articles.
- data: Process text/data and perform calculations (text-based).
- writing: Draft text, summaries, briefs, reports, emails.
- code: Save text content to workspace files. Use ONLY for file IO.

Rules:
1. Break user requests into concrete, independent subtasks.
2. Assign each subtask to the most appropriate specialist.
3. For search/news, use 'research'. For briefs/summaries, use 'writing'. For saving files, use 'code'.
4. Declare dependencies: list prerequisite subtask IDs in 'dependencies'.
5. Include a critical path: sequence of bottleneck subtask IDs.
"""


def validate_plan(plan: ExecutionPlan) -> Tuple[bool, Optional[str]]:
    """Validates plan subtask IDs, dependencies, critical path, and specialist names."""
    subtask_ids = {st.id for st in plan.subtasks}

    if len(subtask_ids) != len(plan.subtasks):
        return False, "Duplicate subtask IDs found in plan."

    valid_specialists = {"research", "data", "writing", "code"}
    for st in plan.subtasks:
        missing_deps = [dep for dep in st.dependencies if dep not in subtask_ids]
        if missing_deps:
            return False, f"Subtask '{st.id}' depends on missing ID(s): {missing_deps}"
        if st.assigned_to not in valid_specialists:
            return False, f"Subtask '{st.id}' assigned to unknown specialist '{st.assigned_to}'"

    missing_cp = [cp for cp in plan.critical_path if cp not in subtask_ids]
    if missing_cp:
        return False, f"Critical path contains missing subtask ID(s): {missing_cp}"

    return True, None


def supervisor_node(state: WorkflowState) -> Dict[str, Any]:
    """LangGraph Supervisor Node: Generates structured execution plans.

    Why with_structured_output: Forces the LLM to output valid JSON strictly
    conforming to the Pydantic ExecutionPlan schema.
    """
    logger.info("Supervisor node: Generating execution plan.")
    llm = get_llm(temperature=0)
    # Use function_calling method for maximum compatibility across Groq model gateways
    structured_llm = llm.with_structured_output(ExecutionPlan, method="function_calling")

    user_request = state["user_request"]
    similar_tasks = memory_manager.get_context_for_planning(user_request)

    # Build memory context from ChromaDB
    memory_context = ""
    if similar_tasks:
        records = [f"{i+1}. {t['document'][:150]}..." for i, t in enumerate(similar_tasks)]
        memory_context = "Similar past tasks and results:\n" + "\n".join(records)

    messages = [
        SystemMessage(content=SUPERVISOR_SYSTEM_PROMPT),
        HumanMessage(content=f"User request: {user_request}\n{memory_context}"),
    ]

    if state.get("validation_errors"):
        logger.info(f"Supervisor retry due to errors: {state['validation_errors']}")
        messages.append(HumanMessage(content=f"Previous plan had errors: {state['validation_errors']}. Please fix them."))

    plan: ExecutionPlan = invoke_with_retry(structured_llm, messages)
    logger.info(f"Supervisor created plan: '{plan.overall_goal}'")

    return {"plan": plan, "retry_count": state.get("retry_count", 0) + 1, "memory_context": memory_context}


def validation_node(state: WorkflowState) -> Dict[str, Any]:
    """LangGraph Validation Node: Evaluates plan structural integrity."""
    plan = state.get("plan")
    if not plan:
        return {"validation_errors": "No plan found to validate."}

    is_valid, error = validate_plan(plan)
    return {"validation_errors": error}
