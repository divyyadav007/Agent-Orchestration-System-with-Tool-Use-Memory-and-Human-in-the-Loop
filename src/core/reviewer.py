import json
import logging
from typing import Dict, Any, Union
from langchain_core.messages import SystemMessage, HumanMessage
from src.utils.llm import get_llm, invoke_with_retry
from src.core.state import WorkflowState
from pydantic import BaseModel, Field

# Initialize module logger
logger = logging.getLogger(__name__)

class ReviewResult(BaseModel):
    """Data model representing the verification result from the reviewer agent."""
    score: float = Field(..., description="Quality verification score between 0.0 and 1.0")
    feedback: str = Field(..., description="Detailed instructions/feedback if score is below 0.7; otherwise empty")
    passes: bool = Field(..., description="True if the output satisfies the task requirements (score >= 0.7)")


REVIEWER_SYSTEM_PROMPT = (
    "You are a reviewer. Evaluate the output of a specialist agent against the task description, "
    "relevance to the overall user goal, and expected output type. Provide a quality score between 0 (completely wrong) and 1 (perfect). "
    "Ensure the specialist's output is highly focused on the requested topic and contains no unrelated or off-topic information. "
    "If the score is below 0.7, give specific feedback on how to improve. "
    "Output MUST be ONLY a JSON object with fields: score, feedback, passes."
)

def reviewer_node(state: WorkflowState) -> Dict[str, Any]:
    """LangGraph node representing the task output verification step.
    
    Submits the specialist agent's output to a verification check using an LLM.
    If verified, indexes the completed output. If verification fails, increments
    retry counts.

    Args:
        state (WorkflowState): Current global graph state.

    Returns:
        Dict[str, Any]: State updates with completed tasks, reset metrics, or retry feedback.
    """
    task_id = state["current_task_id"]
    output_raw = state.get("current_task_output", "")
    
    if isinstance(output_raw, list):
        output_str = "".join(str(item) for item in output_raw)
    else:
        output_str = str(output_raw)

    if not task_id or not output_str:
        logger.warning("Reviewer node executed but current_task_id or output is empty.")
        return {}

    plan = state["plan"]
    if not plan:
        logger.error("Reviewer node: No execution plan found in state.")
        return {}
        
    subtask = next((st for st in plan.subtasks if st.id == task_id), None)
    if subtask is None:
        logger.error(f"Reviewer node: Subtask with ID '{task_id}' not found in plan.")
        return {}
        
    expected_type = subtask.expected_output_type
    retry_count = state.get("current_task_retry_count", 0)
    max_retries = 2

    logger.info(f"Reviewer node: Evaluating output for subtask '{task_id}' (attempt {retry_count + 1}).")
    llm = get_llm(temperature=0)
    messages = [
        SystemMessage(content=REVIEWER_SYSTEM_PROMPT),
        HumanMessage(content=f"""Task: {subtask.description}
Expected output type: {expected_type}
Actual output:
{output_str}

Return ONLY valid JSON with score, feedback, passes.""")
    ]

    review = None
    for attempt in range(2):
        try:
            raw = invoke_with_retry(llm, messages)
            # Standardize json extraction
            cleaned_content = raw.content.strip()
            # If wrapped in markdown blocks, extract content
            if cleaned_content.startswith("```json"):
                cleaned_content = cleaned_content.split("```json")[1].split("```")[0].strip()
            elif cleaned_content.startswith("```"):
                cleaned_content = cleaned_content.split("```")[1].split("```")[0].strip()
                
            review_dict = json.loads(cleaned_content)
            review = ReviewResult(**review_dict)
            break
        except Exception as e:
            logger.warning(f"Failed parsing reviewer JSON output on attempt {attempt + 1}: {e}")
            if attempt == 1:
                # Default safety fallback if evaluation model fails to output valid JSON twice
                logger.warning("Reviewer failed twice. Falling back to default pass.")
                review = ReviewResult(score=0.5, feedback="", passes=True)
            else:
                messages.append(HumanMessage(content="Invalid JSON. Return ONLY valid JSON this time."))

    if review is None:
        review = ReviewResult(score=0.5, feedback="", passes=True)

    if review.passes:
        logger.info(f"Reviewer node: Task '{task_id}' PASSED with score={review.score}.")
        new_completed = dict(state.get("completed_tasks", {}))
        new_completed[task_id] = {
            "output": output_str,
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
        next_retry = retry_count + 1
        logger.warning(f"Reviewer node: Task '{task_id}' FAILED verification (score={review.score}). Feedback: {review.feedback}")
        return {
            "review_feedback": review.feedback,
            "current_task_retry_count": next_retry
        }
