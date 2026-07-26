from typing import TypedDict, Annotated, List, Dict, Optional, Any
import operator
from langchain_core.messages import BaseMessage
from src.core.models import ExecutionPlan


def merge_dicts(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Reducer function that merges two dictionaries together, preserving values.

    Used by LangGraph to merge completed task outputs across iterations.

    Args:
        a (Dict[str, Any]): The existing state dictionary.
        b (Dict[str, Any]): The incoming update dictionary.

    Returns:
        Dict[str, Any]: The merged state dictionary.
    """
    return {**(a or {}), **(b or {})}


class WorkflowState(TypedDict):
    """Represents the global state of the LangGraph multi-agent workflow."""

    # List of conversation messages, appended sequentially via operator.add
    messages: Annotated[List[BaseMessage], operator.add]

    # Original task request entered by the user
    user_request: str

    # The generated overall plan of execution
    plan: Optional[ExecutionPlan]

    # Validation errors encountered during plan checks (if any)
    validation_errors: Optional[str]

    # Retry count for generating/validating the overall plan
    retry_count: int

    # Map of completed task IDs to their outputs and metadata
    completed_tasks: Annotated[Dict[str, Dict[str, Any]], merge_dicts]

    # The task currently being executed
    current_task_id: Optional[str]
    current_task_description: Optional[str]
    current_task_assigned_to: Optional[str]

    # The output returned by the active specialist agent
    current_task_output: Optional[str]

    # Feedback from the reviewer if a task failed verification
    review_feedback: Optional[str]

    # Retry counter for the current task
    current_task_retry_count: int

    # Flag indicating whether the graph is currently waiting for human intervention
    awaiting_human: bool

    # Human Loop Escalation reason details
    escalation_reason: Optional[str]

    # Decision made by human: "approve" or "reject"
    human_decision: Optional[str]

    # Optional feedback comment from the human reviewer
    human_feedback: Optional[str]

    # Retrieved task context from ChromaDB long-term memory
    memory_context: Optional[str]

    # Override toggle forcing human verification on all tasks
    force_human_review: bool
