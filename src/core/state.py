from typing import TypedDict, Annotated, List, Dict, Optional, Any
import operator
from langchain_core.messages import BaseMessage
from src.core.models import ExecutionPlan

def merge_dicts(a: dict, b: dict) -> dict:
    return {**a, **b}

class WorkflowState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    user_request: str
    plan: Optional[ExecutionPlan]
    validation_errors: Optional[str]
    retry_count: int
    completed_tasks: Annotated[Dict[str, Dict[str, Any]], merge_dicts]
    current_task_id: Optional[str]
    current_task_description: Optional[str]
    current_task_assigned_to: Optional[str]
    current_task_output: Optional[str]          # raw specialist output
    review_feedback: Optional[str]             # feedback for retry
    current_task_retry_count: int              # per-task retry count
    awaiting_human: bool                    # True if waiting for human input
    escalation_reason: Optional[str]        # Why escalation happened
    human_decision: Optional[str]           # "approve", "reject", "modify"
    human_feedback: Optional[str]           # Optional instructions from human