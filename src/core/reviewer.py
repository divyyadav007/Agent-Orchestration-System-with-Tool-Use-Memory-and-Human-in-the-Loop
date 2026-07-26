import json
import logging
from typing import Any, Dict

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from src.core.state import WorkflowState
from src.utils.llm import get_llm, invoke_with_retry

logger = logging.getLogger(__name__)


class ReviewResult(BaseModel):
    """Quality evaluation output from the Reviewer Agent."""

    score: float = Field(..., description="Quality verification score (0.0 to 1.0)")
    feedback: str = Field(..., description="Improvement instructions if score < 0.7")
    passes: bool = Field(..., description="True if output satisfies quality thresholds")


REVIEWER_SYSTEM_PROMPT = (
    "You are a quality reviewer. Evaluate a specialist agent's output against the task description, "
    "overall goal, and expected output type. Score quality between 0 (completely wrong) and 1 (perfect). "
    "If score < 0.7, provide actionable feedback. Output MUST be ONLY valid JSON with keys: score, feedback, passes."
)


def _extract_json_text(text: str) -> str:
    """Helper function to clean LLM markdown fences (e.g. ```json ... ```) from JSON responses."""
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned.split("```json")[1].split("```")[0].strip()
    elif cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1].split("```")[0].strip()
    return cleaned


def reviewer_node(state: WorkflowState) -> Dict[str, Any]:
    """LangGraph Reviewer Node: Automated Double-Loop Quality Verification.

    Why this exists: Specialist LLMs can hallucinate or miss key requirements.
    The Reviewer scores outputs ($< 0.7$ fails). Passed tasks advance to the next step;
    failed tasks trigger retries with specific feedback.
    """
    task_id = state.get("current_task_id")
    raw_output = state.get("current_task_output", "")
    output_str = "".join(str(i) for i in raw_output) if isinstance(raw_output, list) else str(raw_output)

    if not task_id or not output_str or not state.get("plan"):
        logger.warning("Reviewer node: Missing task ID, output, or plan.")
        return {}

    plan = state["plan"]
    subtask = next((st for st in plan.subtasks if st.id == task_id), None)
    if not subtask:
        logger.error(f"Reviewer node: Subtask '{task_id}' not found in plan.")
        return {}

    retry_count = state.get("current_task_retry_count", 0)
    logger.info(f"Reviewer evaluating subtask '{task_id}' (attempt {retry_count + 1}).")

    llm = get_llm(temperature=0)
    messages = [
        SystemMessage(content=REVIEWER_SYSTEM_PROMPT),
        HumanMessage(
            content=f"Task: {subtask.description}\nExpected type: {subtask.expected_output_type}\nActual output:\n{output_str}\n\nReturn ONLY valid JSON."
        ),
    ]

    review: ReviewResult = ReviewResult(score=0.5, feedback="", passes=True)
    for attempt in range(2):
        try:
            response = invoke_with_retry(llm, messages)
            json_str = _extract_json_text(response.content)
            data = json.loads(json_str)
            review = ReviewResult(**data)
            break
        except Exception as e:
            logger.warning(f"Failed parsing reviewer JSON output on attempt {attempt + 1}: {e}")
            if attempt == 0:
                messages.append(HumanMessage(content="Invalid JSON. Return ONLY valid JSON this time."))

    if review.passes:
        logger.info(f"Reviewer: Task '{task_id}' PASSED with score={review.score}")
        completed = dict(state.get("completed_tasks", {}))
        completed[task_id] = {
            "output": output_str,
            "assigned_to": state["current_task_assigned_to"],
            "review_score": review.score,
            "passed": True,
        }
        return {
            "completed_tasks": completed,
            "current_task_id": None,
            "current_task_output": None,
            "review_feedback": None,
            "current_task_retry_count": 0,
            "messages": [{"role": "system", "content": f"Task {task_id} reviewed, score={review.score}"}],
        }
    else:
        logger.warning(f"Reviewer: Task '{task_id}' FAILED (score={review.score}). Feedback: {review.feedback}")
        return {"review_feedback": review.feedback, "current_task_retry_count": retry_count + 1}
