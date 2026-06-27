# src/core/reviewer.py
from pydantic import BaseModel, Field

class ReviewResult(BaseModel):
    score: float = Field(description="Quality score between 0.0 and 1.0")
    feedback: str = Field(description="Constructive feedback if score < 0.7, else empty")
    passes: bool = Field(description="True if score >= 0.7")


from src.core.models import SubTask
from src.core.state import WorkflowState
from src.utils.llm import get_llm
from langchain_core.messages import SystemMessage, HumanMessage

REVIEWER_SYSTEM_PROMPT = """You are a reviewer. Your job is to evaluate the output of a specialist agent against the task description and expected output type. Provide a quality score between 0 (completely wrong) and 1 (perfect). If score is below 0.7, give specific feedback on how to improve. Output MUST be structured as JSON with fields: score, feedback, passes (true if score >= 0.7)."""

def reviewer_node(state: WorkflowState) -> dict:
    task_id = state["current_task_id"]
    task_desc = state["current_task_description"]
    output = state.get("current_task_output", "")
    plan = state["plan"]
    
    if not task_id or not output:
        return {}
    
    # Find the expected output type from the plan
    subtask = next((st for st in plan.subtasks if st.id == task_id), None)
    expected_type = subtask.expected_output_type if subtask else "text"
    
    llm = get_llm(temperature=0)
    structured_llm = llm.with_structured_output(ReviewResult)
    
    messages = [
        SystemMessage(content=REVIEWER_SYSTEM_PROMPT),
        HumanMessage(content=f"""Task description: {task_desc}
Expected output type: {expected_type}
Actual output:
{output}""")
    ]
    
    review = structured_llm.invoke(messages)
    
    retry_count = state.get("current_task_retry_count", 0)
    max_retries = 2  # total 3 attempts
    
    if review.passes or retry_count >= max_retries:
        # Accept the output (even if low score but retries exhausted)
        new_completed = dict(state.get("completed_tasks", {}))
        new_completed[task_id] = {
            "output": output,
            "assigned_to": state["current_task_assigned_to"],
            "review_score": review.score,
            "passed": review.passes
        }
        return {
            "completed_tasks": new_completed,
            "current_task_id": None,
            "current_task_output": None,
            "review_feedback": None,
            "current_task_retry_count": 0,
            "messages": [{"role": "system", "content": f"Task {task_id} reviewed, score={review.score}"}]
        }
    else:
        # Retry needed
        return {
            "review_feedback": review.feedback,
            "current_task_retry_count": retry_count + 1
        }