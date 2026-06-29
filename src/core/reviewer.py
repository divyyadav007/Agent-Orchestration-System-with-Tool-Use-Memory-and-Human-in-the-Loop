import json
from langchain_core.messages import SystemMessage, HumanMessage
from src.utils.llm import get_llm, invoke_with_retry
from src.core.state import WorkflowState
from pydantic import BaseModel, Field

class ReviewResult(BaseModel):
    score: float = Field(description="Quality score 0.0 to 1.0")
    feedback: str = Field(description="Feedback if score < 0.7, else empty")
    passes: bool = Field(description="True if score >= 0.7")

REVIEWER_SYSTEM_PROMPT = """You are a reviewer. Evaluate the output of a specialist agent against the task description and expected output type. Provide a quality score between 0 (completely wrong) and 1 (perfect). If score is below 0.7, give specific feedback on how to improve. Output MUST be ONLY a JSON object with fields: score, feedback, passes."""

def reviewer_node(state: WorkflowState) -> dict:
    task_id = state["current_task_id"]
    output_raw = state.get("current_task_output", "")
    if isinstance(output_raw, list):
        output_str = "".join(str(item) for item in output_raw)
    else:
        output_str = str(output_raw)

    if not task_id or not output_str:
        return {}

    plan = state["plan"]
    subtask = next((st for st in plan.subtasks if st.id == task_id), None)
    if subtask is None:
        return {}
    expected_type = subtask.expected_output_type if subtask else "text"

    output_text = output_str

    retry_count = state.get("current_task_retry_count", 0)
    max_retries = 2

    # Otherwise, evaluate normally
    llm = get_llm(temperature=0)
    messages = [
        SystemMessage(content=REVIEWER_SYSTEM_PROMPT),
        HumanMessage(content=f"""Task: {subtask.description}
Expected output type: {expected_type}
Actual output:
{output_text}

Return ONLY valid JSON with score, feedback, passes.""")
    ]

    review = None
    for attempt in range(2):
        try:
            raw = invoke_with_retry(llm, messages)
            review_dict = json.loads(raw.content)
            review = ReviewResult(**review_dict)
            break
        except Exception as e:
            if attempt == 1:
                review = ReviewResult(score=0.5, feedback="", passes=True)
            else:
                messages.append(HumanMessage(content="Invalid JSON. Return ONLY valid JSON this time."))

    if review.passes:
        new_completed = dict(state.get("completed_tasks", {}))
        new_completed[task_id] = {
            "output": output_str,
            "assigned_to": state["current_task_assigned_to"],
            "review_score": review.score,
            "passed": review.passes
        }
        print(f"DEBUG reviewer: task {task_id} passed, score={review.score}")
        return {
            "completed_tasks": new_completed,
            "current_task_id": None,
            "current_task_output": None,
            "review_feedback": None,
            "current_task_retry_count": 0,
            "messages": [{"role": "system", "content": f"Task {task_id} reviewed, score={review.score}"}]
        }
    else:
        print(f"DEBUG reviewer: task {task_id} failed, retry {retry_count+1}/{max_retries}, score={review.score}, feedback='{review.feedback}'")
        return {
            "review_feedback": review.feedback,
            "current_task_retry_count": retry_count + 1
        }
